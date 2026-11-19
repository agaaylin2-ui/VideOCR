"""Run the Windows picker selection through VideOCR's video-to-SRT API."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def export(args):
    from video_backend import verified_models

    write_srt(args.video, args.output, verified_models(args.image_run.resolve()),
              args.adapter, args.diagnostics, ocr_engine='paddleocr', lang='en')


def export_desktop(video_path, file_path, **settings):
    from dxgi_adapters import enumerate_adapters
    from video_backend import verified_model_directory

    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    adapters = [a for a in enumerate_adapters()
                if a['vendor_id'] == '1002' and 'radeon rx 9070 xt' in a['name'].lower()]
    if len(adapters) != 1:
        raise ValueError('Windows must report exactly one Radeon RX 9070 XT for this preview.')
    adapter = adapters[0]
    print(f"Using {adapter['name']} (DirectML adapter {adapter['index']})", flush=True)
    models = verified_model_directory(Path(__file__).resolve().parents[1] / 'models')
    logs = Path(os.environ['LOCALAPPDATA']) / 'VideOCR-AMD' / 'runs'
    logs.mkdir(parents=True, exist_ok=True)
    diagnostics = Path(tempfile.mkdtemp(prefix='video-', dir=logs))
    write_srt(Path(video_path), Path(file_path), models, adapter['index'], diagnostics, **settings)


def write_srt(video, output, models, adapter, diagnostics, **settings):
    from video_backend import DirectMLVideoBackend

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'CLI'))
    from videocr import save_subtitles_to_file

    output = output.resolve()
    if output.suffix.lower() != '.srt' or output.exists():
        raise ValueError('Choose a new .srt filename. An existing file will be kept.')
    backend = DirectMLVideoBackend(models, adapter, diagnostics)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        draft = Path(temp) / 'subtitles.srt'
        try:
            save_subtitles_to_file(str(video.resolve(strict=True)), str(draft),
                                   directml_backend=backend, **settings)
        finally:
            (diagnostics / 'execution.json').write_text(json.dumps({
                'dxgi_adapter': adapter, 'sampled_node_events': backend.evidence,
            }, indent=2), encoding='utf-8')
        if not draft.stat().st_size:
            raise RuntimeError('No subtitles found in the selected area and time range.')
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
