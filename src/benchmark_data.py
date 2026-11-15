"""Bước 3: kiểm tra benchmark và chấm evidence; chỉ dùng standard library.

python -m src.benchmark_data --split dev
Không gọi retrieval hoặc agent, không chấm câu trả lời bằng LLM.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def normalize(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def matches(chunk, evidence):
    return (chunk["source_id"] == evidence["source_id"]
            and chunk["page"] == evidence["page"]
            and normalize(evidence["evidence"]) in normalize(chunk["text"]))


def single_chunk_hit(results, question):
    """Metric strict: một chunk phải chứa trọn một gold thay thế hợp lệ."""
    if not question["answerable"]:
        return None
    return any(matches(c, g) for c in results for g in question["gold"])


def evidence_set_hit(results, question):
    """Mỗi set là AND các mảnh; nhiều set là OR các cách hỗ trợ thay thế."""
    if not question["answerable"]:
        return None
    sets = question.get("evidence_sets") or [[g] for g in question["gold"]]
    return any(all(any(matches(c, e) for c in results) for e in group)
               for group in sets)


def runtime_input(question):
    """Allowlist dữ liệu agent/retrieval được thấy; không copy gold/nhãn."""
    result = {"query": question["question"]}
    if question.get("filter"):
        result["filters"] = dict(question["filter"])
    return result


def validate_cases(cases, chunks, split):
    ids = set()
    split_evidence = []
    for q in cases:
        if not isinstance(q.get("id"), str) or not q["id"].strip() or q["id"] in ids:
            raise ValueError("Query ID thiếu hoặc bị trùng")
        ids.add(q["id"])
        if q.get("split") != split or type(q.get("answerable")) is not bool:
            raise ValueError(f"{q['id']}: split/answerable không hợp lệ")
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            raise ValueError(f"{q['id']}: thiếu question")
        filters = q.get("filter", {})
        if (not isinstance(filters, dict) or set(filters) - {"section"}
                or any(not isinstance(v, str) for v in filters.values())):
            raise ValueError(f"{q['id']}: filter không hợp lệ")
        eligible = [c for c in chunks if all(c["metadata"].get(k) == v
                                           for k, v in filters.items())]
        if not q["answerable"]:
            if q.get("gold") or q.get("evidence_sets"):
                raise ValueError(f"{q['id']}: câu thiếu evidence không được có gold")
            if q.get("expected_behavior") != "search_and_abstain" or not q.get("absence_reason"):
                raise ValueError(f"{q['id']}: thiếu lý do/hành vi từ chối")
            if not q.get("absence_check"):
                raise ValueError(f"{q['id']}: thiếu cách kiểm tra toàn corpus")
            continue
        if not q.get("expected_answer") or not q.get("gold"):
            raise ValueError(f"{q['id']}: thiếu đáp án/gold")
        for evidence in q["gold"]:
            if (not isinstance(evidence.get("source_id"), str)
                    or type(evidence.get("page")) is not int
                    or not isinstance(evidence.get("evidence"), str)
                    or not normalize(evidence["evidence"])):
                raise ValueError(f"{q['id']}: gold không hợp lệ")
        groups = q.get("evidence_sets")
        if groups is not None:
            if not groups or any(not group for group in groups):
                raise ValueError(f"{q['id']}: evidence set rỗng")
            for group in groups:
                if not all(any(matches(c, e) for c in eligible) for e in group):
                    raise ValueError(f"{q['id']}: mảnh evidence không nằm trong corpus/filter")
                # Schema bước này chỉ nối mảnh trên cùng trang theo thứ tự nguồn.
                # Không tuyên bố hỗ trợ multi-hop tùy ý khi chưa có cách kiểm chứng.
                reconstructed = normalize(" ".join(e["evidence"] for e in group))
                if not any(all(e["source_id"] == g["source_id"] and e["page"] == g["page"]
                               for e in group) and reconstructed == normalize(g["evidence"])
                           for g in q["gold"]):
                    raise ValueError(f"{q['id']}: các mảnh không tái tạo trọn gold gốc")
            split_evidence.append(q["id"])
        elif not single_chunk_hit(eligible, q):
            raise ValueError(f"{q['id']}: gold không nằm trọn trong chunk; cần evidence_sets")
    counts = Counter(q["answerable"] for q in cases)
    minimum = 15 if split == "dev" else 5
    if counts[True] < minimum or counts[False] < 2:
        raise ValueError(f"{split}: cần >= {minimum} câu có đáp án và >= 2 câu thiếu evidence")
    return {"split": split, "total": len(cases), "answerable": counts[True],
            "unanswerable": counts[False], "split_evidence_ids": split_evidence}


def load_cases(root, split):
    manifest = json.loads((root / "benchmark/manifest.json").read_text())
    files = [f"benchmark/{split}.json", "data/day6_chunks.json"]
    for name in files:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if digest != manifest["files_sha256"][name]:
            raise ValueError(f"{name}: khác bản benchmark đã ghi hash")
    cases = json.loads((root / files[0]).read_text())
    chunks = json.loads((root / files[1]).read_text())
    return cases, chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    args = parser.parse_args()
    cases, chunks = load_cases(ROOT, args.split)
    print(json.dumps(validate_cases(cases, chunks, args.split), ensure_ascii=False, indent=2))
    print("Schema/evidence đã kiểm tra; chưa chạy retrieval/agent, chưa chứng nhận nhãn ngữ nghĩa.")


if __name__ == "__main__":
    main()
