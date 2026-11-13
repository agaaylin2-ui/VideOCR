# Windows AMD test helper

This helper can run the CPU baseline and can run the export and DirectML experiments **when separately prepared isolated environments are supplied**. It does not install Python packages, GPU drivers, or alter system-wide Python. There is currently no complete independently verified, hash-locked dependency set for the Windows PaddleX nightly converter and its dependencies. Therefore a beginner cannot yet complete the converter/DirectML stages with this helper alone. Do not use the older unpinned installation commands in `amd_experiment/README.md` if your policy is to execute only verified downloads. Those commands are experimental and are not run by this helper.

## Run the CPU diagnostic

1. Install [Python 3.12 for Windows](https://www.python.org/downloads/) and [7-Zip](https://www.7-zip.org/), from their official websites if they are not already installed. Python and 7-Zip are prerequisites; the helper does not install them. Choose a Python 3.12 release and use the Windows x64 installer. No administrator or PATH changes are required if the Python launcher is installed.
2. On [the development branch](https://github.com/agaaylin2-ui/VideOCR/tree/feature/amd-gpu-support), click the green **Code** button, choose **Download ZIP**, and extract the ZIP. Open the extracted folder containing `run-amd-test.ps1`.
3. Click the folder's address bar, type `powershell`, and press Enter. In the blue or black window, enter:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\run-amd-test.ps1
   ```

   This execution-policy setting applies only to this PowerShell process. If your organization's policy blocks it, do not bypass that policy; ask your administrator.
4. Select a clear screenshot containing subtitles. Type `YES` and press Enter to permit the approximately 450 MB download. The helper compares each archive with the project's published SHA-256 digest before extraction or execution. The screenshot is not copied to the report, but the recognized text and local paths may appear in logs.
5. At the end, find the `amd-diagnostic-...zip` file in the same folder. Review its contents for personal information and send it back. Keep the window open until the report location appears. The script prints PASS, FAIL or UNVERIFIED for each stage; the GPU is always UNVERIFIED until actual execution and accuracy are independently checked.

The helper queries DXGI directly and reports its adapter index, name and PCI vendor/device identifiers. It proceeds with DirectML only when exactly one DXGI adapter identifies itself as an AMD Radeon RX 9070 XT. A match or an ORT node trace does not by itself prove that physical GPU executed useful work. Task Manager activity and model-level accuracy comparisons are still required.

## Prepared environments (for maintainers)

Optional `-ConverterPython` and `-OrtPython` parameters accept the `Scripts\python.exe` paths of **separate existing virtual environments**. The converter must already contain PaddlePaddle, PaddleX with the conversion plugin, ONNX and `paddlex.exe`; the ORT environment must contain NumPy and `onnxruntime-directml`. The script checks for `pyvenv.cfg`, does not create or install these environments, and does not validate the provenance of pre-existing packages. Supply environments only after verifying all packages against a trusted complete hash lock. Record their `pip freeze` output in the report. Once supplied, the helper attempts model export, then detector and recognizer comparisons with the discovered DXGI index. Input tensors are synthetic; no OCR parity is established. Failure at any stage is recorded without claiming GPU compatibility. The source model folders and converted models remain in `amd-work`, outside the diagnostic ZIP.

A future change must supply a reviewed, reproducible dependency lock and safe installation process before the full test is beginner-ready. Export has not yet been verified for these models. If the report says UNVERIFIED for converter or DirectML dependencies, this is expected and does not mean the graphics card failed.
