import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'amd_experiment'))
from paddlex_runtime import trace_sessions
from video_backend import result_rows, verified_models


class Box:
    def tolist(self):
        return [[0, 0], [20, 0], [20, 10], [0, 10]]


class VideoBackendTests(unittest.TestCase):
    def test_detection_emits_real_scores(self):
        box = Box()
        rows = list(result_rows({'dt_polys': [box], 'dt_scores': [0.87]}, True))
        self.assertEqual(rows, [[box.tolist(), 0.87]])

    def test_recognition_round_trips_through_video_parser(self):
        text = """She said "it's fine"."""
        result = {'rec_polys': [Box()], 'rec_texts': [text], 'rec_scores': [0.96]}
        row, = result_rows(result, False)
        self.assertEqual(ast.literal_eval(repr(row))[1], (text, 0.96))
        result['rec_scores'] = []
        with self.assertRaises(ValueError):
            list(result_rows(result, False))

    def test_rejects_changed_model_before_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            det = Path(folder) / 'diagnostics/comparison/model-configs/det'
            det.mkdir(parents=True)
            (det / 'inference.onnx').write_bytes(b'wrong model')
            with self.assertRaisesRegex(ValueError, 'det/inference.onnx'):
                verified_models(Path(folder))

    def test_rejects_cpu_only_session_and_restores_constructor(self):
        from types import SimpleNamespace
        def cpu_session(*args, **kwargs):
            return SimpleNamespace(disable_fallback=lambda: None, get_providers=lambda: ['CPUExecutionProvider'])
        ort = SimpleNamespace(InferenceSession=cpu_session)
        with patch.dict(sys.modules, onnxruntime=ort):
            with self.assertRaisesRegex(RuntimeError, 'Expected DmlExecutionProvider'):
                with trace_sessions('DmlExecutionProvider', Path('.')):
                    ort.InferenceSession('det/inference.onnx', sess_options=SimpleNamespace())
            self.assertIs(ort.InferenceSession, cpu_session)
