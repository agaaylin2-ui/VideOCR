param(
    [string]$ImagePath = '',
    [string]$ConverterPython = '',
    [string]$OrtPython = ''
)
# Local diagnostic only. Never installs drivers or system-wide packages.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$experiment = Join-Path $root 'amd_experiment'
. (Join-Path $experiment 'adapter_selection.ps1')
$runRoot = Join-Path $root ('amd-work\run-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
$logs = Join-Path $runRoot 'diagnostics'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$results = [ordered]@{}
$summary = Join-Path $logs 'summary.txt'
function Status([string]$Stage, [string]$State, [string]$Message) {
    $results[$Stage] = "$State - $Message"
    Write-Host ("[{0}] {1}: {2}" -f $State, $Stage, $Message)
}
function Run-Logged([string]$Label, [string]$Program, [string[]]$Arguments) {
    $log = Join-Path $logs ($Label + '.log')
    Write-Host "Running $Label. This can take several minutes..."
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Program @Arguments 2>&1 | Out-File -FilePath $log -Encoding utf8
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($code -ne 0) { throw "$Label failed (exit $code). See $Label.log in the report." }
}
function Find-VenvPython([string]$Candidate, [string]$Label) {
    if (-not $Candidate) { Status $Label 'UNVERIFIED' 'No prepared isolated environment supplied.'; return $null }
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { Status $Label 'FAIL' 'Python executable not found.'; return $null }
    $exe = (Resolve-Path -LiteralPath $Candidate).Path
    $cfg = Join-Path (Split-Path (Split-Path $exe -Parent) -Parent) 'pyvenv.cfg'
    if (-not (Test-Path -LiteralPath $cfg -PathType Leaf)) { Status $Label 'FAIL' 'This Python is not in a virtual environment.'; return $null }
    return $exe
}
try {
    "Windows: $([Environment]::OSVersion.VersionString)`nPowerShell: $($PSVersionTable.PSVersion)`nTime: $(Get-Date -Format o)" | Set-Content -Encoding utf8 (Join-Path $logs 'environment.txt')
    if ($env:OS -ne 'Windows_NT') { throw 'This helper requires Windows.' }
    $pythonExe = $null
    $pythonPrefix = @()
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try { Run-Logged 'python-version' $py.Source @('-3.12','--version'); $pythonExe = $py.Source; $pythonPrefix = @('-3.12') } catch { }
    }
    if (-not $pythonExe) {
        $python = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($python) {
            try { Run-Logged 'python-version' $python.Source @('-c', 'import sys; print(sys.version); sys.exit(0 if sys.version_info[:2] == (3,12) else 1)'); $pythonExe = $python.Source } catch { }
        }
    }
    if (-not $pythonExe) { Status 'Python 3.12' 'FAIL' 'Install Python 3.12 from python.org, then rerun.'; throw 'Python 3.12 missing.' }
    Status 'Python 3.12' 'PASS' 'Python 3.12 found.'
    $seven = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if (-not $seven) {
        $candidate = Join-Path ${env:ProgramFiles} '7-Zip\7z.exe'
        if (Test-Path -LiteralPath $candidate) { $sevenPath = $candidate } else { $sevenPath = $null }
    } else { $sevenPath = $seven.Source }
    if (-not $sevenPath) { Status '7-Zip' 'FAIL' 'Install 7-Zip from 7-zip.org, then rerun.'; throw '7-Zip missing.' }
    Status '7-Zip' 'PASS' 'Found 7-Zip.'
    try {
        $gpuFile = Join-Path $logs 'dxgi-adapters.json'
        & $pythonExe @pythonPrefix (Join-Path $experiment 'dxgi_adapters.py') | Set-Content -Encoding utf8 $gpuFile
        if ($LASTEXITCODE -ne 0) { throw 'DXGI enumeration failed' }
        $adapterJson = Get-Content -Raw -Encoding utf8 $gpuFile
        $adapters = ConvertFrom-Json -InputObject $adapterJson
        Write-Host 'DirectML adapter list:'
        foreach ($a in $adapters) { Write-Host ("  {0}: {1} (vendor {2}, device {3})" -f $a.index, $a.name, $a.vendor_id, $a.device_id) }
        $adapter = Get-SelectedAmdAdapter -Json $adapterJson
        Status 'AMD adapter' 'PASS' "RX 9070 XT identified at DXGI index $adapter."
    } catch { $adapter = $null; Status 'AMD adapter' 'UNVERIFIED' "Could not enumerate DXGI adapters: $_" }
    try { Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,PNPDeviceID | Format-List | Out-File -Encoding utf8 (Join-Path $logs 'windows-gpus.txt') } catch { "GPU driver information unavailable: $_" | Set-Content -Encoding utf8 (Join-Path $logs 'windows-gpus.txt') }
    if (-not $ImagePath) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker = New-Object System.Windows.Forms.OpenFileDialog
        $picker.Title = 'Choose a subtitle screenshot'; $picker.Filter = 'Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg'
        if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $ImagePath = $picker.FileName }
        $picker.Dispose()
    }
    if (-not $ImagePath -or -not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) { Status 'Screenshot' 'FAIL' 'No image selected. Run again and choose a subtitle screenshot.'; throw 'Screenshot missing.' }
    $ImagePath = (Resolve-Path -LiteralPath $ImagePath).Path
    Status 'Screenshot' 'PASS' 'Image selected. It will not be copied into the report.'
    $converter = Find-VenvPython $ConverterPython 'Converter dependencies'
    $ort = Find-VenvPython $OrtPython 'DirectML dependencies'
    $download = Read-Host 'Download the verified PaddleOCR archives (about 450 MB) and isolated test dependencies? Type YES to continue'
    if ($download -cne 'YES') { Status 'Archives' 'UNVERIFIED' 'Download skipped.'; throw 'Download skipped by user.' }
    $assets = @(
        @{ name='PaddleOCR-CPU-v3.7.0.7z'; hash='a1b597f5620d1a86cec606b50908a12fc1b215adf6807be5538b7ca6bddc9d20'; dest='runtime' },
        @{ name='PaddleOCR.PP-OCRv6.support.files.VideOCR.7z'; hash='7f98a187a1d8d9b5291f3be7cd6a6b693b32ddffd75d39c05d333d8f0b3ee145'; dest='models' }
    )
    foreach ($asset in $assets) {
        $archive = Join-Path $runRoot $asset.name
        Write-Host "Downloading $($asset.name)..."
        Invoke-WebRequest -Uri ("https://github.com/timminator/PaddleOCR-Standalone/releases/download/v3.7.0/" + $asset.name) -OutFile $archive -UseBasicParsing
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
        if ($actual -ne $asset.hash) { Status 'Archives' 'FAIL' 'SHA-256 mismatch; download was not executed or extracted.'; throw "Hash mismatch: $($asset.name)" }
        $dir = Join-Path $runRoot $asset.dest
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Run-Logged ('extract-' + $asset.dest) $sevenPath @('x', $archive, "-o$dir", '-y')
    }
    Status 'Archives' 'PASS' 'Both published SHA-256 hashes matched before extraction.'
    $exe = @(Get-ChildItem (Join-Path $runRoot 'runtime') -Recurse -File -Filter paddleocr.exe)
    $models = @(Get-ChildItem (Join-Path $runRoot 'models') -Recurse -Directory -Filter 'PaddleOCR.PP-OCRv6.support.files')
    if ($exe.Count -ne 1 -or $models.Count -ne 1) { throw 'Unexpected archive layout. Please send the diagnostic report.' }
    $modelRoot = $models[0].FullName
    try { Run-Logged 'cpu-baseline' $pythonExe ($pythonPrefix + @((Join-Path $experiment 'baseline.py'), '--exe', $exe[0].FullName, '--models', $modelRoot, '--image', $ImagePath, '--out', (Join-Path $logs 'cpu-baseline'))); Status 'CPU baseline' 'PASS' 'CPU commands completed. OCR accuracy still needs review.' }
    catch { Status 'CPU baseline' 'FAIL' "$_" }
    if (-not $ort -and -not $OrtPython) {
        try {
            $ortDir = Join-Path $runRoot 'ort-env'
            Run-Logged 'ort-create-environment' $pythonExe ($pythonPrefix + @('-m','venv',$ortDir))
            $ortCandidate = Join-Path $ortDir 'Scripts\python.exe'
            Run-Logged 'ort-install-verified' $ortCandidate @('-m','pip','install','--index-url','https://pypi.org/simple','--only-binary=:all:','--require-hashes','-r',(Join-Path $experiment 'locks\directml-win-py312.txt'))
            $ort = $ortCandidate
            Status 'DirectML dependencies' 'PASS' 'Installed hash-checked packages in an isolated environment.'
        } catch { $ort = $null; Status 'DirectML dependencies' 'FAIL' "$_" }
    }
    if ($ort) {
        try {
            Run-Logged 'ort-versions' $ort @('-m','pip','freeze')
            Run-Logged 'ort-dependencies' $ort @('-c', 'import numpy,onnxruntime; print(onnxruntime.get_available_providers()); assert "DmlExecutionProvider" in onnxruntime.get_available_providers()')
            Status 'DirectML dependencies' 'PASS' 'DirectML provider is available; model execution remains unverified.'
        } catch { Status 'DirectML dependencies' 'FAIL' "$_"; $ort = $null }
    }
    $exportOk = $false
    if ($converter) {
        try {
            Run-Logged 'converter-dependencies' $converter @('-c', 'import paddle,paddlex,onnx')
            Status 'Converter dependencies' 'PASS' 'Required Python imports succeeded; package provenance must be verified separately.'
            $env:Path = (Split-Path $converter -Parent) + ';' + $env:Path
            $paddlex = Join-Path (Split-Path $converter -Parent) 'paddlex.exe'
            if (-not (Test-Path -LiteralPath $paddlex)) { throw 'paddlex.exe is missing from the converter environment.' }
            Run-Logged 'converter-versions' $converter @('-m','pip','freeze')
            Run-Logged 'export' $converter @((Join-Path $experiment 'export_models.py'), '--models', $modelRoot, '--out', (Join-Path $runRoot 'onnx'), '--opset', '17')
            Copy-Item (Join-Path $runRoot 'onnx\export_manifest.json') $logs
            $exportOk = $true; Status 'ONNX export' 'PASS' 'Both model files were exported. Correctness is unverified.'
        } catch { Status 'ONNX export' 'FAIL' "$_" }
    } else { Status 'ONNX export' 'UNVERIFIED' 'Converter environment is not prepared; see README.' }
    if ($ort -and $exportOk -and $null -ne $adapter) {
        try {
            foreach ($kind in @('det','rec')) {
              try {
                $model = @(Get-ChildItem (Join-Path $runRoot "onnx\$kind") -Recurse -File -Filter '*.onnx')
                if ($model.Count -ne 1) { throw "Expected one $kind ONNX model." }
                $shape = if ($kind -eq 'det') { '1,3,640,640' } else { '1,3,48,320' }
                $inputFile = Join-Path $runRoot "$kind-input.npz"
                Run-Logged "$kind-input" $ort @((Join-Path $experiment 'make_smoke_input.py'), '--model', $model[0].FullName, '--shape', $shape, '--out', $inputFile)
                Run-Logged "$kind-comparison" $ort @((Join-Path $experiment 'compare_ort.py'), '--model', $model[0].FullName, '--input', $inputFile, '--out', (Join-Path $logs "$kind-test"), '--adapter', "$adapter")
                Status "$kind tensor test" 'PASS' 'ORT comparison and provider trace completed; physical GPU use is still unverified.'
              } catch { Status "$kind tensor test" 'FAIL' "$_" }
            }
        } catch { Status 'DirectML experiment' 'FAIL' "$_" }
    } else {
        $reasons = @()
        if (-not $ort) { $reasons += 'DirectML environment missing' }
        if (-not $exportOk) { $reasons += 'model export did not succeed' }
        if ($null -eq $adapter) { $reasons += 'RX 9070 XT adapter not uniquely identified' }
        Status 'DirectML experiment' 'UNVERIFIED' ('Skipped: ' + ($reasons -join '; ') + '.')
    }
    Status 'AMD acceleration' 'UNVERIFIED' 'Inspect both traces and observe the RX 9070 XT during real inference; this smoke test does not verify OCR accuracy.'
} catch {
    if (-not $results.Contains('Overall')) { Status 'Overall' 'FAIL' "$_" }
} finally {
    if (-not $results.Contains('AMD acceleration')) { Status 'AMD acceleration' 'UNVERIFIED' 'GPU inference has not been established.' }
    $results.GetEnumerator() | ForEach-Object { "$($_.Key): $($_.Value)" } | Set-Content -Encoding utf8 $summary
    $zip = Join-Path $root ('amd-diagnostic-' + (Split-Path $runRoot -Leaf) + '.zip')
    try { Compress-Archive -Path (Join-Path $logs '*') -DestinationPath $zip -Force; Write-Host "`nDiagnostic report: $zip" }
    catch { Write-Host "Could not create ZIP. Diagnostic files are in: $logs" }
    Write-Host 'Review the report before sharing: it may include account paths, hardware details and recognized subtitle text.'
}

if (@($results.Values | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { exit 1 }
