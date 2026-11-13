import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('ocr_metrics', Path(__file__).resolve().parents[1] / 'amd_experiment/ocr_metrics.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def item(x, text, score=0.9):
    return {'polygon': [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]], 'text': text, 'confidence': score}


class MetricsTests(unittest.TestCase):
    def test_character_error_and_normalization(self):
        self.assertEqual(metrics.character_error_rate('cafe\u0301 hi', 'café  hi'), 0)
        self.assertEqual(metrics.character_error_rate('abc', 'axc'), 1 / 3)
        self.assertIsNone(metrics.character_error_rate('', 'anything'))

    def test_matches_are_one_to_one_and_report_unmatched(self):
        result = metrics.match_boxes([item(0, 'hello'), item(20, 'other')], [item(0, 'hello', .8), item(100, 'extra')])
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['missing_reference'], [1])
        self.assertEqual(result['extra_candidate'], [1])
        self.assertAlmostEqual(result['matches'][0]['confidence_delta'], -.1)
        self.assertTrue(result['matches'][0]['text_equal'])

    def test_no_overlap(self):
        self.assertEqual(metrics.box_iou(item(0, '')['polygon'], item(20, '')['polygon']), 0)


if __name__ == '__main__':
    unittest.main()
