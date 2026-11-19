"""Adapt the two VideOCR image passes to the tested PaddleX/DirectML environment."""
import hashlib
from pathlib import Path

from paddlex_runtime import engine_settings, ocr_pipeline, trace_sessions
from real_image_compare import summarize_profile


def verified_models(image_run):
    return verified_model_directory(image_run / "diagnostics" / "comparison" / "model-configs")


def verified_model_directory(models):
    # SHA-256 of the exact exports and preprocessing/decoder configs from the
    # reference RX 9070 XT run. Reject swapped models or a different dictionary.
    expected = {
        'det': ('b1a4f07289eda88d29239890b94ea2f9e29f5635a33ff6e165bb1b27dcea25fc',
                '193f435274bf9f0b5f71a929bbfbcf148282df7e633b34e7c373e8f44741b516'),
        'rec': ('7a10319171913a664e03b9f84bb159dbc1c7c397a2ff7a79d89287df64c64d4b',
                'ab078671bb49f06228eadccd34f1bb501e157f7a047095ffb943ba81512c77d1'),
    }
    for kind, hashes in expected.items():
        for filename, digest in zip(('inference.onnx', 'inference.yml'), hashes):
            with (models / kind / filename).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    raise ValueError(f'The {kind}/{filename} file differs from the tested model.')
    return models


def result_rows(result, detection):
    if detection:
        for box, score in zip(result['dt_polys'], result['dt_scores'], strict=True):
            yield [box.tolist(), float(score)]
    else:
        for box, text, score in zip(result['rec_polys'], result['rec_texts'], result['rec_scores'], strict=True):
            yield [box.tolist(), (str(text), float(score))]


class DirectMLVideoBackend:
    name = 'directml'

    def __init__(self, models, adapter, diagnostics):
        self.models = models
        self.provider, self.settings = engine_settings('directml', adapter)
        self.diagnostics = diagnostics
        self.evidence = {}

    def run(self, args, extra_env=None):
        from paddlex import create_predictor

        stage = args[1]
        if stage not in ('text_detection', 'ocr'):
            raise ValueError(f'Unexpected video OCR pass: {stage}')
        detection = stage == 'text_detection'
        images = sorted(Path(args[args.index('--input') + 1]).glob('*.jpg'))
        if not images:
            raise RuntimeError(f'{stage}: VideOCR supplied no images')
        traces = self.diagnostics / stage
        traces.mkdir()
        with trace_sessions(self.provider, traces) as sessions:
            if detection:
                predict = create_predictor('PP-OCRv6_small_det', model_dir=str(self.models / 'det'),
                                          device='cpu', engine='onnxruntime', engine_config=self.settings)
            else:
                predict = ocr_pipeline(self.models / 'det', self.models / 'rec', self.settings).predict
        required = {'det'} if detection else {'det', 'rec'}
        if {kind for kind, _ in sessions} != required:
            raise RuntimeError(f'{stage}: missing expected ONNX sessions')
        self.evidence[stage] = {}
        for image in images:
            result, = predict(str(image))
            rows = list(result_rows(result, detection))
            # Stop profiling each model once it has had input, keeping traces small.
            for kind, session in sessions:
                if kind in self.evidence[stage] or (kind == 'rec' and not len(result['dt_polys'])):
                    continue
                trace = summarize_profile(Path(session.end_profiling()))
                if not trace['counts'].get(self.provider):
                    raise RuntimeError(f'{stage}/{kind}: no DirectML execution was recorded.')
                self.evidence[stage][kind] = trace
            yield f'ppocr INFO: **********{image.name}**********'
            for row in rows:
                yield f'ppocr INFO: {row!r}'
