"""Bước 1: dùng snapshot và dense retrieval thật của Day 6 (chỉ đọc).

Chạy từ root Day 7: python -m src.day6_adapter --help
Không ingest, không đọc benchmark gold, không gọi model sinh câu trả lời.
"""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

DAY6_NAME = "K5-L3A-DAY06-QuachNgocPhuc-2A202603665-DataIngestion"
DEFAULT_DAY6 = Path(__file__).resolve().parents[2] / DAY6_NAME


def convert_chunk(chunk: dict) -> dict:
    """Đổi tên trường; giữ nguyên ID, text và vị trí nguồn."""
    return {
        "id": chunk["chunk_id"],
        "source_id": chunk["document_id"],
        "source": chunk["source"],
        "page": chunk["page"],
        "text": chunk["text"],
        "metadata": dict(chunk["metadata"]),
    }


def load_snapshot(day6_root: Path) -> tuple[dict, list[dict]]:
    bundle = json.loads(
        (day6_root / "starter/results/ingest.json").read_text(encoding="utf-8")
    )
    identity = bundle["report"]["embedding"]
    expected = {
        "model": "intfloat/multilingual-e5-small",
        "dimensions": 384,
        "normalized": True,
        "document_prefix": "passage: ",
        "query_prefix": "query: ",
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise ValueError("Snapshot không đúng hợp đồng embedding E5 của Day 6")
    if not identity.get("revision"):
        raise ValueError("Snapshot thiếu revision; không tự chọn model mới nhất")
    chunks = [convert_chunk(c) for c in bundle["chunks"]["B"]]
    if not chunks or len({c["id"] for c in chunks}) != len(chunks):
        raise ValueError("Snapshot B rỗng hoặc trùng chunk ID")
    return identity, chunks


def load_backend(day6_root: Path):
    """Đặt tên riêng cho code Day 6 để không xung đột package src Day 7."""
    package_dir = day6_root / "starter/src"
    name = "_day7_day6_backend"
    if name in sys.modules:
        loaded = Path(sys.modules[name].__file__).resolve().parent
        if loaded != package_dir.resolve():
            raise ValueError("Một tiến trình chỉ dùng một backend Day 6")
    else:
        spec = importlib.util.spec_from_file_location(
            name, package_dir / "__init__.py",
            submodule_search_locations=[str(package_dir)],
        )
        if spec is None or spec.loader is None:
            raise ImportError("Không tìm thấy package Day 6")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    embedder = importlib.import_module(f"{name}.embeddings").MyEmbedder
    store = importlib.import_module(f"{name}.store").PgVectorStore
    return embedder, store


class DenseRetriever:
    """Hiện thực Retriever.search của Day 7 trên strategy B đã lưu."""

    def __init__(self, day6_root: Path):
        from dotenv import dotenv_values

        self.identity, self.chunks = load_snapshot(day6_root)
        config = dotenv_values(day6_root / "starter/.env")
        database_url = os.environ.get("DATABASE_URL") or config.get("DATABASE_URL")
        if not database_url:
            raise ValueError("Thiếu DATABASE_URL trong môi trường hoặc .env Day 6")
        embedder_class, store_class = load_backend(day6_root)
        self.embedder = embedder_class(
            self.identity["model"], self.identity["revision"]
        )
        if self.embedder.dimensions != self.identity["dimensions"]:
            raise ValueError("Số chiều query khác snapshot")
        self.store = store_class(database_url, self.embedder.dimensions)
        self.expected = {c["id"]: c for c in self.chunks}

    def search(self, query: str, *, filters=None, top_k=3) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query phải là chuỗi không rỗng")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k phải là số nguyên dương")
        vector = self.embedder.embed_query(query.strip())
        # Corpus nhỏ: đọc đủ ranking để đối chiếu snapshot, chỉ trả top-k.
        rows = self.store.search("B", vector, top_k=len(self.chunks) + 1)
        converted = [convert_chunk(row) for row in rows]
        if (len(converted) != len(self.expected)
                or {c["id"] for c in converted} != set(self.expected)
                or any(self.expected.get(c["id"]) != c for c in converted)):
            raise ValueError("Database B khác snapshot: kiểm tra lại dữ liệu Day 6")
        if filters:
            rows = self.store.search("B", vector, top_k=top_k, filters=filters)
        return [{**convert_chunk(row), "score": float(row["score"])}
                for row in rows[:top_k]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day6-root", type=Path, default=DEFAULT_DAY6)
    parser.add_argument("--export", type=Path, help="Xuất JSON chunk, không cần DB/model")
    parser.add_argument("--question", help="Query thật tới pgvector")
    parser.add_argument("--section", help="Filter từ yêu cầu người dùng, không lấy gold")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if not args.export and args.question is None:
        parser.error("Cần --export hoặc --question")
    identity, chunks = load_snapshot(args.day6_root)
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        with args.export.open("x", encoding="utf-8") as output:
            json.dump(chunks, output, ensure_ascii=False, indent=2)
            output.write("\n")
        print(f"Đã xuất {len(chunks)} chunk B → {args.export}")
    if args.question is not None:
        retriever = DenseRetriever(args.day6_root)
        results = retriever.search(
            args.question, top_k=args.top_k,
            filters={"section": args.section} if args.section else None,
        )
        print(json.dumps({"method": "dense", "embedding": identity,
                          "query": args.question, "results": results},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
