"""Show frozen test evidence for review, or aggregate confirmed labels; never call the model."""
import argparse
import hashlib
import json
from pathlib import Path
from src.benchmark_data import ROOT, load_cases
from src.benchmark_agent import save
from src.review_agent import aggregate_reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "summary"])
    parser.add_argument("--run", type=Path, default=ROOT / "results/haiku-test-frozen-01")
    parser.add_argument("--config", required=True)
    parser.add_argument("--id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = json.loads((args.run / "run.json").read_text())
    if record["split"] != "test" or args.config not in record["configs_executed"]:
        raise ValueError("Expected test run and one of its frozen configs")
    if hashlib.sha256((ROOT / "benchmark/test.json").read_bytes()).hexdigest() != record["input_code_hashes"]["benchmark/test.json"]:
        raise ValueError("Test benchmark changed since execution")
    cases, _ = load_cases(ROOT, "test")
    if [q["id"] for q in cases] != record["query_ids"]:
        raise ValueError("Cases do not match the complete test run")
    if args.action == "show":
        case = next((q for q in cases if q["id"] == args.id), None)
        if case is None:
            parser.error("--id must belong to the test run")
        trace = json.loads((args.run / "traces" / args.config / f"{args.id}.json").read_text())
        print(json.dumps({"case_for_reviewer_only": case, "trace": trace}, ensure_ascii=False, indent=2))
        return
    if not args.output:
        parser.error("summary requires --output pointing to a new file")
    traces = [json.loads((args.run / "traces" / args.config / f"{q['id']}.json").read_text()) for q in cases]
    reviews = json.loads((args.run / "reviews" / f"{args.config}.json").read_text())
    report = aggregate_reviews(cases, traces, reviews)
    save(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
