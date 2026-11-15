import unittest
from src.benchmark_retrieval import evaluate_result, summarize
from src.context import pack_context


class RetrievalBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.chunk = {"id": "a", "source_id": "doc", "source": "url", "page": 1,
                      "text": "Complete evidence.", "metadata": {}, "score": 0.9}
        self.case = {"id": "q", "split": "dev", "answerable": True, "question": "Question",
                     "expected_answer": "Answer", "gold": [{"source_id": "doc", "page": 1,
                                                                 "evidence": "Complete evidence."}]}

    def test_packing_can_lose_evidence_after_retrieval_hit(self):
        trace = evaluate_result(self.case, "dense", [self.chunk], 0.01, 1, 1)
        self.assertTrue(trace["hit3"])
        self.assertFalse(trace["packed_context_strict_hit"])
        self.assertEqual(trace["context"], "")
        self.assertNotIn("gold", trace["request"])

    def test_errors_and_unanswerable_do_not_enter_quality_denominator(self):
        success = evaluate_result(self.case, "dense", [self.chunk], 0.01, 800, 1)
        negative = {"id": "negative", "answerable": False, "question": "Absent"}
        other = evaluate_result(negative, "dense", [self.chunk], 0.01, 800, 1)
        failure = {"query_id": "failed", "method": "dense", "answerable": True, "status": "error"}
        row = summarize([success, other, failure])[0]
        self.assertEqual(row["answerable_total"], 2)
        self.assertEqual(row["answerable_scored"], 1)
        self.assertEqual(row["errors"], 1)
        self.assertEqual(row["hit3_rate"], 1)
        self.assertIsNone(other["hit3"])

    def test_context_deduplicates_and_counts_source_headers(self):
        context, kept = pack_context([self.chunk, self.chunk], 800)
        self.assertEqual(len(kept), 1)
        self.assertIn("page 1", context)
        context2, kept2 = pack_context([self.chunk], len(context) - 1)
        self.assertEqual((context2, kept2), ("", []))

    def test_skipping_large_chunk_does_not_block_later_small_one(self):
        large = {**self.chunk, "id": "large", "text": "x" * 1000}
        _, kept = pack_context([large, self.chunk], 100)
        self.assertEqual([c["id"] for c in kept], ["a"])


if __name__ == "__main__":
    unittest.main()
