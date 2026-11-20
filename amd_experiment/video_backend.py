"""Adapt the two VideOCR image passes to the tested PaddleX/DirectML environment."""
import hashlib
import os
from contextlib import ExitStack
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from itertools import batched, groupby
from pathlib import Path
from time import perf_counter

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


def predict_video_images(images, predict, batch_size):
    from paddlex.inference.common.reader.image_reader import ReadImage

    reader = ReadImage(format='BGR')
    groups = iter(batched(images, batch_size))
    with ThreadPoolExecutor(max_workers=1) as loader:
        paths = next(groups, ())
        pending = loader.submit(reader, list(map(str, paths)))
        while paths:
            frames = pending.result()
            next_paths = next(groups, ())
            if next_paths:
                pending = loader.submit(reader, list(map(str, next_paths)))
            # Keep order and avoid padding differently sized zones or end grids.
            for (height, width, _), group in groupby(zip(paths, frames), key=lambda pair: pair[1].shape):
                limit = max(1, 4_000_000 // (width * height))
                for batch in batched(group, min(limit, batch_size)):
                    names, pixels = zip(*batch)
                    yield from zip(names, predict(list(pixels)), strict=True)
            paths = next_paths


class _VideoPass:
    def __init__(self, models, adapter, traces, detection):
        from paddlex import create_predictor

        self.detection = detection
        self.evidence = {}
        self.provider, settings = engine_settings('directml', adapter)
        settings['intra_op_num_threads'] = 1
        directory = traces / str(os.getpid())
        directory.mkdir()
        with trace_sessions(self.provider, directory) as self.sessions:
            if detection:
                self.predict = create_predictor(
                    'PP-OCRv6_small_det', model_dir=str(models / 'det'), device='cpu',
                    engine='onnxruntime', engine_config=settings, batch_size=4)
            else:
                self.predict = ocr_pipeline(models / 'det', models / 'rec', settings, batch_size=4).predict
        required = {'det'} if detection else {'det', 'rec'}
        if {kind for kind, _ in self.sessions} != required:
            raise RuntimeError('Missing expected video ONNX sessions')

    def process(self, images):
        outputs = []
        for image, result in predict_video_images(images, self.predict, 4):
            rows = list(result_rows(result, self.detection))
            for kind, session in self.sessions:
                if kind in self.evidence or (kind == 'rec' and not len(result['dt_polys'])):
                    continue
                trace = summarize_profile(Path(session.end_profiling()))
                if not trace['counts'].get(self.provider):
                    raise RuntimeError(f'{kind}: no DirectML execution was recorded.')
                self.evidence[kind] = trace
            outputs.append((image.name, rows))
        return outputs, self.evidence


def _start_worker(models, adapter, traces, detection):
    global _worker
    _worker = _VideoPass(models, adapter, traces, detection)


def _process_images(images):
    return _worker.process(images)


class DirectMLVideoBackend:
    name = 'directml'

    def __init__(self, models, adapter, diagnostics):
        self.models = models
        self.adapter = adapter
        self.diagnostics = diagnostics
        self.evidence = {}

    def run(self, args, extra_env=None):
        import psutil

        stage = args[1]
        if stage not in ('text_detection', 'ocr'):
            raise ValueError(f'Unexpected video OCR pass: {stage}')
        images = sorted(Path(args[args.index('--input') + 1]).glob('*.jpg'))
        if not images:
            raise RuntimeError(f'{stage}: VideOCR supplied no images')
        traces = self.diagnostics / stage
        traces.mkdir()
        detection = stage == 'text_detection'
        # Amortize Windows process and model startup over longer passes. Each
        # process owns its sessions and processes its GPU calls sequentially.
        images_per_worker = 128 if detection else 256
        memory_limit = max(1, psutil.virtual_memory().available // (2 * 1024 ** 3))
        workers = min(3, 1 + len(images) // images_per_worker, memory_limit)
        config = (self.models, self.adapter, traces, detection)
        evidence = self.evidence[stage] = {}
        start = perf_counter()
        print(f'{stage}: using {workers} DirectML worker(s)', flush=True)
        chunks = batched(images, 32)
        with ExitStack() as stack:
            if workers == 1:
                worker = _VideoPass(*config)
                results = map(worker.process, chunks)
            else:
                pool = stack.enter_context(ProcessPoolExecutor(
                    max_workers=workers, initializer=_start_worker, initargs=config))
                results = pool.map(_process_images, chunks)
            for outputs, sampled in results:
                evidence.update(sampled)
                for name, rows in outputs:
                    yield f'ppocr INFO: **********{name}**********'
                    for row in rows:
                        yield f'ppocr INFO: {row!r}'
        print(f'\n{stage}: {len(images)} images in {perf_counter() - start:.2f}s', flush=True)
