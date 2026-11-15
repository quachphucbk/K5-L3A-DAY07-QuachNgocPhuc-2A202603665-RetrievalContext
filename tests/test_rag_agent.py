import json
import unittest
from src.rag_agent import ClaudeAgentController, run_agent, validate_finish


class ScriptedController:
    """Chỉ dùng unit test, không dùng báo chất lượng model."""
    def __init__(self, actions):
        self.actions = iter(actions)
        self.requests = []

    def decide(self, system, messages, tools):
        self.requests.append(messages)
        name, arguments = next(self.actions)
        call = {"type": "tool_use", "id": f"call-{len(self.requests)}", "name": name, "input": arguments}
        return {"content": [call], "tool_call": call, "model": "unit-test-only", "usage": {"input_tokens": 2, "output_tokens": 1}}


class StubRetriever:
    def __init__(self):
        self.queries = []

    def search(self, query, *, filters=None, top_k=3):
        self.queries.append((query, filters))
        return [{"id": "c1", "source_id": "doc", "source": "url", "page": 1,
                 "text": "Enough evidence.", "metadata": {}, "score": 0.9}]


SEARCH = ("search_documents", {"query": "English rewritten query"})
ANSWER = ("finish", {"status": "answered", "answer": "Kết luận [c1]", "citations": ["c1"]})
ABSTAIN = ("finish", {"status": "abstain", "answer": "Chưa đủ bằng chứng trong kho.", "citations": []})


class AgentLoopTests(unittest.TestCase):
    def test_search_then_answer_and_usage(self):
        controller, retriever = ScriptedController([SEARCH, ANSWER]), StubRetriever()
        trace = run_agent("Vietnamese question", controller, retriever, filters={"section": "S"})
        self.assertEqual(trace["status"], "answered")
        self.assertEqual(trace["engine"], "starter.agentic.run_agent")
        self.assertEqual(trace["searches"], 1)
        self.assertEqual(trace["usage"]["input_tokens"], 4)
        self.assertEqual(retriever.queries, [("English rewritten query", {"section": "S"})])
        self.assertNotIn("gold", json.dumps(controller.requests))

    def test_adapter_implements_starter_decide_contract(self):
        provider = ScriptedController([SEARCH, ANSWER])
        adapter = ClaudeAgentController(provider, {"section": "S"})
        first = adapter.decide("Question", [])
        self.assertEqual(first["action"], "search")
        self.assertEqual(first["query"], "English rewritten query")
        history = [{"tool": "search", "queries": [first["query"]],
                    "context": "Evidence [c1]", "context_ids": ["c1"], "searches_remaining": 3}]
        second = adapter.decide("Question", history)
        self.assertEqual(second["action"], "answer")
        self.assertEqual(second["citations"], ["c1"])
        native_result = provider.requests[-1][-1]["content"][0]
        self.assertEqual(native_result["tool_use_id"], "call-1")
        self.assertEqual(json.loads(native_result["content"])["current_context_ids"], ["c1"])

    def test_cannot_finish_without_search(self):
        controller = ScriptedController([ABSTAIN, SEARCH, ABSTAIN])
        trace = run_agent("Question", controller, StubRetriever())
        self.assertEqual(trace["status"], "abstain")
        self.assertEqual(trace["searches"], 1)
        self.assertTrue(any(e["event"] == "invalid_finish" for e in trace["events"]))

    def test_invalid_citation_is_repaired_with_actual_context(self):
        invalid = ("finish", {"status": "answered", "answer": "Wrong [fake]", "citations": ["fake"]})
        controller = ScriptedController([SEARCH, invalid, ANSWER])
        trace = run_agent("Question", controller, StubRetriever())
        self.assertEqual(trace["status"], "answered")
        feedback = json.loads(controller.requests[-1][-1]["content"][0]["content"])
        self.assertEqual(feedback["current_context_ids"], ["c1"])
        self.assertIn("Enough evidence", feedback["current_context"])

    def test_contexts_are_not_accumulated_in_model_history(self):
        controller = ScriptedController([SEARCH, SEARCH, ANSWER])
        trace = run_agent("Question", controller, StubRetriever(), budget=100)
        self.assertEqual(len(controller.requests[-1]), 3)
        self.assertLessEqual(len(trace["context"]), 100)
        self.assertEqual(trace["context_ids"], ["c1"])

    def test_retrieval_error_is_not_abstention(self):
        class Broken(StubRetriever):
            def search(self, *args, **kwargs):
                raise ConnectionError("backend failed")
        trace = {}
        with self.assertRaises(ConnectionError):
            run_agent("Question", ScriptedController([SEARCH]), Broken(), trace=trace)
        self.assertEqual(trace["status"], "error")

    def test_model_limit_is_not_reported_as_semantic_abstention(self):
        trace = run_agent("Question", ScriptedController([SEARCH, SEARCH]), StubRetriever(),
                          max_searches=1, max_model_calls=2)
        self.assertEqual(trace["status"], "limit")
        self.assertEqual(trace["searches"], 1)

    def test_finish_rejects_hidden_inline_ids_and_empty_citations(self):
        with self.assertRaises(ValueError):
            validate_finish({"status": "answered", "answer": "Claim [c1] [fake]", "citations": ["c1"]}, ["c1"], True)
        with self.assertRaises(ValueError):
            validate_finish({"status": "answered", "answer": "Claim", "citations": []}, ["c1"], True)


if __name__ == "__main__":
    unittest.main()
