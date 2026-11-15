"""Khung agent Day 7 được mở rộng từ starter gốc; production nối qua adapter.

Controller.decide(question, history) trả action search/answer/abstain.
Retriever.search(query, filters=..., top_k=...) truy xuất dữ liệu thật.
Không import model/provider, database hoặc benchmark gold vào vòng lặp này.
Các tham số mở rộng giữ mặc định của ví dụ cho test và cách gọi starter cũ.
"""
from typing import Any, Callable, Protocol
import time

if __package__:
    from .baseline import pack_context
else:
    from baseline import pack_context


class Controller(Protocol):
    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """search: action/query; answer: action/answer/citations; abstain: action/answer/citations=[]."""
        ...


class Retriever(Protocol):
    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        """Trả id/text/source_id/source/page/metadata/score, không nhận gold."""
        ...


def run_agent(question: str, controller: Controller, retriever: Retriever, *,
              filters=None, max_searches=4, top_k=3, budget=800,
              max_model_calls=None, trace=None, context_order="oldest",
              expand_results: Callable | None = None, pack_context_fn: Callable | None = None,
              validate_answer: Callable | None = None, stop_on_search_limit=True,
              context_policy=None):
    """Vòng lặp thực tế dùng bởi src.rag_agent, vẫn hỗ trợ adapter mẫu gốc.

    Callbacks context/citation cho phép sửa starter mà không gắn provider vào nó.
    _trace là metadata công khai do model adapter cung cấp, không phải chỉ dẫn.
    Lỗi provider/retrieval truyền ra ngoài; không fallback mock hoặc giả abstain.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question phải là chuỗi không rỗng")
    if any(type(n) is not int or n < 1 for n in [max_searches, top_k, budget]):
        raise ValueError("max_searches/top_k/budget phải là số nguyên dương")
    max_model_calls = max_searches + 1 if max_model_calls is None else max_model_calls
    if type(max_model_calls) is not int or max_model_calls < 1 or context_order not in {"oldest", "latest"}:
        raise ValueError("max_model_calls/context_order không hợp lệ")
    packer = pack_context_fn or pack_context
    trace = trace if trace is not None else {}
    trace.update({"question": question, "filter": filters, "events": [], "searches": 0,
                  "model_calls": 0, "usage": {}, "cost_usd": None, "status": "running",
                  "configuration": {"top_k": top_k, "budget_chars": budget,
                                    "max_searches": max_searches, "max_model_calls": max_model_calls,
                                    "context_policy": context_policy or context_order},
                  "context": "", "context_ids": [], "context_chunks": []})
    events, candidates, queries, history = trace["events"], [], [], []
    started = time.perf_counter()

    def finish(value):
        trace.update(value)
        trace["elapsed_seconds"] = time.perf_counter() - started
        return trace

    def feedback(error=None):
        current = {"tool": "search", "queries": list(queries), "context": trace["context"],
                   "context_ids": list(trace["context_ids"]),
                   "searches_remaining": max_searches - trace["searches"]}
        if error:
            current["error"] = error
        return [current]

    try:
        for step in range(max_model_calls):
            trace["model_calls"] += 1
            action = controller.decide(question, history)
            if not isinstance(action, dict):
                raise ValueError("Controller phải trả normalized action")
            metadata = action.get("_trace")
            if metadata:
                events.append({"event": "model", "step": step + 1, **metadata})
                response = metadata.get("response", {})
                for key, value in response.get("usage", {}).items():
                    if type(value) is int:
                        trace["usage"][key] = trace["usage"].get(key, 0) + value
                estimates = [e["response"].get("cost_estimate") for e in events if e["event"] == "model"]
                trace["cost_estimate_coverage"] = {"known_calls": sum(e is not None for e in estimates), "returned_calls": len(estimates)}
                trace["estimated_cost_usd"] = (round(sum(e["estimated_usd"] for e in estimates), 12)
                                                 if all(e is not None for e in estimates) else None)
            kind = action.get("action")
            if kind == "search":
                query = action.get("query")
                if not isinstance(query, str) or not query.strip():
                    raise ValueError("search query phải là chuỗi không rỗng")
                if trace["searches"] >= max_searches:
                    events.append({"event": "search_limit"})
                    if stop_on_search_limit:
                        return finish({"status": "abstain", "answer": "Không đủ bằng chứng để trả lời.", "citations": []})
                    history = feedback("Đã đạt giới hạn search; hãy kết thúc bằng answer hoặc abstain.")
                    continue
                before = time.perf_counter()
                trace["searches"] += 1
                results = retriever.search(query, filters=filters, top_k=top_k)
                if len(results) > top_k or len({r["id"] for r in results}) != len(results):
                    raise ValueError("retriever phải trả tối đa top_k chunk ID duy nhất")
                added = expand_results(results) if expand_results else results
                candidates = added + candidates if context_order == "latest" else candidates + added
                context, ids = packer(candidates, budget=budget)
                by_id = {c["id"]: c for c in reversed(candidates)}
                if len(set(ids)) != len(ids) or set(ids) - set(by_id) or len(context) > budget:
                    raise ValueError("Context packer trả ID/budget không hợp lệ")
                queries.append(query)
                trace.update({"context": context, "context_ids": ids, "context_chunks": [by_id[i] for i in ids]})
                events.append({"event": "search", "query": query, "query_rewritten": query != question,
                               "filter": filters, "results": results, "context": context,
                               "context_candidates": added, "context_ids": ids,
                               "elapsed_seconds": time.perf_counter() - before})
                history = feedback()
            elif kind in {"answer", "abstain"}:
                if validate_answer:
                    try:
                        result = validate_answer(action, trace["context_ids"], trace["searches"] > 0)
                    except ValueError as error:
                        events.append({"event": "invalid_finish", "error": str(error)})
                        history = feedback(str(error))
                        continue
                else:
                    answer, citations = action.get("answer"), action.get("citations")
                    if not isinstance(answer, str) or not isinstance(citations, list) or any(not isinstance(i, str) for i in citations):
                        raise ValueError("answer/citations không hợp lệ")
                    valid = bool(answer.strip() and citations and all(i in trace["context_ids"] and f"[{i}]" in answer for i in citations))
                    if kind == "abstain" and not citations and trace["searches"] > 0:
                        result = {"status": "abstain", "answer": answer, "citations": []}
                    elif valid:
                        result = {"status": "answered", "answer": answer, "citations": citations}
                    else:
                        events.append({"event": "invalid_or_missing_citations"})
                        return finish({"status": "abstain", "answer": "Không đủ bằng chứng để trả lời.", "citations": []})
                events.append({"event": "finish" if validate_answer else "answer", **result,
                               "citation_check": "ID membership/format only; semantic support requires review"})
                return finish(result)
            else:
                raise ValueError("action phải là search, answer hoặc abstain")
        if stop_on_search_limit:
            return finish({"status": "abstain", "answer": "Không đủ bằng chứng để trả lời.", "citations": []})
        return finish({"status": "limit", "answer": "Agent đã dừng vì đạt giới hạn lượt model; chưa có kết luận hợp lệ.", "citations": []})
    except Exception as error:
        trace.update({"status": "error", "error_type": type(error).__name__,
                      "error": str(error) if type(error).__name__ == "ModelError" else "Agent/retrieval error; không thay bằng câu trả lời giả.",
                      "elapsed_seconds": time.perf_counter() - started})
        raise
