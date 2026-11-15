"""Chạy các cấu hình agent Haiku trên DEV; mặc định chỉ in kế hoạch, --execute mới gọi API."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from .benchmark_data import ROOT, evidence_set_hit, load_cases, single_chunk_hit, validate_cases
from .context import NeighborIndex
from .costs import CHECKED_ON, SOURCE
from .day6_adapter import DEFAULT_DAY6, DenseRetriever, load_snapshot
from .model_controller import ClaudeController
from .rag_agent import run_agent
from .retrievers import BM25Retriever, HybridRetriever


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def technical_summary(traces):
    ok = [t for t in traces if t["status"] in {"answered", "abstain"}]
    positive = [t for t in ok if t["answerable"]]
    known_costs = [t.get("estimated_cost_usd") for t in traces if t.get("estimated_cost_usd") is not None]
    complete_costs = all(t.get("estimated_cost_usd") is not None and
                         t.get("model_calls", 0) == sum(e["event"] == "model" for e in t.get("events", []))
                         for t in traces)
    return {"scheduled": len(traces), "status_counts": dict(Counter(t["status"] for t in traces)),
            "tool_use": {"n": sum(t.get("searches", 0) > 0 for t in ok), "N": len(ok)},
            "search_distribution": dict(Counter(str(t.get("searches", 0)) for t in ok)),
            "model_calls": sum(t.get("model_calls", 0) for t in traces),
            "elapsed_seconds": sum(t.get("elapsed_seconds", 0) for t in traces),
            "usage": {key: sum(t.get("usage", {}).get(key, 0) for t in traces)
                      for key in ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]},
            "known_estimated_cost_usd": round(sum(known_costs), 12),
            "cost_estimate_complete": complete_costs,
            "context_evidence_exact": {"n": sum(t["context_strict_hit"] is True for t in positive), "N": len(positive)},
            "context_evidence_set": {"n": sum(t["context_set_hit"] is True for t in positive), "N": len(positive)},
            "semantic_quality": "pending human review; status counts are not accuracy/abstention correctness",
            "billing": "Estimate from returned usage only; not invoice or hardware cost."}


def review_template(trace):
    return {"query_id": trace["query_id"], "config_id": trace["config_id"],
            "review_status": "pending" if trace["status"] in {"answered", "abstain"} else "not_applicable",
            "reviewer": None, "reviewed_at": None,
            "answer_grade": None, "context_grade": None,
            "citation_support": [{"id": c, "supports": None, "reason": ""} for c in trace.get("citations", [])],
            "abstention_correct": None, "reason": ""}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "configs/agent-dev.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--day6-root", type=Path, default=DEFAULT_DAY6)
    parser.add_argument("--configs", help="Các ID cấu hình phân cách dấu phẩy; mặc định toàn bộ")
    parser.add_argument("--ids", help="Subset ID dev, chỉ dùng pilot; không gọi là full dev")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if plan["split"] != "dev" or plan["model"] != "claude-haiku-5-5":
        raise ValueError("Runner này chỉ dùng dev và Haiku đã chọn; không chạy test/Opus")
    cases, chunks = load_cases(ROOT, "dev")
    validate_cases(cases, chunks, "dev")
    configs = plan["configs"]
    if len({c["id"] for c in configs}) != len(configs):
        raise ValueError("Config ID trùng")
    for field, values, collection, id_key in [("configs", args.configs, configs, "id"), ("ids", args.ids, cases, "id")]:
        if values:
            requested = set(values.split(","))
            if requested - {x[id_key] for x in collection}:
                raise ValueError(f"ID không tồn tại trong {field}")
            filtered = [x for x in collection if x[id_key] in requested]
            if field == "configs": configs = filtered
            else: cases = filtered
    print(f"Plan: {len(cases)} dev cases × {len(configs)} configs = {len(cases) * len(configs)} agent runs; model={plan['model']}", flush=True)
    if not args.execute:
        print("Dry run; chưa gọi API. Thêm --execute để chạy thật.")
        return
    if args.output.exists():
        raise FileExistsError("Output tồn tại; chọn thư mục mới")
    identity, source_chunks = load_snapshot(args.day6_root)
    manifest = json.loads((ROOT / "benchmark/manifest.json").read_text())
    snapshot_hash = hashlib.sha256((args.day6_root / "starter/results/ingest.json").read_bytes()).hexdigest()
    if source_chunks != chunks or snapshot_hash != manifest["source_snapshot_sha256"]:
        raise ValueError("Snapshot/corpus khác benchmark")
    paths = ["benchmark/dev.json", "benchmark/manifest.json", "data/day6_chunks.json",
             "starter/agentic.py", "starter/__init__.py", "starter/baseline.py",
             *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "src").glob("*.py"))]]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
    record = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "split": "dev", "model": plan["model"],
              "plan": plan, "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
              "configs_executed": [c["id"] for c in configs], "query_ids": [q["id"] for q in cases],
              "full_dev": len(cases) == 17, "input_code_hashes": hashes, "embedding": identity,
              "source_snapshot_sha256": snapshot_hash,
              "pricing_source": SOURCE, "pricing_checked_on": CHECKED_ON,
              "quality_status": "unreviewed; no automatic semantic grades",
              "notes": "Sequential fixed config order, no temperature control, one sample per config/query; cache/model variability can affect timings and query choices."}
    save(args.output / "run.json", record)
    controller = ClaudeController(model=plan["model"])
    before = time.perf_counter()
    dense = DenseRetriever(args.day6_root)
    if dense.chunks != chunks:
        raise ValueError("Backend chunks differ")
    lexical, neighbors = BM25Retriever(chunks), NeighborIndex(chunks)
    retrievers = {"dense": dense, "bm25": lexical, "hybrid": HybridRetriever(lexical, dense)}
    summaries = {"shared_retriever_init_seconds": time.perf_counter() - before, "configs": {}}
    for config in configs:
        traces, reviews = [], []
        for case in cases:
            trace = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "stage": "agent_dev",
                     "query_id": case["id"], "config_id": config["id"], "split": "dev",
                     "requested_model": controller.model, "provider": "anthropic",
                     "retrieval_method": config["method"], "semantic_review": "pending"}
            try:
                # Không truyền answerable, gold hoặc expected_answer vào run_agent.
                run_agent(case["question"], controller, retrievers[config["method"]],
                          filters=case.get("filter"), top_k=config["top_k"], budget=config["budget"],
                          max_searches=config["max_searches"], max_model_calls=config["max_model_calls"],
                          context_policy=config["context_policy"], neighbor_index=neighbors, trace=trace)
            except Exception as error:
                trace.setdefault("status", "error")
                if trace["status"] == "running": trace["status"] = "error"
                trace.setdefault("error_type", type(error).__name__)
            trace["answerable"] = case["answerable"]  # Chỉ thêm sau khi model chạy xong.
            trace["context_strict_hit"] = single_chunk_hit(trace.get("context_chunks", []), case)
            trace["context_set_hit"] = evidence_set_hit(trace.get("context_chunks", []), case)
            searches = [e for e in trace.get("events", []) if e["event"] == "search"]
            trace["first_search_hit3"] = single_chunk_hit(searches[0]["results"][:3], case) if searches else None
            trace["first_search_is_original_query"] = bool(searches and searches[0]["query"] == case["question"])
            save(args.output / "traces" / config["id"] / f"{case['id']}.json", trace)
            traces.append(trace)
            reviews.append(review_template(trace))
            print(f"{config['id']}/{case['id']}: {trace['status']} searches={trace.get('searches',0)} calls={trace.get('model_calls',0)} estimated_USD={trace.get('estimated_cost_usd')}", flush=True)
        save(args.output / "reviews" / f"{config['id']}.json", reviews)
        summaries["configs"][config["id"]] = technical_summary(traces)
    if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value for name, value in hashes.items()):
        raise ValueError("Code/data thay đổi trong khi chạy; giữ trace và không dùng run này làm so sánh cố định")
    save(args.output / "technical_summary.json", summaries)
    print("Saved", args.output, "— human semantic review still pending.")


if __name__ == "__main__":
    main()
