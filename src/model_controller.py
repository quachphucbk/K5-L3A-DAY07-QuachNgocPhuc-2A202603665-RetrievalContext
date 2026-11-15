"""Claude Messages API qua HTTPS, dùng key local; không cần thêm SDK."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from .benchmark_data import ROOT
from .costs import estimate_cost


class ModelError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Không chuyển header chứa key tới host khác.
        return None


class ClaudeController:
    def __init__(self, env_file=None, model=None):
        from dotenv import dotenv_values

        local = dotenv_values(ROOT / ".env")
        source = env_file or os.environ.get("AGENT_ENV_FILE") or local.get("AGENT_ENV_FILE")
        if source:
            source = Path(source).expanduser()
            if not source.is_absolute():
                source = ROOT / source
            if not source.is_file():
                raise ModelError("Không tìm thấy AGENT_ENV_FILE; xem hướng dẫn bước 5")
            inherited = dotenv_values(source)
        else:
            inherited = {}
        self.key = (os.environ.get("ANTHROPIC_API_KEY") or local.get("ANTHROPIC_API_KEY")
                    or inherited.get("ANTHROPIC_API_KEY"))
        self.model = (model or os.environ.get("AGENT_MODEL") or local.get("AGENT_MODEL")
                      or inherited.get("MODEL"))
        if not self.key or self.key.endswith("..."):
            raise ModelError("Thiếu ANTHROPIC_API_KEY trong môi trường hoặc env được chỉ định")
        if not self.model:
            raise ModelError("Thiếu AGENT_MODEL hoặc MODEL trong env nguồn")
        self.opener = urllib.request.build_opener(NoRedirect)

    def decide(self, system, messages, tools, *, max_tokens=1800):
        payload = {"model": self.model, "max_tokens": max_tokens,
                   "system": system, "messages": messages, "tools": tools,
                   "tool_choice": {"type": "auto", "disable_parallel_tool_use": True}}
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json", "x-api-key": self.key,
                     "anthropic-version": "2023-06-01"}, method="POST")
        try:
            with self.opener.open(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            # Không ghi response body/header có thể chứa thông tin nhạy cảm.
            raise ModelError(f"Claude API HTTP {error.code}; kiểm tra key/model/quota") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ModelError("Không kết nối được Claude API hoặc timeout") from None
        if result.get("type") == "error":
            raise ModelError("Claude API trả lỗi; không thay bằng model giả")
        if result.get("stop_reason") != "tool_use":
            raise ModelError("Model chưa trả tool call hoàn chỉnh (có thể hết max_tokens)")
        content = result.get("content", [])
        calls = [block for block in content if block.get("type") == "tool_use"]
        if len(calls) != 1:
            raise ModelError("Yêu cầu đúng một tool call mỗi lượt")
        # Chỉ lưu output công khai, không yêu cầu/lưu chain of thought nội bộ.
        visible = [b for b in content if b.get("type") in {"text", "tool_use"}]
        actual_model = result.get("model", self.model)
        usage = result.get("usage", {})
        return {"id": result.get("id"), "model": actual_model,
                "content": visible, "tool_call": calls[0], "usage": usage,
                "cost_estimate": estimate_cost(actual_model, usage)}
