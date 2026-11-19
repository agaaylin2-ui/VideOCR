"""Pinned PaddleX inference setup shared by the screenshot and video tools."""
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path


def engine_settings(mode, adapter):
    import onnxruntime as ort

    versions = {'numpy': version('numpy'), 'onnxruntime': ort.__version__, 'paddlex': version('paddlex')}
    if versions != {'numpy': '1.26.4', 'onnxruntime': '1.24.4', 'paddlex': '3.7.0'}:
        raise RuntimeError(f'Unexpected OCR environment: {versions}')
    dml = mode == 'directml'
    provider = 'DmlExecutionProvider' if dml else 'CPUExecutionProvider'
    if provider not in ort.get_available_providers():
        raise RuntimeError(f'{provider} is unavailable')
    return provider, {
        'providers': [provider, 'CPUExecutionProvider'] if dml else [provider],
        'provider_options': [{'device_id': str(adapter)}, {}] if dml else [{}],
        'enable_mem_pattern': False, 'execution_mode': 'sequential',
    }


def ocr_pipeline(det, rec, settings):
    from paddlex import create_pipeline
    from paddlex.inference import load_pipeline_config

    config = load_pipeline_config('OCR')
    config['use_doc_preprocessor'] = False
    config['use_textline_orientation'] = False
    for kind, directory, name in [('TextDetection', det, 'PP-OCRv6_small_det'),
                                  ('TextRecognition', rec, 'PP-OCRv6_small_rec')]:
        config['SubModules'][kind].update(model_dir=str(directory.resolve()), model_name=name)
    # The pinned PaddleX checks for CUDA on device='gpu'. ORT chooses the explicit EP.
    return create_pipeline(config=config, device='cpu', engine='onnxruntime', engine_config=settings)


@contextmanager
def trace_sessions(provider, directory):
    """Intercept session construction during initialization in the dedicated OCR process."""
    import onnxruntime as ort

    sessions = []
    original = ort.InferenceSession

    def build(*args, **kwargs):
        options = kwargs['sess_options']
        options.log_severity_level = 3
        options.enable_profiling = True
        options.profile_file_prefix = str((directory / f'profile-{len(sessions)}').resolve())
        session = original(*args, **kwargs)
        session.disable_fallback()
        if session.get_providers()[0] != provider:
            raise RuntimeError(f'Expected {provider}, got {session.get_providers()}')
        sessions.append((Path(args[0]).parent.name, session))
        return session

    ort.InferenceSession = build
    try:
        yield sessions
    finally:
        ort.InferenceSession = original
