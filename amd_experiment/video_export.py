"""Run the Windows picker selection through VideOCR's video-to-SRT API."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def export(args):
    from video_backend import DirectMLVideoBackend, verified_models

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'CLI'))
    from videocr import save_subtitles_to_file

    output = args.output.resolve()
    if output.suffix.lower() != '.srt' or output.exists():
        raise ValueError('Choose a new .srt filename. An existing file will be kept.')
    models = verified_models(args.image_run.resolve())
    backend = DirectMLVideoBackend(models, args.adapter, args.diagnostics)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        draft = Path(temp) / 'subtitles.srt'
        try:
            save_subtitles_to_file(str(args.video.resolve(strict=True)), str(draft),
                                   ocr_engine='paddleocr', lang='en', directml_backend=backend)
        finally:
            (args.diagnostics / 'execution.json').write_text(json.dumps({
                'dxgi_adapter': args.adapter, 'sampled_node_events': backend.evidence,
            }, indent=2), encoding='utf-8')
        if not draft.stat().st_size:
            raise RuntimeError('No subtitles found in the bottom third of the video. Try a clip with visible English subtitles.')
        if 'rec' not in backend.evidence.get('ocr', {}):
            raise RuntimeError('Recognition lacked a recorded DirectML execution.')
        # Windows rename fails if another export created the destination meanwhile.
        draft.rename(output)
    print(f'Saved subtitles: {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for option in ('video', 'output', 'image-run', 'diagnostics'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--adapter', type=int, required=True)
    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    export(parser.parse_args())
