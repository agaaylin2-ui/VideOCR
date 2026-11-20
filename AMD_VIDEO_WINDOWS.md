# Export English subtitles on a Radeon RX 9070 XT

This Windows 11 preview turns English text visible in the bottom third of a video into a timed SubRip (.srt) file. Open it with the **VideOCR-AMD.exe** launcher. It uses the fork's VideOCR frame selection, cropping, subtitle merging and timestamps, plus the two PP-OCRv6 small models from the screenshot test.

1. Keep the folders from your successful [Windows setup](AMD_TEST_WINDOWS.md) and [real-image test](REAL_IMAGE_TEST_WINDOWS.md). The ZIP reports alone omit the models and Python packages.
2. [Download the AMD fork](https://github.com/aylinlabs/VideoOCR-AMD/archive/refs/heads/master.zip). In Downloads, right-click the new ZIP, choose **Extract All**, and pick a fresh folder.
3. Open the extracted folder and double-click **VideOCR-AMD.exe**. If you already have the two successful test folders, press **Enter**. On a new PC, install Python 3.12 x64 and 7-Zip first. Choose **1** to prepare the models, then reopen the launcher and choose **2** to prepare screenshot OCR. Reopen it and press **Enter** to export. Keep the helper scripts beside the executable.
4. Choose a short video with upright English subtitles near the bottom. Click **Open**, then **Save**. The proposed name is the video's name followed by `.amd.srt`. If it exists, choose another filename.
5. Keep the window open. The launcher looks in the project and previous VideOCR folders under Downloads. If prompted for the image test, select the successful **real-image-...** folder containing **paddlex-deps**. If prompted for the runtime, select the **run-...** folder containing **ort-env**. Both are inside an **amd-work** folder.
6. On first use the launcher downloads five hash-checked video packages to **amd-work**. Later runs reuse that cache. Wait for **VideOCR export complete**. Open the video in VLC and choose **Subtitle > Add Subtitle File** to load the new SRT. You can also open the SRT in Notepad to check its text and timestamps.

The console launcher defaults to English. In the Preview 5 source, pass `-Language ch` or `-Language chinese_cht` to `run-amd-video.ps1` to select a Chinese export.

### What has been tested

On one RX 9070 XT, the preview exported two cues from a five-second clip containing a real two-line screenshot, a second caption and blank intervals. The SRT matched the installed VideOCR CPU output in text and timestamps. Sampled ONNX Runtime traces recorded DirectML execution in both models and two CPU operations during recognition (Slice and Concat). A longer movie, faint subtitles and variable frame rates still need playback checks. CPU/CUDA users can continue using their usual VideOCR launcher.

### If extraction stops

- **No subtitles found** means the bottom-third crop yielded no accepted cues. Check that the words are visible with the player's subtitle track switched off. The preview currently uses VideOCR's default bottom-third crop and confidence threshold.
- **Model differs**, missing packages, or a missing DirectML provider means the previous test files could not be reused. Check that you kept both successful test folders. The launcher prints the folders it selected.
- Each run creates **amd-work/video-...**. **execution.json** records the selected adapter index and the sampled node counts for each stage that ran. An empty stage has no execution evidence. If a run fails, send the error text from the window and this file if it exists.

Developers can repeat the timed-cue and overwrite regression test in a Python environment with OpenCV and NumPy by setting `VIDEOCR_TEST_AMD_VIDEO=1` and running `python -m unittest discover -s tests` on the prepared Windows machine. Set `VIDEOCR_IMAGE_RUN` and `VIDEOCR_RUNTIME_RUN` when the previous runs are outside Downloads.
