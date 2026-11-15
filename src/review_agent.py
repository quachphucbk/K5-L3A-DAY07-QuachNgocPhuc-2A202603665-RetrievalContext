"""Hiển thị evidence để học viên chấm; chỉ tổng hợp khi đủ nhãn thủ công."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from .benchmark_data import ROOT, load_cases
from .benchmark_agent import save, technical_summary


def aggregate_reviews(cases, traces, reviews):
    by_trace = {t["query_id"]: t for t in traces}
    by_review = {r["query_id"]: r for r in reviews}
    if len(by_trace) != len(traces) or len(by_review) != len(reviews):
        raise ValueError("ID trace/review trùng")
    if set(by_trace) != {q["id"] for q in cases} or set(by_review) != set(by_trace):
        raise ValueError("Reviews/cases không khớp toàn bộ trace của cấu hình")
    grades, context_grades = Counter(), Counter()
    out = {"grounded_answer": {"n": 0, "mean_out_of_2": None},
           "citation_validity": {"n": 0, "N": 0}, "answer_citation_coverage": {"n": 0, "N": 0},
           "abstention": {"n": 0, "N": 0}, "false_abstention": {"n": 0, "N": 0},
           "context_sufficient_reviewed": {"n": 0, "N": 0}, "errors": 0, "limits": 0}
    for case in cases:
        t, r = by_trace[case["id"]], by_review[case["id"]]
        if t["status"] in {"error", "limit"}:
            out["errors" if t["status"] == "error" else "limits"] += 1
            continue
        if r.get("review_status") != "verified" or not r.get("reviewer") or not r.get("reviewed_at") or not r.get("reason", "").strip():
            raise ValueError(f"{case['id']}: còn pending hoặc thiếu người/ngày/lý do review")
        datetime.fromisoformat(r["reviewed_at"])
        citations = t.get("citations", [])
        support = r.get("citation_support", [])
        if len(support) != len(citations) or [c.get("id") for c in support] != citations:
            raise ValueError(f"{case['id']}: nhãn citation không đúng ID/thứ tự")
        for label in support:
            if type(label.get("supports")) is not bool or not label.get("reason", "").strip():
                raise ValueError(f"{case['id']}: mỗi citation cần true/false và lý do")
            member = label["id"] in t.get("context_ids", []) and f"[{label['id']}]" in t.get("answer", "")
            if label["supports"] and not member:
                raise ValueError(f"{case['id']}: không thể xác nhận citation ngoài context/answer")
            out["citation_validity"]["n"] += label["supports"] and member
            out["citation_validity"]["N"] += 1
        if t["status"] == "answered":
            out["answer_citation_coverage"]["N"] += 1
            out["answer_citation_coverage"]["n"] += bool(citations)
        if case["answerable"]:
            grade, context_grade = r.get("answer_grade"), r.get("context_grade")
            if type(grade) is not int or grade not in [0,1,2] or type(context_grade) is not int or context_grade not in [0,1,2]:
                raise ValueError(f"{case['id']}: answer_grade/context_grade cần 0, 1 hoặc 2")
            if t["status"] == "abstain" and grade != 0:
                raise ValueError(f"{case['id']}: từ chối câu có đáp án phải chấm answer_grade=0")
            grades[grade] += 1; context_grades[context_grade] += 1
            out["false_abstention"]["N"] += 1
            out["false_abstention"]["n"] += t["status"] == "abstain"
            out["context_sufficient_reviewed"]["N"] += 1
            out["context_sufficient_reviewed"]["n"] += context_grade == 2
        else:
            correct = r.get("abstention_correct")
            if type(correct) is not bool or (correct and t["status"] != "abstain"):
                raise ValueError(f"{case['id']}: abstention_correct cần bool khớp hành vi")
            out["abstention"]["N"] += 1
            out["abstention"]["n"] += correct
    n = sum(grades.values())
    out["grounded_answer"] = {"distribution": {str(k): grades[k] for k in [0,1,2]}, "N": n,
                              "mean_out_of_2": sum(k*v for k,v in grades.items()) / n if n else None}
    out["context_grade_distribution"] = {str(k): context_grades[k] for k in [0,1,2]}
    out["technical"] = technical_summary(traces)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "summary"])
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = json.loads((args.run / "run.json").read_text())
    if args.config not in record["configs_executed"]:
        parser.error("Config không thuộc run")
    cases, _ = load_cases(ROOT, "dev")
    cases = [q for q in cases if q["id"] in record["query_ids"]]
    by_case = {q["id"]: q for q in cases}
    if args.action == "show":
        if args.id not in by_case: parser.error("Cần --id thuộc dev của run")
        trace = json.loads((args.run / "traces" / args.config / f"{args.id}.json").read_text())
        print(json.dumps({"case_for_reviewer_only": by_case[args.id], "trace": trace}, ensure_ascii=False, indent=2))
        return
    if not args.output: parser.error("summary cần --output file mới")
    traces = [json.loads((args.run / "traces" / args.config / f"{q['id']}.json").read_text()) for q in cases]
    reviews = json.loads((args.run / "reviews" / f"{args.config}.json").read_text())
    report = aggregate_reviews(cases, traces, reviews)
    save(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
