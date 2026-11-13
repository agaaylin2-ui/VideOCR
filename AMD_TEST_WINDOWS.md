# Windows AMD diagnostic

The helper runs a CPU OCR baseline, exports the PP-OCRv6 small detection and recognition models, and compares ONNX Runtime CPU and DirectML outputs on **synthetic tensors**. It does not install drivers or modify system-wide Python. OCR text accuracy on DirectML and end-to-end VideOCR GPU support are not established.

## Run the test

1. If needed, install Python 3.12 x64 from [python.org](https://www.python.org/downloads/) and 7-Zip from [7-zip.org](https://www.7-zip.org/). The helper can also find compatible 7-Zip command line tools.
2. Open [the development branch](https://github.com/agaaylin2-ui/VideOCR/tree/feature/amd-gpu-support), click **Code**, then **Download ZIP**. Extract the ZIP and open its folder, containing `run-amd-test.ps1`.
3. Click the folder address bar, type `powershell`, and press Enter. Paste and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\run-amd-test.ps1
   ```

   The execution-policy change applies only to this process; follow your organization's rules if the command is blocked.
4. Choose a subtitle screenshot. When prompted, type `YES` and press Enter to allow the downloads. The initial run downloads approximately 450 MB of archives plus Python packages. Model archives are checked against pinned SHA-256 values before extraction; Python packages are installed in separate virtual environments with pinned SHA-256 hashes. Hashes check file integrity, not publisher security.
5. Wait for the `amd-diagnostic-...zip` location. Review it before sharing: paths, GPU details and recognized subtitle text may be included. The screenshot, archives, and converted models are not included.

The helper identifies the RX 9070 XT from DXGI and reports the actual adapter index. A provider being available does not prove inference. The two tensor tests run real converted model graphs on CPU and DirectML and record provider node profiles, tolerances and CPU partitions. They use artificial input, and do not check OCR text, decoded boxes, or subtitle timing. Independent observation of GPU activity and tests on real preprocessed images remain necessary. `AMD acceleration: UNVERIFIED` is intentional.

## Converter findings

On this Windows 11 host, PaddlePaddle 3.3.1 with Paddle2ONNX 2.1.0 failed to load `paddle2onnx_cpp2py_export`: Windows reported that a procedure could not be found. This points to a native binary compatibility problem, but its exact missing symbol has not been identified. Paddle2ONNX 2.1.0 also requires ONNX <=1.17.0, so the previous ONNX 1.19.1 instructions were incompatible. See the [upstream Windows issue](https://github.com/PaddlePaddle/Paddle2ONNX/issues/1615).

A separately installed, hash-checked Python 3.12 x64 environment with PaddlePaddle 3.1.1, Paddle2ONNX 2.1.0, and ONNX 1.17.0 successfully exported the two exact PP-OCRv6 small model directories from the CPU baseline. The helper uses that locked environment and passes `--optimize_tool None` to avoid the optional Polygraphy constant-folding step and its extra dependencies. It checks each output with ONNX's checker and records source/output hashes and actual opsets. CPU-vs-DirectML tensor tests passed on this host with synthetic inputs; that does not establish native Paddle-vs-ONNX equivalence or OCR accuracy.

The package locks in `amd_experiment/locks` target Windows x64 and Python 3.12. Their hashes were checked against PyPI release metadata. The converter and ORT run in separate virtual environments to avoid dependency conflicts. They are created inside the new `amd-work/run-*` folder; no GPU driver or global package is changed. If a download, import, export or inference fails, the report records the failing stage and logs. Do not run the outdated nightly or unpinned installation instructions.

Maintainers can supply separate existing environments with `-ConverterPython` and `-OrtPython`; the helper does not verify the provenance of packages already installed there. Test on representative subtitle images, compare Paddle and ONNX outputs, verify profile assignment and independently observe the selected physical GPU before claiming compatibility. The existing application CPU/NVIDIA paths are unaffected.
