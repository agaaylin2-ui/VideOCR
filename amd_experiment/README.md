# Phase 0 baseline and Phase 1 Windows experiment

This is an isolated research harness, not a VideOCR backend. No DirectML support or OCR accuracy is established. Source pins and release SHA-256 are in `manifest.json`; the Standalone source commit and 3.7.0 release binary are independent pins and are not claimed to be identical. The application `build.py` still downloads latest releases: do not use it as a reproducible baseline. Pin the VideOCR checkout to commit `548f8753d169539e56a0fb4ba532a53d8b7a8c82`; the branch adds only this folder. Reproducibility is conditional on recording the environment, exact downloaded archives and input data; this is not a fully locked transitive Python environment.

The first models are the exact default English paths selected by `CLI/videocr/utils.py`: `det/PP-OCRv6_small_det` and `rec/PP-OCRv6_small_rec`. Keep every file in each directory, including model configuration and character dictionary. Use orientation disabled. The medium/server models, orientation classifier and other language families are outside this spike. Model contents and hashes are recorded by the scripts, but their individual expected hashes are not yet independently verified. Do not replace weights with similarly named official downloads.

## 1. Get and verify release archives (PowerShell)

Use Windows x64, Python 3.12 and 7-Zip. Open PowerShell in the VideOCR checkout root. This downloads about 450 MB. Install 7-Zip separately if needed. GitHub asset digest is checked before extraction; `7z` must be on PATH, or replace it with the full path to 7z.exe.

