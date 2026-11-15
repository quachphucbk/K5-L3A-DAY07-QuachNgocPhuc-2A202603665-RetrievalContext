import unittest
from src.costs import estimate_cost
from src.context import NeighborIndex
from src.review_agent import aggregate_reviews


def chunk(cid, start, page=1, section="S", segment=0):
    return {"id": cid, "source_id": "d", "source": "url", "page": page, "text": cid,
            "metadata": {"start": start, "section": section, "segment_start": segment}}


class ExperimentTests(unittest.TestCase):
    def test_neighbor_order_uses_offsets_and_stays_in_segment(self):
        rows = [chunk("hash-z", 0), chunk("hash-a", 10), chunk("hash-m", 20),
                chunk("other-page", 0, page=2), chunk("other-section", 30, section="T")]
        index = NeighborIndex(rows)
        self.assertEqual([c["id"] for c in index.expand([rows[1]])], ["hash-a", "hash-z", "hash-m"])
        self.assertEqual(len(index.expand([rows[1], rows[0]])), 3)

    def test_cost_uses_per_request_threshold_and_output(self):
        low = estimate_cost("claude-haiku-5-5", {"input_tokens": 1000, "output_tokens": 100})
        self.assertAlmostEqual(low["estimated_usd"], 0.00015)
        high = estimate_cost("claude-haiku-5-5", {"input_tokens": 100001, "output_tokens": 100})
        self.assertAlmostEqual(high["estimated_usd"], (100001*0.5+100*2.5)/1000000)

    def test_cache_is_separate_and_unknown_ttl_not_guessed(self):
        usage = {"input_tokens": 100, "output_tokens": 100, "cache_read_input_tokens": 1000,
                 "cache_creation_input_tokens": 1000, "cache_creation": {"ephemeral_5m_input_tokens": 1000}}
        value = estimate_cost("claude-haiku-5-5", usage)
        self.assertAlmostEqual(value["estimated_usd"], 0.000195)
        usage.pop("cache_creation")
        self.assertIsNone(estimate_cost("claude-haiku-5-5", usage))
        self.assertIsNone(estimate_cost("claude-opus-5-5", usage))

    def test_pending_review_is_not_turned_into_a_grade(self):
        cases = [{"id": "q", "answerable": True}]
        traces = [{"query_id": "q", "status": "answered", "citations": []}]
        reviews = [{"query_id": "q", "review_status": "pending"}]
        with self.assertRaisesRegex(ValueError, "pending"):
            aggregate_reviews(cases, traces, reviews)

    def test_verified_reviews_aggregate_without_scoring_backend_errors(self):
        cases = [{"id": "p", "answerable": True}, {"id": "n", "answerable": False},
                 {"id": "e", "answerable": True}]
        common = {"searches": 1, "model_calls": 2, "usage": {}, "events": [],
                  "elapsed_seconds": 1, "context_strict_hit": True, "context_set_hit": True}
        traces = [{**common, "query_id": "p", "answerable": True, "status": "answered",
                   "answer": "Claim [c1]", "citations": ["c1"], "context_ids": ["c1"]},
                  {**common, "query_id": "n", "answerable": False, "status": "abstain", "citations": []},
                  {"query_id": "e", "answerable": True, "status": "error"}]
        reviewed = {"review_status": "verified", "reviewer": "Student", "reviewed_at": "2026-11-14", "reason": "Checked source"}
        reviews = [{**reviewed, "query_id": "p", "answer_grade": 2, "context_grade": 2,
                    "citation_support": [{"id": "c1", "supports": True, "reason": "Supports claim"}]},
                   {**reviewed, "query_id": "n", "citation_support": [], "abstention_correct": True},
                   {"query_id": "e", "review_status": "not_applicable"}]
        out = aggregate_reviews(cases, traces, reviews)
        self.assertEqual(out["grounded_answer"]["N"], 1)
        self.assertEqual(out["grounded_answer"]["mean_out_of_2"], 2)
        self.assertEqual(out["citation_validity"], {"n": 1, "N": 1})
        self.assertEqual(out["abstention"], {"n": 1, "N": 1})
        self.assertEqual(out["errors"], 1)

    def test_supported_label_cannot_accept_missing_citation(self):
        cases = [{"id": "q", "answerable": True}]
        traces = [{"query_id": "q", "status": "answered", "citations": ["fake"], "context_ids": [], "answer": "[fake]"}]
        reviews = [{"query_id": "q", "review_status": "verified", "reviewer": "Student", "reviewed_at": "2026-11-14",
                    "reason": "Reviewed", "citation_support": [{"id": "fake", "supports": True, "reason": "Claim"}]}]
        with self.assertRaisesRegex(ValueError, "ngoài context"):
            aggregate_reviews(cases, traces, reviews)


if __name__ == "__main__": unittest.main()
