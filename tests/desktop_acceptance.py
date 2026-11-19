"""Windows hardware acceptance test. Run with the packaged runtime/python.exe."""
import argparse
import os
from pathlib import Path
import runpy
import sys
import tempfile
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=Path, help='Packaged app directory')
    args = parser.parse_args()
    app = args.app.resolve()
    sys.path.insert(0, str(app))
    import cv2
    import numpy as np
    import PySimpleGUI as sg

    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        os.environ.update(APPDATA=temp, LOCALAPPDATA=temp)
        video = work / 'two areas.mp4'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'mp4v'), 10, (960, 540))
        assert writer.isOpened()
        for seconds in range(5):
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            if seconds in (1, 3):
                for text, y in [('Upper subtitle.', 100), ('Lower subtitle.', 480)]:
                    cv2.putText(frame, text, (340, y), cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                                (255, 255, 255), 2, cv2.LINE_AA)
            for _ in range(10):
                writer.write(frame)
        writer.release()
        second = work / 'second.mp4'
        import shutil
        shutil.copyfile(video, second)
        read = sg.Window.read
        step = 0
        start = time.monotonic()
        done = False

        def exercise(window, *a, **kw):
            nonlocal step, done
            # Drive the same events as the main window, after collecting real Tk values.
            if window.Title != 'VideOCR AMD':
                raise AssertionError(f'Unexpected modal dialog: {window.Title}')
            event, values = read(window, *a, **kw)
            if kw.get('timeout') != 50 or event != sg.TIMEOUT_EVENT:
                return event, values
            state = sys._getframe(1).f_globals
            if time.monotonic() - start > 150:
                raise AssertionError(f'Timed out in step {step}: {window["-OUTPUT-"].get()}')
            if step in (0, 6):
                path = str(video if step == 0 else second)
                window['-VIDEO-LIST-'].update(values=[path], value=path)
                values['-VIDEO-LIST-'] = path
                event = '-VIDEO-LIST-'
            elif step in (1, 7):
                assert state['current_image_bytes'], 'Preview frame did not decode'
                assert values['-OCR_ENGINE_COMBO-'] == state['AMD_ENGINE']
                assert str(window['--use_angle_cls'].Widget.cget('state')) == 'disabled'
                window['--send_notification'].update(False)
                window['--time_start'].update('0:00' if step == 1 else '0:03')
                window['--time_end'].update('0:03' if step == 1 else '0:05')
                window['--output'].update(str(work / ('upper.srt' if step == 1 else 'lower.srt')))
                window['-SLIDER-'].update(value=1500)
                values['-SLIDER-'] = 1500
                event = '-SLIDER-'
            elif step in (2, 3, 8, 9):
                x = 0.15 if step in (2, 8) else 0.85
                y = {2: .02, 3: .38, 8: .68, 9: .98}[step]
                values['-GRAPH-'] = (int(state['image_offset_x'] + x * state['resized_frame_width']),
                                      int(state['image_offset_y'] + y * state['resized_frame_height']))
                event = '-GRAPH-'
            elif step in (4, 10):
                event = '-GRAPH-+UP'
            elif step in (5, 11):
                assert window.crop_boxes
                event = '-BTN-ADD-BATCH-'
            elif step == 12:
                jobs = state['batch_queue']
                assert len(jobs) == 2 and jobs[0]['args']['crop_y'] < jobs[1]['args']['crop_y']
                assert all(job['args']['directml'] for job in jobs)
                event = '-BTN-RUN-'
            elif step == 13:
                if window.is_processing:
                    return event, values
                log = window['-OUTPUT-'].get()
                assert 'DirectML adapter' in log, log
                for name, text, span in [('upper', 'Upper subtitle.', '01,000 --> 00:00:02,000'),
                                         ('lower', 'Lower subtitle.', '03,000 --> 00:00:04,000')]:
                    content = (work / (name + '.srt')).read_text(encoding='utf8').strip()
                    assert content.splitlines()[-1] == text and span in content, content
                print('PASS: crop, seek, queue, settings and timed SRT on DirectML', flush=True)
                window['--output'].update(str(work / 'cancelled.srt'))
            elif step == 14:
                event = '-BTN-RUN-'
            elif step == 15:
                if not getattr(window, '_videocr_process_pid', None):
                    return event, values
                event = '-BTN-CANCEL-'
            elif step == 16:
                if window.is_processing:
                    return event, values
                assert state['batch_queue'][-1]['status'] == 'Cancelled'
                assert not (work / 'cancelled.srt').exists()
                print('PASS: cancelled extraction', flush=True)
                done = True
                event = sg.WIN_CLOSED
            step += 1
            return event, values

        sys.argv = [str(app / 'VideOCR.py'), '--amd-desktop']
        with patch.object(sg.Window, 'read', exercise):
            runpy.run_path(sys.argv[0], run_name='__main__')
        assert done

        def reopened(window, *a, **kw):
            event, values = read(window, *a, **kw)
            if kw.get('timeout') == 50:
                assert values['--time_start'] == '0:03' and values['--time_end'] == '0:05'
                return sg.WIN_CLOSED, values
            return event, values
        with patch.object(sg.Window, 'read', reopened):
            runpy.run_path(sys.argv[0], run_name='__main__')
        print('PASS: saved settings restored after reopening')


if __name__ == '__main__':
    main()
