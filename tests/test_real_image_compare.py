import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'amd_experiment'))
from real_image_compare import parse_paddle, parse_paddle_detection, summarize_profile


class RealImageComparisonTests(unittest.TestCase):
    def test_parse_paddle_result_and_reject_unexpected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'output.txt'
            path.write_text("[date] ppocr INFO: [[[1, 2], [3, 2], [3, 4], [1, 4]], ('Hello', 0.9)]\n", encoding='utf8')
            self.assertEqual(parse_paddle(path)[0]['text'], 'Hello')
            path.write_text('[date] ppocr INFO: [[not a literal]]\n', encoding='utf8')
            with self.assertRaises((ValueError, SyntaxError)):
                parse_paddle(path)

    def test_parse_detection_confidence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'det.txt'
            path.write_text('[date] ppocr INFO: [[[1, 2], [3, 2], [3, 4], [1, 4]], (0.85)]\n', encoding='utf8')
            self.assertEqual(parse_paddle_detection(path)[0]['confidence'], 0.85)

    def test_profile_reports_cpu_fallback_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'trace.json'
            path.write_text('[{"cat":"Node","args":{"provider":"DmlExecutionProvider","op_name":"Conv"}},{"cat":"Node","args":{"provider":"CPUExecutionProvider","op_name":"Shape"}}]', encoding='utf8')
            result = summarize_profile(path)
            self.assertEqual(result['counts']['DmlExecutionProvider'], 1)
            self.assertEqual(result['cpu_fallback_operations'], {'Shape': 1})


if __name__ == '__main__':
    unittest.main()
