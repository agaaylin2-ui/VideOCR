"""Optional Windows hardware test using the previous verified OCR experiment."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == 'nt' and os.environ.get('VIDEOCR_TEST_AMD_VIDEO') == '1',
                     'Set VIDEOCR_TEST_AMD_VIDEO=1 on the prepared RX 9070 XT machine')
class HardwareExportTests(unittest.TestCase):
    def test_two_cues_blank_gaps_and_existing_output(self) -> None:
        import cv2
        import numpy as np

        script = Path(__file__).resolve().parents[1] / 'run-amd-video.ps1'
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / 'two cues.mp4'
            output = video.with_suffix('.srt')
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter.fourcc(*'mp4v'), 10, (960, 540))
            self.assertTrue(writer.isOpened())
            try:
                for text in ['', 'Everything is ready.', '', 'A different subtitle.', '']:
                    frame = np.zeros((540, 960, 3), dtype=np.uint8)
                    (width, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 2)
                    cv2.putText(frame, text, ((960 - width) // 2, 480), cv2.FONT_HERSHEY_SIMPLEX,
                                1.4, (255, 255, 255), 2, cv2.LINE_AA)
                    for _ in range(10):
                        writer.write(frame)
            finally:
                writer.release()
            command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                       str(script), '-Video', str(video), '-OutputFile', str(output)]
            for variable, option in [('VIDEOCR_IMAGE_RUN', '-ImageRun'), ('VIDEOCR_RUNTIME_RUN', '-RuntimeRun')]:
                if os.environ.get(variable):
                    command.extend([option, os.environ[variable]])
            subprocess.run(command, check=True, timeout=300)
            expected = ('1\n00:00:01,000 --> 00:00:02,000\nEverything is ready.\n\n'
                        '2\n00:00:03,000 --> 00:00:04,000\nA different subtitle.\n\n')
            self.assertEqual(output.read_text(encoding='utf-8'), expected)
            self.assertNotEqual(subprocess.run(command, timeout=30).returncode, 0)
            self.assertEqual(output.read_text(encoding='utf-8'), expected)
