import unittest
from src.benchmark_data import evidence_set_hit, runtime_input, single_chunk_hit


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.gold = {"source_id": "doc", "page": 45, "evidence": "The line is the median among low-income economies."}
        self.case = {"id": "q", "split": "dev", "question": "What line?", "answerable": True,
                     "expected_answer": "Median", "gold": [self.gold],
                     "evidence_sets": [[{**self.gold, "evidence": "The line is the median"},
                                        {**self.gold, "evidence": "among low-income economies."}]]}
        self.parts = [{"source_id": "doc", "page": 45, "text": "The line is the median"},
                      {"source_id": "doc", "page": 45, "text": "among low-income economies."}]

    def test_one_fragment_is_not_a_complete_answer(self):
        self.assertFalse(evidence_set_hit(self.parts[:1], self.case))
        self.assertTrue(evidence_set_hit(self.parts, self.case))
        self.assertFalse(single_chunk_hit(self.parts, self.case))

    def test_wrong_page_does_not_count(self):
        wrong = [{**c, "page": 46} for c in self.parts]
        self.assertFalse(evidence_set_hit(wrong, self.case))

    def test_single_chunk_normalizes_whitespace(self):
        full = {"source_id": "doc", "page": 45,
                "text": "The line is the median\n among low-income economies."}
        self.assertTrue(single_chunk_hit([full], self.case))

    def test_runtime_allowlist_blocks_labels_and_gold(self):
        self.case["filter"] = {"section": "S"}
        value = runtime_input(self.case)
        self.assertEqual(value, {"query": "What line?", "filters": {"section": "S"}})
        self.assertNotIn("answerable", value)
        self.assertNotIn("gold", value)
        self.assertNotIn("expected_answer", value)

    def test_unanswerable_is_not_a_retrieval_failure(self):
        case = {"answerable": False}
        self.assertIsNone(single_chunk_hit([], case))
        self.assertIsNone(evidence_set_hit([], case))


if __name__ == "__main__":
    unittest.main()
