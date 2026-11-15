"""Bước 4: benchmark retrieval trên DEV, chưa chạy agent hoặc test holdout.

python -m src.benchmark_retrieval --output results/dev-retrieval-01
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import time

from .benchmark_data import (ROOT, evidence_set_hit, load_cases, runtime_input,
                             single_chunk_hit, validate_cases)
from .context import pack_context
from .day6_adapter import DEFAULT_DAY6, DenseRetriever, load_snapshot
from .retrievers import BM25Retriever, reciprocal_rank_fusion


def evaluate_result(case, method, results, elapsed, budget, candidate_count):
    top3 = results[:3]
    context, kept = pack_context(top3, budget)
    return {
        "query_id": case["id"], "split": "dev", "method": method, "status": "ok",
        "answerable": case["answerable"], "request": runtime_input(case),
        "results": top3, "candidate_count": candidate_count,
        "ranking": [{"id": c["id"], "page": c["page"], "score": c["score"]} for c in results],
        "hit1": single_chunk_hit(top3[:1], case),
        "hit3": single_chunk_hit(top3, case),
        "evidence_set_hit3": evidence_set_hit(top3, case),
        "packed_context_strict_hit": single_chunk_hit(kept, case),
        "packed_context_set_hit": evidence_set_hit(kept, case),
        "context": context, "context_ids": [c["id"] for c in kept],
        "context_chars": len(context), "budget_chars": budget, "elapsed_seconds": elapsed,
        # Gold nằm trong trace evaluator, không truyền cho retriever/packer.
        "gold": case.get("gold", []), "evidence_sets": case.get("evidence_sets"),
        "expected_answer": case.get("expected_answer"),
    }


def summarize(traces):
    rows = []
    for method in ["dense", "bm25", "hybrid"]:
        selected = [t for t in traces if t["method"] == method]
        ok = [t for t in selected if t["status"] == "ok"]
        answerable = [t for t in ok if t["answerable"]]
        row = {"method": method, "scheduled": len(selected), "successful": len(ok),
               "errors": len(selected) - len(ok),
               "answerable_total": sum(t["answerable"] for t in selected),
               "answerable_scored": len(answerable),
               "unanswerable_successful": sum(not t["answerable"] for t in ok),
               "mean_search_ms": statistics.mean(t["elapsed_seconds"] * 1000 for t in ok) if ok else None}
        for field in ["hit1", "hit3", "evidence_set_hit3", "packed_context_strict_hit", "packed_context_set_hit"]:
            numerator = sum(t[field] is True for t in answerable)
            row[field + "_n"] = numerator
            row[field + "_rate"] = numerator / len(answerable) if answerable else None
        rows.append(row)
    return rows


def write_json(path, data):
    with path.open("x", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Thư mục mới; không ghi đè")
    parser.add_argument("--day6-root", type=Path, default=DEFAULT_DAY6)
    parser.add_argument("--budget", type=int, default=800, help="Ký tự context gồm header nguồn")
    args = parser.parse_args()
    if args.budget < 1:
        parser.error("budget phải dương")
    if args.output.exists():
        parser.error("Output đã tồn tại; chọn thư mục mới để giữ kết quả cũ")
    cases, chunks = load_cases(ROOT, "dev")
    validate_cases(cases, chunks, "dev")
    manifest_path = ROOT / "benchmark/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    snapshot_path = args.day6_root / "starter/results/ingest.json"
    snapshot_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    if snapshot_hash != manifest["source_snapshot_sha256"]:
        raise ValueError("Snapshot Day 6 khác nguồn benchmark")
    identity, source_chunks = load_snapshot(args.day6_root)
    if source_chunks != chunks:
        raise ValueError("Chunk B Day 6 khác corpus benchmark Day 7")
    args.output.mkdir(parents=True, exist_ok=False)
    input_paths = ["benchmark/dev.json", "benchmark/manifest.json", "data/day6_chunks.json",
                   "src/day6_adapter.py", "src/retrievers.py", "src/benchmark_data.py",
                   "src/context.py", "src/benchmark_retrieval.py"]
    input_hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in input_paths}
    versions = {}
    for name in ["sentence-transformers", "torch", "transformers", "psycopg", "python-dotenv"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not installed"
    plan = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "stage": "retrieval_only",
        "split": "dev", "benchmark_hashes": input_hashes, "source_snapshot_sha256": snapshot_hash,
        "python": platform.python_version(), "versions": versions, "embedding": identity,
        "configuration": {"methods": ["dense", "bm25", "hybrid"], "ranking_cutoff": 3,
                          "candidate_window": len(chunks), "budget_chars": args.budget,
                          "packing": "whole chunks in rank order; skip those not fitting; include source headers",
                          "query_translation": False, "rrf_constant": 60, "bm25_k1": 1.2, "bm25_b": 0.75},
        "limitations": ["Literal normalized evidence proxy; semantic equivalents need separate human review.",
                        "Packed context is a candidate context, not yet sent to a model; no grounded answer/citation/abstention metrics.",
                        "Quality denominator excludes retrieval errors; report errors, total and scored counts together.",
                        "Shared branch rankings: hybrid search time equals BM25 + dense + fusion; initialization reported separately.",
                        "Local inference API USD=0, excludes hardware/electricity; one measurement, fixed branch order, cache may matter."],
    }
    write_json(args.output / "run.json", plan)
    started = time.perf_counter()
    before = time.perf_counter()
    lexical = BM25Retriever(chunks)
    init_times = {"bm25_seconds": time.perf_counter() - before}
    before = time.perf_counter()
    dense_error = None
    try:
        dense = DenseRetriever(args.day6_root)
    except Exception as exc:
        dense_error = type(exc).__name__
    init_times["dense_seconds"] = time.perf_counter() - before
    traces = []
    for case in cases:
        rankings, timings, errors = {}, {}, {}
        request = runtime_input(case)
        for method in ["bm25", "dense"]:
            before = time.perf_counter()
            if method == "dense" and dense_error:
                errors[method] = dense_error
                continue
            try:
                retriever = lexical if method == "bm25" else dense
                rankings[method] = retriever.search(**request, top_k=len(chunks))
                timings[method] = time.perf_counter() - before
            except Exception as exc:
                errors[method] = type(exc).__name__
        if not errors:
            before = time.perf_counter()
            rankings["hybrid"] = reciprocal_rank_fusion(rankings)
            timings["hybrid"] = sum(timings.values()) + time.perf_counter() - before
        else:
            errors["hybrid"] = "DependencyError"
        for method in ["dense", "bm25", "hybrid"]:
            if method in errors:
                trace = {"query_id": case["id"], "split": "dev", "method": method,
                         "answerable": case["answerable"], "status": "error",
                         "request": request, "error_type": errors[method],
                         "error_note": "Retrieval failed; no fake results or abstention substituted."}
            else:
                trace = evaluate_result(case, method, rankings[method], timings[method],
                                        args.budget, len(rankings[method]))
            traces.append(trace)
        # Lưu từng câu để không mất trace khi tiến trình dừng giữa chừng.
        with (args.output / "traces.jsonl").open("a", encoding="utf-8") as file:
            for trace in traces[-3:]:
                file.write(json.dumps(trace, ensure_ascii=False) + "\n")
        print(f"{case['id']}: " + ", ".join(f"{t['method']}={t['status']}" for t in traces[-3:]), flush=True)
    if any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != value for p, value in input_hashes.items()):
        raise ValueError("Đầu vào/code thay đổi trong khi chạy; giữ trace và chạy lại ở output mới")
    summary = {"split": "dev", "stage": "retrieval_only", "initialization": init_times,
               "wall_seconds": time.perf_counter() - started, "api_cost_usd": 0,
               "limitations": plan["limitations"], "metrics": summarize(traces)}
    write_json(args.output / "summary.json", summary)
    with (args.output / "metrics.csv").open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary["metrics"][0]))
        writer.writeheader()
        writer.writerows(summary["metrics"])
    report = ["# Kết quả retrieval dev — chưa chấm agent", "",
              "Metric tự động khớp evidence sau chuẩn hóa, không thay nhãn ngữ nghĩa thủ công.", "",
              "| Method | Hit@1 | Evidence Hit@3 | EvidenceSetHit@3 | Packed strict | Packed set | Errors |",
              "|---|---|---|---|---|---|---|"]
    for row in summary["metrics"]:
        n = row["answerable_scored"]
        fields = ["hit1", "hit3", "evidence_set_hit3", "packed_context_strict_hit", "packed_context_set_hit"]
        values = [f"{row[f + '_n']}/{n}" for f in fields]
        report.append("| " + " | ".join([row["method"], *values, str(row["errors"])]) + " |")
    report += ["", f"Context budget: {args.budget} ký tự, gồm nguồn. Chỉ pack top-3; chưa gửi model.",
               "", "## Giới hạn", "", *["- " + item for item in plan["limitations"]]]
    (args.output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("Saved:", args.output)
    if any(row["errors"] for row in summary["metrics"]):
        raise SystemExit("Run có lỗi retrieval; xem trace, không dùng như run hoàn chỉnh.")


if __name__ == "__main__":
    main()
