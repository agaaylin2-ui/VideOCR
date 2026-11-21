# VideoOCR-AMD

Extract burned-in subtitles from video and save them as a timed SubRip (`.srt`) file. On the Preview 5 source branch, you can export English, Simplified Chinese or Traditional Chinese from a bilingual video. The Windows desktop app uses PaddleOCR with DirectML on the **AMD Radeon RX 9070 XT**. It includes Python, the OCR models, a video preview, adjustable subtitle regions and a processing queue.

## Download for Windows 11 (x64)

Open [Releases](https://github.com/aylinlabs/VideoOCR-AMD/releases) and choose the Windows executable under **Assets**. GitHub also provides ZIP and tar.gz archives of the source code.

- **Desktop Preview 1** is a portable download. Run the executable, choose an extraction folder and open **VideOCR-AMD.exe** inside it. Keep the extracted folders together.
- **Windows Setup builds** install the app for your Windows account. Run the file ending in **-Setup.exe**, then open **VideoOCR-AMD** from Start. You can remove it through **Settings → Apps → Installed apps**.

## Extract subtitles

1. Choose **Open File** and select a video.
2. Select **PaddleOCR - AMD DirectML (RX 9070 XT)**. In Preview 5, choose **English**, **Chinese** (Simplified) or **Chinese Traditional** under **Subtitle Language**. Seek to a frame with a subtitle and drag a box around the lines you want. The default region is the bottom third of the picture.
3. Choose a new SRT filename and click **Run**. Open the resulting file as a subtitle track in your video player.

To save both languages, run the same clip twice with a different subtitle language and output filename. Published builds through Preview 4 offer only the English setting. [Language selection and validation](PREVIEW_5_MULTILINGUAL.md)

Frame extraction runs on the CPU. On longer jobs, the current desktop source uses up to three DirectML workers for text detection and recognition. The processing log reports the worker count. [Desktop settings and build instructions](AMD_DESKTOP.md)

## Hardware and testing

The AMD desktop path has been tested on Windows 11 with a 16 GB RX 9070 XT. It currently selects that adapter model. Other Radeon cards and Linux ROCm require separate validation. The original CPU and NVIDIA CUDA workflows are described in the [upstream VideOCR guide](https://github.com/timminator/VideOCR).

On one 21:30 episode, the Preview 3 worker update reduced total export time from 3:30 to 2:44. The two runs produced byte-identical subtitles across all 368 cues. This comparison measured performance and consistency on that episode. OCR accuracy also depends on the subtitle region, font and background.

## Source, console tools and credits

The desktop installer bundles its dependencies. Developers using the separate console launcher can follow the [console setup](AMD_VIDEO_WINDOWS.md), [model setup](AMD_TEST_WINDOWS.md) and [image comparison guide](REAL_IMAGE_TEST_WINDOWS.md).

This fork builds on Tim Lodemann’s VideOCR and the earlier contributors credited in the [MIT license](LICENSE). PaddleOCR and PaddleX supply the models and inference pipeline. ONNX Runtime supplies DirectML execution. [AMD porting notes](AMD_PORTING_PLAN.md)
