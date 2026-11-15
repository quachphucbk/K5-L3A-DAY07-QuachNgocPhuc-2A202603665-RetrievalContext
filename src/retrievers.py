"""Bước 2: BM25, dense E5/pgvector và hybrid RRF trên cùng chunk B.

Tái sử dụng công thức/tokenizer từ exercises/hybrid-search/run.py của Day 6.
Chỉ nhận query và filter; không đọc gold, không dịch query tự động.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time
import unicodedata

from .day6_adapter import DEFAULT_DAY6, DenseRetriever, load_snapshot


def tokenize(text: str) -> list[str]:
    """Giữ số hiệu như 1.1, chuẩn hóa Unicode và chữ thường."""
    return re.findall(r"\w+(?:[./-]\w+)*", unicodedata.normalize("NFKC", text).lower())


def validate_request(query, top_k, filters):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query phải là chuỗi không rỗng")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k phải là số nguyên dương")
    if filters is not None and (
        not isinstance(filters, dict) or set(filters) - {"section"}
        or any(not isinstance(value, str) for value in filters.values())
    ):
        raise ValueError("Chỉ hỗ trợ filter section kiểu chuỗi")


class BM25Retriever:
    def __init__(self, chunks: list[dict], k1=1.2, b=0.75):
        if not chunks or len({c["id"] for c in chunks}) != len(chunks):
            raise ValueError("Corpus rỗng hoặc trùng ID")
        if not math.isfinite(k1) or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Cần k1 > 0 và 0 <= b <= 1")
        self.chunks, self.k1, self.b = chunks, k1, b
        documents = [tokenize(c["text"]) for c in chunks]
        self.lengths = [len(tokens) for tokens in documents]
        self.term_counts = [Counter(tokens) for tokens in documents]
        self.document_frequency = Counter(
            term for counts in self.term_counts for term in counts
        )
        self.average_length = sum(self.lengths) / len(chunks)

    def search(self, query: str, *, filters=None, top_k=3) -> list[dict]:
        validate_request(query, top_k, filters)
        terms = set(tokenize(query))
        results = []
        if self.average_length == 0:
            return results
        for chunk, counts, length in zip(self.chunks, self.term_counts, self.lengths):
            if filters and any(chunk["metadata"].get(k) != v for k, v in filters.items()):
                continue
            score = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if frequency == 0:
                    continue
                df = self.document_frequency[term]
                idf = math.log(1 + (len(self.chunks) - df + 0.5) / (df + 0.5))
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / self.average_length
                )
                score += idf * frequency * (self.k1 + 1) / denominator
            # Không gán thứ hạng giả cho chunk không khớp từ nào.
            if score > 0:
                results.append({**chunk, "score": score})
        return sorted(results, key=lambda c: (-c["score"], c["id"]))[:top_k]


def reciprocal_rank_fusion(rankings: dict[str, list[dict]], *, constant=60) -> list[dict]:
    """Cộng 1/(constant + rank) cho mỗi nhánh có chunk; rank bắt đầu từ 1."""
    if not isinstance(constant, int) or isinstance(constant, bool) or constant < 1:
        raise ValueError("Hằng số RRF phải là số nguyên dương")
    fused = {}
    for method, rows in rankings.items():
        seen = set()
        for rank, chunk in enumerate(rows, start=1):
            chunk_id = chunk["id"]
            if chunk_id in seen:
                raise ValueError(f"Nhánh {method} có ID trùng")
            seen.add(chunk_id)
            if chunk_id not in fused:
                fused[chunk_id] = {
                    **chunk, "score": 0.0, "component_ranks": {}, "component_scores": {}
                }
            result = fused[chunk_id]
            result["score"] += 1 / (constant + rank)
            result["component_ranks"][method] = rank
            result["component_scores"][method] = chunk["score"]
    return sorted(fused.values(), key=lambda c: (-c["score"], c["id"]))


class HybridRetriever:
    def __init__(self, lexical: BM25Retriever, dense: DenseRetriever, constant=60):
        self.lexical, self.dense, self.constant = lexical, dense, constant
        if lexical.chunks != dense.chunks:
            raise ValueError("BM25 và dense phải dùng cùng corpus B")

    def search(self, query: str, *, filters=None, top_k=3) -> list[dict]:
        validate_request(query, top_k, filters)
        # Lấy đầy đủ ứng viên của corpus nhỏ trước khi fusion, rồi mới cắt top-k.
        window = len(self.lexical.chunks)
        rankings = {
            "bm25": self.lexical.search(query, filters=filters, top_k=window),
            "dense": self.dense.search(query, filters=filters, top_k=window),
        }
        return reciprocal_rank_fusion(rankings, constant=self.constant)[:top_k]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day6-root", type=Path, default=DEFAULT_DAY6)
    parser.add_argument("--method", choices=["bm25", "dense", "hybrid", "all"], default="all")
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--section")
    parser.add_argument("--output", type=Path, help="Lưu JSON đầy đủ ranking, không ghi đè")
    args = parser.parse_args()
    filters = {"section": args.section} if args.section else None
    validate_request(args.question, args.top_k, filters)
    started = time.perf_counter()
    identity, chunks = load_snapshot(args.day6_root)
    rankings, timings = {}, {}
    if args.method in {"bm25", "hybrid", "all"}:
        before = time.perf_counter()
        lexical = BM25Retriever(chunks)
        timings["bm25_init_seconds"] = time.perf_counter() - before
        before = time.perf_counter()
        rankings["bm25"] = lexical.search(args.question, filters=filters, top_k=len(chunks))
        timings["bm25_search_seconds"] = time.perf_counter() - before
    if args.method in {"dense", "hybrid", "all"}:
        before = time.perf_counter()
        dense = DenseRetriever(args.day6_root)
        if dense.chunks != chunks:
            raise ValueError("Snapshot thay đổi trong lúc chạy")
        timings["dense_init_seconds"] = time.perf_counter() - before
        before = time.perf_counter()
        rankings["dense"] = dense.search(args.question, filters=filters, top_k=len(chunks))
        timings["dense_search_seconds"] = time.perf_counter() - before
    if args.method in {"hybrid", "all"}:
        before = time.perf_counter()
        rankings["hybrid"] = reciprocal_rank_fusion({
            "bm25": rankings["bm25"], "dense": rankings["dense"]
        })
        timings["rrf_fusion_seconds"] = time.perf_counter() - before
    timings["total_seconds"] = time.perf_counter() - started
    shown = list(rankings) if args.method == "all" else [args.method]
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": args.question, "filter": filters, "method": args.method,
        "top_k": args.top_k, "corpus_chunks": len(chunks),
        "snapshot_sha256": hashlib.sha256(
            (args.day6_root / "starter/results/ingest.json").read_bytes()
        ).hexdigest(),
        "embedding": identity,
        "configuration": {"bm25_k1": 1.2, "bm25_b": 0.75, "rrf_constant": 60,
                          "candidate_window": len(chunks), "query_translation": False,
                          "bm25_statistics": "full B corpus; filter before ranking",
                          "tie_break": "chunk ID ascending"},
        "timings": timings,
        "timing_note": "Branches run once and are shared; hybrid search cost includes both branches plus fusion. Dense search includes snapshot audit.",
        "candidate_counts": {m: len(rows) for m, rows in rankings.items()},
        "results": {m: rankings[m][:args.top_k] for m in shown},
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump({**report, "rankings": rankings}, output, ensure_ascii=False, indent=2)
            output.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
