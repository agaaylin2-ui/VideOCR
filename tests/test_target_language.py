"""Small OCR-region fixtures exercising selection and the existing subtitle merger."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'CLI'))
from videocr.models import PredictedFrames, PredictedSubtitle
from videocr.video import Video

type Region = list[list[list[int]] | tuple[str, float]]


def box(text: str, x: int = 100, y: int = 40, width: int = 120, confidence: float = .96) -> Region:
    return [[[x, y], [x + width, y], [x + width, y + 16], [x, y + 16]], (text, confidence)]


def frame(regions: list[Region], lang: str, index: int = 0) -> PredictedFrames:
    return PredictedFrames('paddleocr', index, [regions], .75, 0, lang, True, select_target=True)


class TargetLanguageTests(unittest.TestCase):
    def assert_exports(self, regions: list[Region], en: str, ch: str, cht: str | None = None) -> None:
        for lang, expected in [('en', en), ('ch', ch), ('chinese_cht', cht if cht is not None else ch)]:
            with self.subTest(lang=lang, expected=expected):
                self.assertEqual(frame(regions, lang).text, expected)

    def test_english_above_chinese_and_confidence(self) -> None:
        regions = [box('Wait!', y=20, confidence=.84), box('等等！', confidence=.99)]
        self.assert_exports(regions, 'Wait!', '等等！')
        self.assertEqual(frame(regions, 'en').confidence, .84)
        self.assertEqual(frame(regions, 'ch').confidence, .99)

    def test_chinese_above_english(self) -> None:
        self.assert_exports([box('That was fast.'), box('來得真快。', y=20)],
                            'That was fast.', '来得真快。', '來得真快。')

    def test_same_line_separate_and_fused(self) -> None:
        self.assert_exports([box('等我！', x=240), box('Wait!')], 'Wait!', '等我！')
        for text in ('等我！ Wait!', 'Wait! 等我！', 'Wait! | 等我！'):
            self.assert_exports([box(text)], 'Wait!', '等我！')
        self.assert_exports([box('It costs 3.14! / 等我！')], 'It costs 3.14!', '等我！')
        self.assert_exports([box('等我  Wait here')], 'Wait here', '等我')
        self.assert_exports([box('他已走出那座大山(We lost sight of him)')],
                            '(We lost sight of him)', '他已走出那座大山')

    def test_chinese_only(self) -> None:
        self.assert_exports([box('門開了！')], '', '门开了！', '門開了！')

    def test_english_only(self) -> None:
        self.assert_exports([box('Open the door!'), box('噪音', confidence=.4)], 'Open the door!', '')

    def test_repeated_cues_separated_by_blank_and_non_target_frames(self) -> None:
        video = Video.__new__(Video)
        video.frame_timestamps = {n: n * 100 for n in range(11)}
        video.avg_frame_duration_ms = 100
        video.start_time_offset_ms = 0
        video.pred_frames_zone2 = []
        for lang, text in [('en', 'Again!'), ('ch', '再来！'), ('chinese_cht', '再來！')]:
            both = [box('Again!'), box('再來！', y=62)]
            only_other = [box('再來！' if lang == 'en' else 'Again!')]
            video.pred_frames_zone1 = [frame(regs, lang, i)
                                       for i, regs in [(0, both), (3, []), (5, only_other), (7, both)]]
            for pred, end in zip(video.pred_frames_zone1, (2, 4, 6, 9), strict=True):
                pred.end_index = end
            self.assertEqual(video.get_subtitles(80, .1, lang, False, .2, [None, None]),
                             f'1\n00:00:00,000 --> 00:00:00,300\n{text}\n\n'
                             f'2\n00:00:00,700 --> 00:00:01,000\n{text}\n\n')

    def test_credits_and_preview_labels(self) -> None:
        regions = [box('演員名', x=490, width=60), box('下集預告', y=1),
                   box('Directed by: John', y=78), box('Go!'), box('出發！', y=60)]
        self.assert_exports(regions, 'Go!', '出发！', '出發！')
        self.assert_exports([box('Previously we met here.')], 'Previously we met here.', '')

    def test_vertical_credit_columns_beside_dialogue(self) -> None:
        columns: list[Region] = [[[[x, 0], [x + 12, 0], [x + 12, 65], [x, 65]], (s, .98)]
                   for x, s in [(10, '音樂製作'), (40, '音效設計'), (70, '企劃製作')]]
        self.assert_exports(columns + [box('還好嗎？', x=150)], '', '还好吗？', '還好嗎？')

    def test_mixed_script_names_punctuation_and_digits(self) -> None:
        self.assert_exports([box('I trust 小明 at 8:30…')], 'I trust 小明 at 8:30…', '')
        self.assert_exports([box('讓 Team A 在 8:30 出發！')], '', '让 Team A 在 8:30 出发！', '讓 Team A 在 8:30 出發！')
        self.assert_exports([box('I trust', x=0, width=40), box('小明', x=43, width=18),
                             box('today.', x=65, width=40)], 'I trust 小明 today.', '')
        self.assert_exports([box('Room', width=38), box('７', x=140, width=12),
                             box('房間', x=260)], 'Room ７', '房间', '房間')
        self.assert_exports([box('３：２')], '３：２', '３：２')

    def test_optional_word_splitter_preserves_mixed_names_and_times(self) -> None:
        from unittest.mock import Mock
        model = Mock()
        original = 'I trust 小明 at 8:30…'
        cue = PredictedSubtitle([frame([box(original)], 'en')], 0, 80, 'en', model)
        cue.finalize_text(True)
        self.assertEqual(cue.text, original)
        model.rejoin.assert_not_called()

    def test_legacy_assembly_and_normalization_setting(self) -> None:
        regions = [[box('Yes.'), box('門', y=65)]]
        self.assertEqual(PredictedFrames('paddleocr', 0, regions, .75, 0, 'en', True).text, 'Yes.\n門')
        self.assertEqual(PredictedFrames('paddleocr', 0, regions, .75, 0, 'ch', False, select_target=True).text, '門')
