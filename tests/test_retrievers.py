import unittest
from src.retrievers import BM25Retriever, reciprocal_rank_fusion, tokenize


def chunk(identifier, text, section="A"):
    return {"id": identifier, "source_id": "doc", "source": "local",
            "page": 1, "text": text, "metadata": {"section": section}}


class RetrieverTests(unittest.TestCase):
    def test_numbered_reference_is_preserved(self):
        self.assertEqual(tokenize("BOX 1.1"), ["box", "1.1"])

    def test_bm25_does_not_return_zero_matches(self):
        retriever = BM25Retriever([chunk("a", "food energy"), chunk("b", "poverty")])
        self.assertEqual(retriever.search("khôngkhớp"), [])
        self.assertEqual([c["id"] for c in retriever.search("energy")], ["a"])

    def test_filter_and_deterministic_tie_break(self):
        retriever = BM25Retriever([chunk("b", "food", "B"), chunk("a", "food", "A")])
        self.assertEqual([c["id"] for c in retriever.search("food")], ["a", "b"])
        self.assertEqual([c["id"] for c in retriever.search(
            "food", filters={"section": "B"})], ["b"])
        with self.assertRaises(ValueError):
            retriever.search("food", filters={"gold_page": 1})

    def test_rrf_uses_ranks_not_raw_scores(self):
        a, b = {**chunk("a", "A"), "score": 1000}, {**chunk("b", "B"), "score": 1}
        dense = [{**b, "score": 0.9}, {**a, "score": 0.8}]
        fused = reciprocal_rank_fusion({"bm25": [a, b], "dense": dense})
        self.assertEqual([c["id"] for c in fused], ["a", "b"])
        self.assertAlmostEqual(fused[0]["score"], 1 / 61 + 1 / 62)
        self.assertEqual(fused[0]["component_ranks"], {"bm25": 1, "dense": 2})
        self.assertEqual(a["score"], 1000)

    def test_rrf_missing_branch_keeps_dense_order(self):
        rows = [{**chunk("b", "B"), "score": 0.9}, {**chunk("a", "A"), "score": 0.8}]
        fused = reciprocal_rank_fusion({"bm25": [], "dense": rows})
        self.assertEqual([c["id"] for c in fused], ["b", "a"])
        self.assertEqual(fused[0]["component_ranks"], {"dense": 1})
        self.assertAlmostEqual(fused[0]["score"], 1 / 61)

    def test_rrf_rejects_duplicate_ids_within_branch(self):
        row = {**chunk("a", "A"), "score": 1}
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({"bm25": [row, row]})


if __name__ == "__main__":
    unittest.main()
