# VideOCR AMD

The **AMD Desktop** build opens the original VideOCR interface with video preview, crop boxes, Advanced Settings, queue and progress. Its portable folder includes the DirectML runtime and PP-OCRv6 small models. [Desktop edition and build instructions](AMD_DESKTOP.md)

## Console preview

Turn English subtitles burned into a video into a timed SubRip (.srt) file on Windows 11. This fork adds local GPU recognition using ONNX Runtime DirectML and PaddleOCR's PP-OCRv6 small models. The Windows preview has been tested on the **AMD Radeon RX 9070 XT (16 GB)**.

### Run the console preview on Windows

1. [Download the ZIP from this fork](https://github.com/agaaylin2-ui/VideOCR/archive/refs/heads/master.zip). In Downloads, right-click the ZIP and choose **Extract All**.
2. Open the extracted folder and double-click **VideOCR-AMD.exe**. Keep the executable and the accompanying folders together.
3. If you already ran both AMD setup tests, press **Enter**, pick a video and save the suggested subtitle file. For a first installation, install Python 3.12 x64 and 7-Zip, then choose **1** and **2** on successive launches. Each setup step asks for a subtitle screenshot and permission to download dependencies.
4. Open the video in VLC and choose **Subtitle → Add Subtitle File** to see the result. The preview looks for upright English text in the bottom third of the picture.

[Windows setup and troubleshooting](AMD_VIDEO_WINDOWS.md) · [Model setup](AMD_TEST_WINDOWS.md) · [Screenshot comparison](REAL_IMAGE_TEST_WINDOWS.md)

## Hardware and accuracy

| Path | What we have tested |
| --- | --- |
| Windows 11, RX 9070 XT, DirectML | A two-line subtitle image and short MP4 exports. The reference clip produced the same SRT text and timestamps as the original CPU executable. Runtime profiles recorded GPU work in detection and recognition, with two recognition operations on CPU. |
| Other Radeon cards | The launcher currently selects an RX 9070 XT. RX 6000, RX 7000 and other RX 9000 models still need adapter-specific tests. |
| CPU and NVIDIA CUDA | The original GUI and CLI remain available in the source. The AMD launcher is a separate entry point. |
| Linux AMD | No verified ROCm extraction path in this preview. |

Long-video timing, difficult backgrounds and accuracy across different fonts still need wider testing. Setup downloads pinned packages and models into local folders. The executable launches the included helpers and reuses those files on later runs.

## Project and credits

The AMD preview is maintained in **agaaylin2-ui/VideOCR**. It builds on Tim Lodemann's VideOCR fork and the earlier work credited in the MIT license. PaddleOCR and PaddleX supply the recognition models and image processing. ONNX Runtime supplies the DirectML execution provider.

[Upstream VideOCR and original GUI/CLI guide](https://github.com/timminator/VideOCR) · [License](LICENSE) · [AMD porting notes](AMD_PORTING_PLAN.md)

The launcher source is in [windows/AmdLauncher.cs](windows/AmdLauncher.cs). To rebuild it on Windows x64, run `powershell -NoProfile -File .\windows\build-launcher.ps1` from the repository folder.
