import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "CLI/videocr/backends.py"
spec = importlib.util.spec_from_file_location("backends", path)
assert spec and spec.loader
backends = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backends)


class BackendTests(unittest.TestCase):
    def test_discovery_requires_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "paddleocr.exe"
            self.assertEqual(backends.discover_backends(str(exe), lambda *a: iter(())), {})
            exe.touch()
            self.assertEqual(list(backends.discover_backends(str(exe), lambda *a: iter(()))), ["legacy"])

    def test_auto_and_explicit_selection(self):
        backend = backends.LegacyPaddleBackend(lambda *a: iter(()))
        registry = {"legacy": backend}
        self.assertIs(backends.select_backend(registry), backend)
        self.assertIs(backends.select_backend(registry, "legacy"), backend)
        with self.assertRaises(RuntimeError):
            backends.select_backend(registry, "directml")
        self.assertIs(backends.select_backend(registry, "directml", allow_fallback=True), backend)
        with self.assertRaises(RuntimeError):
            backends.select_backend({}, "directml", allow_fallback=True)

    def test_legacy_command_and_environment_unchanged(self):
        calls = []
        def stream(*args):
            calls.append(args)
            return iter(["output"])
        backend = backends.LegacyPaddleBackend(stream)
        command = ["paddleocr", "ocr", "--device", "gpu"]
        env = {"PADDLE_PDX_LOCAL_FONT_FILE_PATH": "font"}
        self.assertEqual(list(backend.run(command, env)), ["output"])
        self.assertEqual(calls, [(command, "paddleocr_error.log", env)])
        self.assertEqual(list(backend.run(["paddleocr", "text_detection"])), ["output"])
        self.assertEqual(calls[-1], (["paddleocr", "text_detection"], "paddleocr_error.log", None))


if __name__ == "__main__":
    unittest.main()
