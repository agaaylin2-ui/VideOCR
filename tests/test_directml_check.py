import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'amd_experiment' / 'check_directml.py'


class ProviderCheckTests(unittest.TestCase):
    def run_check(self, providers):
        with tempfile.TemporaryDirectory(prefix='provider test ') as tmp:
            root = Path(tmp)
            (root / 'numpy.py').write_text('', encoding='utf-8')
            (root / 'onnxruntime.py').write_text('def get_available_providers():\n    return ' + repr(providers) + '\n', encoding='utf-8')
            # Copy the script beside stub modules, so imports are isolated from installed ORT.
            script = root / 'check directml.py'
            script.write_text(SCRIPT.read_text(encoding='utf-8-sig'), encoding='utf-8')
            return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)

    def test_available(self):
        result = self.run_check(['DmlExecutionProvider', 'CPUExecutionProvider'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DmlExecutionProvider', result.stdout)

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell regression')
    def test_windows_powershell_path_and_arguments(self):
        with tempfile.TemporaryDirectory(prefix='provider test ') as tmp:
            root = Path(tmp)
            (root / 'numpy.py').write_text('', encoding='utf-8')
            (root / 'onnxruntime.py').write_text("def get_available_providers():\n    return ['DmlExecutionProvider']\n", encoding='utf-8')
            script = root / 'check directml.py'
            script.write_text(SCRIPT.read_text(encoding='utf-8-sig'), encoding='utf-8')
            wrapper = Path(__file__).with_name('invoke_provider_check.ps1')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(wrapper), '-Python', sys.executable, '-Check', str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('DmlExecutionProvider', result.stdout)

    def test_missing(self):
        result = self.run_check(['CPUExecutionProvider'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not available', result.stderr)


if __name__ == '__main__':
    unittest.main()
