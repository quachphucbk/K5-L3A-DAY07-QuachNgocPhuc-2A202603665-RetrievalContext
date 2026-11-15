import io
import json
import unittest
from src.model_controller import ClaudeController


class ControllerContractTests(unittest.TestCase):
    def test_request_uses_auto_without_deprecated_temperature(self):
        recorded = {}
        class Opener:
            def open(self, request, timeout):
                recorded.update(json.loads(request.data))
                call = {"type": "tool_use", "id": "call1", "name": "search_documents", "input": {"query": "q"}}
                return io.BytesIO(json.dumps({"stop_reason": "tool_use", "model": "unit-test",
                                               "content": [call], "usage": {"input_tokens": 1}}).encode())
        controller = object.__new__(ClaudeController)
        controller.key = "unit-test-key"
        controller.model = "unit-test"
        controller.opener = Opener()
        result = controller.decide("system", [{"role": "user", "content": "question"}], [])
        self.assertEqual(recorded["tool_choice"]["type"], "auto")
        self.assertNotIn("temperature", recorded)
        self.assertEqual(result["tool_call"]["name"], "search_documents")


if __name__ == "__main__":
    unittest.main()
