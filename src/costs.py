"""Ước tính từ usage từng request, không phải hóa đơn đã đối soát."""
from decimal import Decimal

SOURCE = "https://platform.claude.com/docs/en/models/haiku-5-5/overview"
CHECKED_ON = "2026-11-14"


def estimate_cost(model, usage):
    if not model.startswith("claude-haiku-5-5"):
        return None
    required = ["input_tokens", "output_tokens"]
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in required):
        return None
    counts = {k: usage.get(k, 0) for k in ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]}
    if any(type(n) is not int or n < 0 for n in counts.values()):
        return None
    cache = usage.get("cache_creation") or {}
    five = cache.get("ephemeral_5m_input_tokens", 0)
    hour = cache.get("ephemeral_1h_input_tokens", 0)
    if any(type(n) is not int or n < 0 for n in [five, hour]):
        return None
    if five + hour != counts["cache_creation_input_tokens"]:
        return None  # Không đoán TTL nếu usage không phân loại cache write.
    prompt_size = counts["input_tokens"] + counts["cache_creation_input_tokens"] + counts["cache_read_input_tokens"]
    rates = {"input": "0.10", "output": "0.50", "read": "0.01", "write5m": "0.125", "write1h": "0.20"}
    if prompt_size > 100000:
        rates = {"input": "0.50", "output": "2.50", "read": "0.05", "write5m": "0.625", "write1h": "1.00"}
    values = {"input": counts["input_tokens"], "output": counts["output_tokens"],
              "read": counts["cache_read_input_tokens"], "write5m": five, "write1h": hour}
    usd = sum(Decimal(str(values[k])) * Decimal(rates[k]) for k in rates) / Decimal(1000000)
    return {"estimated_usd": float(usd), "rates_usd_per_million": rates,
            "prompt_tokens_including_cache": prompt_size,
            "source": SOURCE, "checked_on": CHECKED_ON,
            "note": "Standard direct API estimate; excludes taxes, discounts and any call without returned usage. Not a verified invoice."}
