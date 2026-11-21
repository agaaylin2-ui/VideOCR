"""Run PaddleX OCR using ONNX models and record ORT node profiling."""
from __future__ import annotations

import argparse
import json
import os
from importlib.metadata import version
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--det', type=Path, required=True)
    p.add_argument('--rec', type=Path, required=True)
    p.add_argument('--provider', choices=['cpu', 'directml'], required=True)
    p.add_argument('--adapter', type=int, default=0)
    p.add_argument('--repeat', type=int, default=1)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.repeat < 1 or a.repeat > 20:
        p.error('--repeat must be between 1 and 20')
    a.out.mkdir(parents=True, exist_ok=True)
    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    import numpy as np
    import onnxruntime as ort
    from paddlex_runtime import engine_settings, ocr_pipeline, trace_sessions

    versions = {'numpy': np.__version__, 'onnxruntime': ort.__version__, 'paddlex': version('paddlex')}
    provider, settings = engine_settings(a.provider, a.adapter)
    with trace_sessions(provider, a.out) as sessions:
        pipeline = ocr_pipeline(a.det, a.rec, settings)
    outputs = []
    for _ in range(a.repeat):
        outputs = list(pipeline.predict(str(a.image.resolve()), use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False))
    if len(outputs) != 1:
        raise RuntimeError(f'Expected one OCR result, got {len(outputs)}')
    result = outputs[0]
    lines = [{'polygon': poly.tolist(), 'text': str(text), 'confidence': float(score)} for poly, text, score in zip(result['rec_polys'], result['rec_texts'], result['rec_scores'], strict=False)]
    if len(lines) != len(result['rec_texts']) or len(lines) != len(result['rec_polys']) or len(lines) != len(result['rec_scores']):
        raise RuntimeError('Inconsistent recognition result lengths')
    profiles = [{'model': name, 'file': session.end_profiling()} for name, session in sessions]
    (a.out / 'result.json').write_text(json.dumps({'provider': provider, 'repeat': a.repeat, 'versions': versions, 'detection_polygons': [poly.tolist() for poly in result['dt_polys']], 'session_providers': [x.get_providers() for _, x in sessions], 'lines': lines, 'profiles': profiles}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Processed {len(lines)} OCR lines with {provider}; inspect profiling and output.')


if __name__ == '__main__':
    main()