```powershell
New-Item -ItemType Directory -Force amd-work, amd-work/downloads, amd-work/runtime, amd-work/assets | Out-Null
$base = 'https://github.com/timminator/PaddleOCR-Standalone/releases/download/v3.7.0'
$cpu = 'PaddleOCR-CPU-v3.7.0.7z'
$models = 'PaddleOCR.PP-OCRv6.support.files.VideOCR.7z'
Invoke-WebRequest "$base/$cpu" -OutFile "amd-work/downloads/$cpu"
Invoke-WebRequest "$base/$models" -OutFile "amd-work/downloads/$models"
if ((Get-FileHash "amd-work/downloads/$cpu" -Algorithm SHA256).Hash -ne 'a1b597f5620d1a86cec606b50908a12fc1b215adf6807be5538b7ca6bddc9d20') { throw 'CPU archive hash mismatch' }
if ((Get-FileHash "amd-work/downloads/$models" -Algorithm SHA256).Hash -ne '7f98a187a1d8d9b5291f3be7cd6a6b693b32ddffd75d39c05d333d8f0b3ee145') { throw 'Model archive hash mismatch' }
7z x "amd-work/downloads/$cpu" -oamd-work/runtime
if ($LASTEXITCODE -ne 0) { throw 'CPU extraction failed' }
7z x "amd-work/downloads/$models" -oamd-work/assets
if ($LASTEXITCODE -ne 0) { throw 'Model extraction failed' }
$exe = (Get-ChildItem amd-work/runtime -Recurse -Filter paddleocr.exe | Select-Object -First 1).FullName
$root = (Get-ChildItem amd-work/assets -Recurse -Directory -Filter PaddleOCR.PP-OCRv6.support.files | Select-Object -First 1).FullName
if (-not $exe -or -not $root) { throw 'Executable or model support directory not found; inspect archive layout' }
Write-Host "CPU executable: $exe`nModel support directory: $root"
```

Use a representative, non-private subtitle screenshot in PNG/JPEG. Set `$image` below to its full path. Paths, input hashes and recognized text will be included in output files: review/redact sensitive material before sharing.

```powershell
$image = 'C:\path\to\subtitle.png'
py -3.12 amd_experiment/baseline.py --exe "$exe" --models "$root" --image "$image" --out amd-work/baseline
if ($LASTEXITCODE -ne 0) { throw 'CPU baseline failed; inspect baseline logs' }
```

This runs the pinned standalone's CPU-only detection and full OCR pipelines with the selected models and saves stdout, stderr, input/executable/model file SHA-256, commands, wall time and platform in `amd-work/baseline`. The first pass sets `--device cpu` explicitly: unlike VideOCR's existing detection call, it does not rely on default-device selection. This image-level baseline does not establish end-to-end video/SRT equivalence; a separate pinned VideOCR CPU distribution, test clip and manually checked SRT are needed for that gate.

## 2. Export the two models

Use a separate converter environment. PaddleOCR's conversion guide currently specifies a Windows nightly PaddlePaddle build; this command is therefore not a fully immutable converter environment. Save `pip freeze` and the exact wheel URLs/versions used and reuse them on reruns. The converter may automatically raise the requested opset. Do not silently downgrade or infer compatibility from export success. References: [official conversion instructions](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/others/obtaining_onnx_models.html), [DirectML limits](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html).

```powershell
py -3.12 -m venv amd-work/converter
.\amd-work\converter\Scripts\python -m pip install --pre paddlepaddle -i https://www.paddlepaddle.org.cn/packages/nightly/cpu/
.\amd-work\converter\Scripts\python -m pip install 'paddlex[ocr-core]==3.7.0' onnx==1.19.1
.\amd-work\converter\Scripts\paddlex --install paddle2onnx
.\amd-work\converter\Scripts\python -m pip freeze | Set-Content amd-work/converter-versions.txt
$env:Path = (Resolve-Path amd-work/converter/Scripts).Path + ';' + $env:Path
.\amd-work\converter\Scripts\python amd_experiment/export_models.py --models "$root" --out amd-work/onnx --opset 17
if ($LASTEXITCODE -ne 0) { throw 'Conversion failed; save console output and converter-versions.txt' }
```

Each output folder must initially be empty; the export script refuses to overwrite it. Locate the actual files instead of assuming their names:

```powershell
$det = (Get-ChildItem amd-work/onnx/det -Recurse -Filter *.onnx | Select-Object -First 1).FullName
$rec = (Get-ChildItem amd-work/onnx/rec -Recurse -Filter *.onnx | Select-Object -First 1).FullName
.\amd-work\converter\Scripts\python -c "import onnx,sys; [(lambda m: print(p, [(x.domain,x.version) for x in m.opset_import]))(onnx.load(p)) for p in sys.argv[1:]]" "$det" "$rec"
```

Check actual opset/operator support and retain `export_manifest.json`, converted file hashes and logs. If conversion fails, stop and share the error; neither conversion nor Paddle-vs-ONNX accuracy has been validated here.

## 3. CPU versus DirectML smoke tests

Install ORT DirectML in its own venv; do not install CPU `onnxruntime` and `onnxruntime-directml` into the same environment. The latter also supplies CPUExecutionProvider. The example concrete shapes are plausible probes, not verified PP-OCRv6 input preprocessing; if a model rejects a shape, inspect its declared inputs and share the error. Synthetic tensors do not represent subtitle images and cannot evaluate OCR accuracy.

```powershell
py -3.12 -m venv amd-work/ort
.\amd-work\ort\Scripts\python -m pip install numpy==1.26.4 onnxruntime-directml==1.24.4
.\amd-work\ort\Scripts\python -m pip freeze | Set-Content amd-work/ort-versions.txt
.\amd-work\ort\Scripts\python amd_experiment/make_smoke_input.py --model "$det" --shape 1,3,640,640 --out amd-work/det-input.npz
if ($LASTEXITCODE -ne 0) { throw 'Detector input failed' }
.\amd-work\ort\Scripts\python amd_experiment/make_smoke_input.py --model "$rec" --shape 1,3,48,320 --out amd-work/rec-input.npz
if ($LASTEXITCODE -ne 0) { throw 'Recognizer input failed' }
.\amd-work\ort\Scripts\python amd_experiment/compare_ort.py --model "$det" --input amd-work/det-input.npz --out amd-work/det-test --adapter 0
.\amd-work\ort\Scripts\python amd_experiment/compare_ort.py --model "$rec" --input amd-work/rec-input.npz --out amd-work/rec-test --adapter 0
```

`--adapter` is the DXGI enumeration index; 0 may be an integrated or other GPU. Identify the RX 9070 XT adapter using Windows Task Manager/DirectX diagnostics and test other indices if necessary; Task Manager numbering is a clue, not proof of DXGI identity. Record the selected adapter and use GPU activity telemetry during each run. For longer observation repeat the command; this script executes each model once per provider. `comparison.json` lists available and selected providers, CPU and DirectML node-event counts/durations and per-output tolerances; raw ORT JSON traces show the assigned nodes. DirectML profile entries alone do not identify the physical card. Ensure meaningful compute (e.g. convolutions, not merely shape operations) is assigned to DML, GPU activity is visible on the RX 9070 XT, and output comparisons pass. CPU partitions are explicitly reported. A missing DML provider, missing DML nodes, model error or numerical mismatch fails the run. Inspect *both* command results; the second command's exit code does not represent the first. A successful smoke test is not a claim of end-to-end OCR or correct decoding.

For CPU-only troubleshooting add `--cpu-only`. A meaningful next stage must capture genuine preprocessed model tensors, compare Paddle and ONNX tensors, then compare boxes, text, confidence and full subtitle output on a ground-truth corpus. Do not upload private images or subtitle text without reviewing them.

## Send back

Send Windows version, AMD driver version, RX 9070 XT identification, adapter index and GPU activity observations; `amd-work/baseline/` after checking content, `converter-versions.txt`, `ort-versions.txt`, `onnx/export_manifest.json`, detector and recognizer `comparison.json` and profile JSON traces, actual opset output and complete error messages if any. Converted weights and source images are not needed unless requested. Note that full paths in reports may reveal account names; redact as needed.
