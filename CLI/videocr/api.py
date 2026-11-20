from __future__ import annotations

import sys

from . import utils
from .backends import OCRBackend
from .video import Video


def save_subtitles_to_file(
        video_path: str, file_path: str = 'subtitle.srt', ocr_engine: str = 'google_lens', lang: str = 'en',
        time_start: str = '0:00', time_end: str = '', conf_threshold: int = 75, sim_threshold: int = 80, max_merge_gap_sec: float = 0.1,
        use_fullframe: bool = False, use_gpu: bool = False, use_angle_cls: bool = False, use_server_model: bool = False,
        brightness_threshold: int | None = None, ssim_threshold: int = 94, subtitle_position: str = "center", frames_to_skip: int = 1,
        crop_zones: list[dict[str, int]] | None = None, ocr_image_max_width: int = 720, disable_stitching: bool = False, post_processing: bool = False,
        min_subtitle_duration_sec: float = 0.2, normalize_to_simplified_chinese: bool = True, subtitle_alignments: list[str | None] | None = None,
        save_ocr_images: bool = False, ocr_images_output_dir: str = 'ocr_images', *, directml_backend: OCRBackend | None = None) -> None:

    if crop_zones is None:
        crop_zones = []

    if subtitle_alignments is None:
        subtitle_alignments = [None, None]
    elif len(subtitle_alignments) == 1:
        subtitle_alignments.append(None)

    if directml_backend is None:
        paddleocr_path = utils.find_executable("paddleocr")
        try:
            utils.perform_hardware_check(paddleocr_path, use_gpu)
        except SystemExit as e:
            print(e, flush=True)
            sys.exit(1)

        if ocr_engine == 'paddleocr':
            det_model_dir, rec_model_dir, cls_model_dir = utils.resolve_model_dirs(lang, use_server_model)
        else:
            # For the Text-Detection-Only Pass just the default detection model is needed
            det_model_dir, rec_model_dir, cls_model_dir = utils.resolve_model_dirs('en', use_server_model)

        google_lens_path = utils.find_executable("chrome-lens")
    else:
        if (directml_backend.name != 'directml' or ocr_engine != 'paddleocr' or lang != 'en'
                or use_gpu or use_server_model or use_angle_cls or save_ocr_images):
            raise ValueError("The DirectML preview supports English with PP-OCRv6 small models and upright text only.")
        # The in-process backend owns its checked model paths. These identifiers
        # occupy the legacy command fields used by Video's two OCR passes.
        paddleocr_path, google_lens_path = 'directml', ''
        det_model_dir, rec_model_dir, cls_model_dir = 'PP-OCRv6_small_det', 'PP-OCRv6_small_rec', ''

    v = Video(video_path, paddleocr_path, det_model_dir, rec_model_dir, cls_model_dir, google_lens_path,
              ocr_backend=directml_backend)
    try:
        v.run_ocr(
            use_gpu, ocr_engine, lang, use_angle_cls, time_start, time_end, conf_threshold,
            use_fullframe, brightness_threshold, ssim_threshold, subtitle_position,
            frames_to_skip, crop_zones, ocr_image_max_width, disable_stitching,
            normalize_to_simplified_chinese, save_ocr_images, ocr_images_output_dir
        )
    except Exception as e:
        print(f"\nError: {e}", flush=True)
        sys.exit(1)
    subtitles = v.get_subtitles(sim_threshold, max_merge_gap_sec, lang, post_processing, min_subtitle_duration_sec, subtitle_alignments)

    with open(file_path, 'w+', encoding='utf-8') as f:
        f.write(subtitles)
