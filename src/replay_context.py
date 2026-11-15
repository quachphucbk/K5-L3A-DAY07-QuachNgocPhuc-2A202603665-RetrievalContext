"""So sánh context trên CÙNG top-3 đã lưu; không gọi model hay retrieval lại."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

from .benchmark_data import ROOT, evidence_set_hit, load_cases, single_chunk_hit
from .context import NeighborIndex, pack_context
from .benchmark_agent import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, default=ROOT / "results/dev-retrieval-01/traces.jsonl")
    parser.add_argument("--plan", type=Path, default=ROOT / "configs/agent-dev.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError("Chọn output mới")
    cases, chunks = load_cases(ROOT, "dev")
    by_id = {q["id"]: q for q in cases}
    rows = [json.loads(line) for line in args.traces.read_text().splitlines()]
    configs = json.loads(args.plan.read_text())["configs"]
    neighbors, counts, traces = NeighborIndex(chunks), defaultdict(lambda: {"n": 0, "strict": 0, "set": 0, "pack_seconds": 0}), []
    for row in rows:
        case = by_id[row["query_id"]]
        if row["status"] != "ok": continue
        if row["request"]["query"] != case["question"] or row["request"].get("filters") != case.get("filter"):
            raise ValueError("Trace query/filter khác benchmark")
        for config in configs:
            start = time.perf_counter()
            candidates = neighbors.expand(row["results"][:3]) if config["context_policy"] == "neighbors" else row["results"][:3]
            context, kept = pack_context(candidates, config["budget"])
            elapsed = time.perf_counter() - start
            strict, grouped = single_chunk_hit(kept, case), evidence_set_hit(kept, case)
            traces.append({"query_id": case["id"], "method": row["method"], "config_id": config["id"],
                           "context": context, "context_ids": [c["id"] for c in kept],
                           "strict_hit": strict, "set_hit": grouped, "context_chars": len(context), "pack_seconds": elapsed})
            if case["answerable"]:
                counter = counts[(row["method"], config["id"])]
                counter["n"] += 1; counter["strict"] += strict; counter["set"] += grouped
                counter["pack_seconds"] += elapsed
    summary = {"source_traces": str(args.traces), "source_sha256": hashlib.sha256(args.traces.read_bytes()).hexdigest(),
               "stage": "controlled_context_replay", "api_calls": 0,
               "meaning": "Same query/ranking per method across policies; no LLM answers, scores are literal evidence proxies.",
               "metrics": [{"method": m, "config_id": c, **values} for (m,c),values in counts.items()]}
    save(args.output / "summary.json", summary)
    save(args.output / "contexts.json", traces)
    report = ["# Context replay — cùng top-3, không gọi API", "", "| Method | Config | Strict evidence | Evidence set |", "|---|---|---|---|"]
    for row in summary["metrics"]:
        report.append(f"| {row['method']} | {row['config_id']} | {row['strict']}/{row['n']} | {row['set']}/{row['n']} |")
    (args.output / "REPORT.md").write_text("\n".join(report) + "\n")
    print("Saved", args.output)


if __name__ == "__main__": main()
