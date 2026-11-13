"""Run PaddleX OCR using ONNX models and record ORT node profiling."""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
import os
import sys
from pathlib import Path


def main():
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
    from paddlex import create_pipeline
    from paddlex.inference import load_pipeline_config

    versions = {'numpy': np.__version__, 'onnxruntime': ort.__version__, 'paddlex': version('paddlex')}
    if versions != {'numpy': '1.26.4', 'onnxruntime': '1.24.4', 'paddlex': '3.7.0'}:
        raise RuntimeError(f'Unexpected package versions: {versions}')
    provider = 'DmlExecutionProvider' if a.provider == 'directml' else 'CPUExecutionProvider'
    if provider not in ort.get_available_providers():
        raise RuntimeError(f'{provider} is unavailable: {ort.get_available_providers()}')
    sessions = []
    session_models = []
    create_session = ort.InferenceSession

    def profiled_session(*args, **kwargs):
        options = kwargs['sess_options']
        options.enable_profiling = True
        options.profile_file_prefix = str((a.out / f'profile-{len(sessions)}').resolve())
        session = create_session(*args, **kwargs)
        session.disable_fallback()
        if provider not in session.get_providers():
            raise RuntimeError(f'Provider was not enabled: {session.get_providers()}')
        sessions.append(session)
        session_models.append(Path(args[0]).parent.name)
        return session

    ort.InferenceSession = profiled_session
    config = load_pipeline_config('OCR')
    config['use_doc_preprocessor'] = False
    config['use_textline_orientation'] = False
    for kind, directory, name in [('TextDetection', a.det, 'PP-OCRv6_small_det'), ('TextRecognition', a.rec, 'PP-OCRv6_small_rec')]:
        config['SubModules'][kind]['model_dir'] = str(directory.resolve())
        config['SubModules'][kind]['model_name'] = name
    settings = {'providers': [provider, 'CPUExecutionProvider'] if a.provider == 'directml' else [provider], 'provider_options': [{'device_id': str(a.adapter)}, {}] if a.provider == 'directml' else [{}], 'enable_mem_pattern': False, 'execution_mode': 'sequential'}
    # PaddleX 3.7 checks for CUDA when device_type is GPU even with explicit DML;
    # explicit provider configuration controls actual ORT execution here.
    pipeline = create_pipeline(config=config, device='cpu', engine='onnxruntime', engine_config=settings)
    outputs = []
    for _ in range(a.repeat):
        outputs = list(pipeline.predict(str(a.image.resolve()), use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False))
    if len(outputs) != 1:
        raise RuntimeError(f'Expected one OCR result, got {len(outputs)}')
    result = outputs[0]
    lines = [{'polygon': poly.tolist(), 'text': str(text), 'confidence': float(score)} for poly, text, score in zip(result['rec_polys'], result['rec_texts'], result['rec_scores'])]
    if len(lines) != len(result['rec_texts']) or len(lines) != len(result['rec_polys']) or len(lines) != len(result['rec_scores']):
        raise RuntimeError('Inconsistent recognition result lengths')
    profiles = [{'model': name, 'file': session.end_profiling()} for name, session in zip(session_models, sessions)]
    (a.out / 'result.json').write_text(json.dumps({'provider': provider, 'repeat': a.repeat, 'versions': versions, 'detection_polygons': [poly.tolist() for poly in result['dt_polys']], 'session_providers': [x.get_providers() for x in sessions], 'lines': lines, 'profiles': profiles}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Processed {len(lines)} OCR lines with {provider}; inspect profiling and output.')


if __name__ == '__main__':
    sys.exit(main())

