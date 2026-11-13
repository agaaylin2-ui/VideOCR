"""Compare real-image OCR paths; optional .txt sidecars provide ground truth."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ocr_metrics import character_error_rate, match_boxes, normalize


def parse_paddle(log: Path) -> list[dict]:
    lines = []
    for line in log.read_text(encoding='utf-8').splitlines():
        if 'ppocr INFO:' not in line or '[[' not in line:
            continue
        payload = line.split('ppocr INFO:', 1)[1].strip()
        value = ast.literal_eval(payload)
        if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], (tuple, list)):
            raise ValueError('Unexpected PaddleOCR output')
        lines.append({'polygon': value[0], 'text': str(value[1][0]), 'confidence': float(value[1][1])})
    return lines


def parse_paddle_detection(log: Path) -> list[dict]:
    boxes = []
    for line in log.read_text(encoding='utf8').splitlines():
        if 'ppocr INFO:' not in line or '[[' not in line:
            continue
        value = ast.literal_eval(line.split('ppocr INFO:', 1)[1].strip())
        if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], (int, float)):
            raise ValueError('Unexpected Paddle detection output')
        boxes.append({'polygon': value[0], 'text': '', 'confidence': float(value[1])})
    return boxes


def summarize_profile(path: Path) -> dict:
    counts: dict[str, int] = {}
    cpu_ops: dict[str, int] = {}
    for event in json.loads(path.read_text(encoding='utf-8')):
        provider = event.get('args', {}).get('provider')
        if event.get('cat') == 'Node' and provider:
            counts[provider] = counts.get(provider, 0) + 1
            if provider == 'CPUExecutionProvider':
                op = event.get('args', {}).get('op_name', event.get('name', 'unknown'))
                cpu_ops[op] = cpu_ops.get(op, 0) + 1
    return {'counts': counts, 'cpu_fallback_operations': cpu_ops}


def run(command: list[str], log: Path) -> None:
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log.write_text('COMMAND: ' + subprocess.list2cmdline(command) + '\n\nSTDOUT:\n' + process.stdout + '\nSTDERR:\n' + process.stderr, encoding='utf-8')
    if process.returncode:
        raise RuntimeError(f'{log.name} failed (exit {process.returncode}); see log')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path, help='Previous successful amd-work/run-* folder')
    parser.add_argument('--images', required=True, nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--adapter', required=True, type=int)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report: dict = {'scope': 'Real images; compare decoded OCR and ORT provider traces. Real GPU activity requires independent observation.', 'samples': [], 'status': 'UNVERIFIED', 'coverage': 'UNVERIFIED: manually confirm clear, small, multiline and difficult backgrounds are represented'}
    root = args.run.resolve(strict=True)
    executables = list((root / 'runtime').rglob('paddleocr.exe'))
    models = list((root / 'models').rglob('PaddleOCR.PP-OCRv6.support.files'))
    if len(executables) != 1 or len(models) != 1:
        raise RuntimeError('Could not uniquely locate previous CPU executable and model archive')
    model_root = models[0]
    baseline_manifest = json.loads((root / 'diagnostics' / 'cpu-baseline' / 'baseline.json').read_text(encoding='utf8'))
    export_manifest = json.loads((root / 'onnx' / 'export_manifest.json').read_text(encoding='utf8'))
    def file_sha(path):
        with path.open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    if file_sha(executables[0]) != baseline_manifest['inputs']['executable']:
        raise RuntimeError('CPU executable differs from the earlier verified run')
    report['input_hashes'] = {'paddle_executable_sha256': baseline_manifest['inputs']['executable'], 'models': {kind: {'source': export_manifest[kind]['source_files'], 'onnx_sha256': export_manifest[kind]['onnx_sha256']} for kind in ('det', 'rec')}}
    model_dirs = {}
    for kind in ('det', 'rec'):
        source = root / 'onnx' / kind / 'inference.onnx'
        config = model_root / kind / f'PP-OCRv6_small_{kind}' / 'inference.yml'
        source_model = model_root / kind / f'PP-OCRv6_small_{kind}'
        for relative, expected in export_manifest[kind]['source_files'].items():
            if file_sha(source_model / relative) != expected:
                raise RuntimeError(f'Original model file changed: {kind}/{relative}')
        if file_sha(source) != export_manifest[kind]['onnx_sha256']:
            raise RuntimeError(f'ONNX model changed: {kind}')
        target = args.out / 'model-configs' / kind
        target.mkdir(parents=True, exist_ok=True)
        # Copy into the scratch directory without changing the original models.
        for original in (source, config):
            if not original.is_file():
                raise FileNotFoundError(original)
            destination = target / original.name
            if not destination.exists():
                shutil.copy2(original, destination)
        model_dirs[kind] = target
    worker = Path(__file__).with_name('real_image_worker.py')
    for index, image in enumerate(args.images, 1):
        sample = {'image': str(image.resolve()), 'image_sha256': file_sha(image), 'status': 'UNVERIFIED'}
        report['samples'].append(sample)
        folder = args.out / f'sample-{index:02d}'
        folder.mkdir(parents=True, exist_ok=True)
        try:
            run([sys.executable, str(Path(__file__).with_name('baseline.py')), '--exe', str(executables[0]), '--models', str(model_root), '--image', str(image), '--out', str(folder / 'paddle')], folder / 'paddle.log')
            reference = parse_paddle(folder / 'paddle' / 'ocr.stdout.txt')
            sample['paddle_cpu'] = reference
            paddle_detection = parse_paddle_detection(folder / 'paddle' / 'detection.stdout.txt')
            sample['paddle_detection_only'] = paddle_detection
            sample['paths'] = {}
            for mode in ('cpu', 'directml'):
                directory = folder / mode
                run([sys.executable, str(worker), '--image', str(image), '--det', str(model_dirs['det']), '--rec', str(model_dirs['rec']), '--provider', mode, '--adapter', str(args.adapter), '--repeat', '8' if mode == 'directml' else '1', '--out', str(directory)], folder / f'{mode}.log')
                data = json.loads((directory / 'result.json').read_text(encoding='utf-8'))
                traces = [{'model': profile['model'], **summarize_profile(Path(profile['file']))} for profile in data['profiles']]
                if len(traces) < 2:
                    raise RuntimeError('Expected separate detection and recognition ORT sessions')
                if mode == 'directml' and any(t['counts'].get('DmlExecutionProvider', 0) == 0 for t in traces):
                    raise RuntimeError('No DirectML nodes recorded in one or more sessions')
                lines = data['lines']
                ref_text = '\n'.join(x['text'] for x in reference)
                got_text = '\n'.join(x['text'] for x in lines)
                boxes = match_boxes(reference, lines)
                cer = character_error_rate(ref_text, got_text)
                parity = bool(reference) and cer is not None and cer <= 0.01 and not boxes['missing_reference'] and not boxes['extra_candidate'] and all(x['iou'] >= 0.9 for x in boxes['matches'])
                detector_boxes = match_boxes(paddle_detection, [{'polygon': p, 'text': '', 'confidence': 0.0} for p in data['detection_polygons']])
                for pair in detector_boxes['matches']:
                    pair.pop('confidence_delta')
                    pair.pop('text_equal')
                sample['paths'][mode] = {'parity_status': 'PASS' if parity else 'FAIL', 'versions': data['versions'], 'repeat': data['repeat'], 'lines': lines, 'boxes': boxes, 'detection_polygons': data['detection_polygons'], 'detection_only_comparison': detector_boxes, 'cer_vs_paddle': cer, 'node_events_per_session': traces}
            transcript = image.with_suffix('.txt')
            if transcript.exists():
                truth = transcript.read_text(encoding='utf-8-sig')
                sample['ground_truth'] = {'paddle_cpu_cer': character_error_rate(truth, '\n'.join(x['text'] for x in reference)), **{mode + '_cer': character_error_rate(truth, '\n'.join(x['text'] for x in sample['paths'][mode]['lines'])) for mode in ('cpu', 'directml')}}
                for key, value in list(sample['ground_truth'].items()):
                    if value is not None:
                        sample['ground_truth'][key.replace('_cer', '_character_accuracy_percent')] = max(0.0, 1.0 - value) * 100
            else:
                sample['ground_truth'] = 'UNVERIFIED: no same-name .txt transcript supplied'
            sample['status'] = 'UNVERIFIED: parity gates are provisional; inspect ground truth and physical GPU activity'
        except Exception as exc:
            sample['status'] = 'FAIL'
            sample['error'] = f'{type(exc).__name__}: {exc}'
    summary = ['REAL-IMAGE OCR COMPARISON', 'Sample coverage: UNVERIFIED; manually confirm clear, small, multiline and difficult backgrounds.', 'DirectML inference is repeated eight times per image to make GPU activity easier to observe; profiles include all repeats.', 'OCR accuracy against human transcript and physical GPU activity: UNVERIFIED unless separately checked.', 'Provisional parity gate: CER vs Paddle <= 1%, no unmatched recognition boxes, and axis-aligned box IoU >= 0.9.', '']
    for sample in report['samples']:
        summary.append(f"{sample['image']}: {sample['status']}")
        if 'error' in sample:
            summary.append('  Error: ' + sample['error'])
        for line in sample.get('paddle_cpu', []):
            summary.append(f"  Paddle CPU: {line['text']!r} confidence={line['confidence']:.4f} polygon={line['polygon']}")
        summary.append('  Paddle detection-only polygons: ' + str(sample.get('paddle_detection_only', [])))
        for mode, data in sample.get('paths', {}).items():
            summary.append(f"  {mode}: {data['parity_status']}; CER vs Paddle={data['cer_vs_paddle']}; boxes={data['boxes']}; provider node events={data['node_events_per_session']}")
            summary.append('    Detector polygons: ' + str(data['detection_polygons']))
            summary.append('    Detection-only comparison (settings can differ from full OCR): ' + str(data['detection_only_comparison']))
            for line in data['lines']:
                summary.append(f"    {line['text']!r} confidence={line['confidence']:.4f} polygon={line['polygon']}")
        summary.append('  Human transcript: ' + str(sample.get('ground_truth', 'UNVERIFIED')))
        summary.append('')
    (args.out / 'report.txt').write_text('\n'.join(summary), encoding='utf-8')
    (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return int(any(s['status'] == 'FAIL' or any(p['parity_status'] == 'FAIL' for p in s.get('paths', {}).values()) for s in report['samples']))


if __name__ == '__main__':
    sys.exit(main())
