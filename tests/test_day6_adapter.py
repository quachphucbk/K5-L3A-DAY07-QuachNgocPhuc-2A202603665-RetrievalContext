"""Kiểm tra hợp đồng dữ liệu, không dùng mock làm benchmark."""
import json
from pathlib import Path
import tempfile
import unittest
from src.day6_adapter import convert_chunk, load_snapshot


class AdapterTests(unittest.TestCase):
    def test_mapping_preserves_source_and_does_not_copy_gold(self):
        original = {"chunk_id": "c1", "document_id": "d1", "source": "url",
                    "page": 47, "text": "Evidence", "metadata": {"section": "S"},
                    "gold": "secret label"}
        result = convert_chunk(original)
        self.assertEqual(result["id"], "c1")
        self.assertEqual(result["source_id"], "d1")
        self.assertEqual(result["page"], 47)
        self.assertNotIn("gold", result)
        result["metadata"]["section"] = "changed"
        self.assertEqual(original["metadata"]["section"], "S")

    def test_incompatible_embedding_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "starter/results/ingest.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"report": {"embedding": {"dimensions": 768}}}))
            with self.assertRaisesRegex(ValueError, "embedding"):
                load_snapshot(Path(directory))
