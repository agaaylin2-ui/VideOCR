import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("compare_ort", Path(__file__).with_name("compare_ort.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileTests(unittest.TestCase):
    def test_counts_only_assigned_node_events(self):
        events = [
            {"cat": "Node", "name": "conv_kernel_time", "dur": 5, "args": {"provider": "DmlExecutionProvider", "op_name": "Conv"}},
            {"cat": "Node", "name": "reshape_kernel_time", "dur": 2, "args": {"provider": "CPUExecutionProvider", "op_name": "Reshape"}},
            {"cat": "Session", "dur": 900, "args": {"provider": "DmlExecutionProvider"}},
            {"cat": "Node", "args": {}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(events), encoding="utf-8")
            result = module.summarize_profile(path)
        self.assertEqual(result["node_events"], {"DmlExecutionProvider": 1, "CPUExecutionProvider": 1})
        self.assertEqual(result["node_duration_us"]["DmlExecutionProvider"], 5)
        self.assertEqual(result["nodes"][0]["op_name"], "Conv")


if __name__ == "__main__":
    unittest.main()
