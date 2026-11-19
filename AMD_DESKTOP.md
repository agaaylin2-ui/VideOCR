# VideoOCR-AMD Desktop for Windows 11

Extract the complete portable **desktop ZIP** to a folder and double-click **VideOCR-AMD.exe** beside the **app** and **runtime** folders. This edition includes Python, the OCR runtime and the verified models. Keep the folders together. The smaller console preview in the repository root is a separate download.

1. Open **Process Video → Open File** and select a video with visible English subtitles.
2. Choose **PaddleOCR - AMD DirectML (RX 9070 XT)** under **OCR Engine**. Use the seek slider to find a subtitle and drag a box around the part of the frame where subtitles appear. Leave the box empty to use the bottom third.
3. Choose a new SRT filename and click **Run**. The log shows the selected adapter, and the progress bar follows extraction. You can also use **Add to Queue** to capture settings for a later job.
4. In VLC, choose **Subtitle → Add Subtitle File** to check the saved text and timing.

**Advanced Settings** includes start and end times, confidence, frame skipping and other extraction controls. The AMD model pair has been validated with upright English subtitles. Language, CUDA, angle classification, server models and annotated-image export are constrained in this mode. Existing VideOCR installations keep their original configuration. Desktop preferences are saved under the current user's VideOCR-AMD settings.

### Build from source

On Windows x64 with CPython 3.12 including Tcl/Tk, run `python windows/build_amd_desktop.py --output C:\Build\VideOCR-AMD --image-run "C:\path\to\real-image-run"`. Choose a new destination. The builder checks the two model and configuration hashes, installs the pinned wheels in the private runtime, and compiles a windowed launcher. Zip the entire output directory for distribution.

### Credits

The original desktop interface and video processing come from VideOCR and its contributors. This edition uses ONNX conversions of PaddlePaddle's PP-OCRv6 small detection and recognition models, with the original preprocessing and character dictionary. Model weights are distributed under Apache License 2.0, copied to `app/models/LICENSE.txt`. Third-party packages and Python license files are included in the private runtime.

[Detection model](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_det) · [Recognition model](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_rec)
