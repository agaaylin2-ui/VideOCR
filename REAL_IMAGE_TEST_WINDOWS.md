# Real subtitle image comparison

This is an experiment, not a VideOCR GPU backend. It compares the existing PaddleOCR CPU executable with ONNX Runtime CPU and DirectML using PaddleX 3.7.0's OCR image preprocessing, box detection, cropping, recognition and decoding. The original detector/recognizer model files and converted ONNX models come from your earlier successful `run-20261113-175739-a8cda65b` test. The helper verifies they still match the earlier run's recorded hashes and reuses its DirectML Python environment without changing it. It installs separately pinned PaddleX packages in a new local folder using SHA-256 hash checking; package hashes establish file integrity, not publisher safety.

## Select screenshots and optional transcripts

Put at least four subtitle screenshots in one folder: clear text, small text, multiple lines, and a difficult background. These should be real examples you are allowed to use. You can include more. The helper cannot determine the categories automatically; sample coverage stays UNVERIFIED until you confirm them.

To measure accuracy against a human reference, create a plain text file next to each image, with exactly the same name except for `.txt`. For example, `clear.png` needs `clear.txt`. Open Notepad, type exactly the subtitle text visible in the image, and save the file as UTF-8. If you do not supply a transcript, the report still compares ONNX text against Paddle CPU but marks real character accuracy UNVERIFIED. The report normalizes Unicode and whitespace before calculating character error rate (CER); the displayed character accuracy is `max(0, 1 - CER)`. It is not a substitute for manual review.

## Run on Windows 11

1. Download the current development branch: [Download ZIP](https://github.com/agaaylin2-ui/VideOCR/archive/refs/heads/feature/amd-gpu-support.zip). Extract it to a new folder and open that folder.
2. Click the folder address bar, type `powershell`, and press Enter. Copy, paste and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\run-real-ocr-test.ps1
   ```

3. A folder picker opens. Select your previous successful **run folder**, for example `Downloads\VideOCR-feature-amd-gpu-support\VideOCR-feature-amd-gpu-support\amd-work\run-20261113-175739-a8cda65b`. Select the `run-...` folder itself, then click OK. If you deleted it, rerun `run-amd-test.ps1` first.
4. In the image picker, open your screenshots folder. Hold **Ctrl** and click each screenshot, then click **Open**. The optional `.txt` files are read automatically; do not select them.
5. The helper identifies the RX 9070 XT by DXGI index. Press **Ctrl+Shift+Esc**, choose **Performance**, then select your AMD GPU. If needed, change a graph to **Compute**. Keep Task Manager visible. Type `YES` in PowerShell to download the additional hash-verified PaddleX packages into an isolated folder. The existing model exports, DirectML environment, CPU executable and driver are not reinstalled or modified.
6. Watch for activity when the helper says it is running comparisons. DirectML OCR runs eight times per image to make activity easier to see; CPU runs once. Windows graph labels and display refresh can miss short activity, so absence of a spike is not proof of failure. Note what you saw.
7. When complete, find `real-image-report-...zip` in the new folder. It includes `report.txt`, detailed JSON, logs and profiles, but not screenshots or model weights. Review it before sharing: OCR text, file paths and hardware information are included. Send it back with what you saw in Task Manager.

## Reading the report

Per-image CPU and DirectML parity checks use provisional gates: CER versus Paddle CPU <=1%, no unmatched recognized boxes, and axis-aligned bounding-box IoU >=0.9. Boxes are paired greedily at IoU >=0.5. They are simple screening criteria, not production accuracy guarantees. The report includes recognized text, confidence and confidence differences, box coordinates, unmatched boxes, and a separate detection-only comparison; detection-only defaults can differ from the full OCR pipeline.

ORT profiling lists DirectML and CPU node events separately for detector and recognizer and identifies CPU operations. The DirectML test requires DirectML events in both sessions. PaddleX's 3.7 GPU convenience check assumes CUDA, so this experimental worker sets its device configuration to `cpu` but explicitly selects `DmlExecutionProvider` with the selected DXGI adapter in ORT; session provider lists and profiles record what actually happened. Provider events do not independently identify the physical GPU. Eight repeats are reflected in profile counts. Ground-truth accuracy, image coverage, actual physical GPU activity and final VideOCR subtitle quality remain UNVERIFIED until reviewed.

The prior successful test's isolated DirectML environment must have NumPy 1.26.4 and ONNX Runtime DirectML 1.24.4. Additional PaddleX 3.7.0 dependencies are in `amd_experiment/locks/real-ocr-extra-win-py312.txt`; their wheel hashes were checked against PyPI. The source model and executable hashes are checked against the earlier run's reports. If a stage fails, send the generated ZIP and the error; it may contain partial results. Do not install drivers or edit system-wide Python to troubleshoot.
