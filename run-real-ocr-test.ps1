param([string]$PreviousRun = '', [string[]]$Images = @())
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$experiment = Join-Path $root 'amd_experiment'
. (Join-Path $experiment 'adapter_selection.ps1')
$work = Join-Path $root ('amd-work\real-image-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
$logs = Join-Path $work 'diagnostics'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$result = 'UNVERIFIED'
try {
    Add-Type -AssemblyName System.Windows.Forms
    if (-not $PreviousRun) {
        $folder = New-Object System.Windows.Forms.FolderBrowserDialog
        $folder.Description = 'Select the successful run folder inside your previous amd-work folder (run-20261113-175739-a8cda65b)'
        if ($folder.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $PreviousRun = $folder.SelectedPath }
        $folder.Dispose()
    }
    if (-not $PreviousRun -or -not (Test-Path -LiteralPath $PreviousRun -PathType Container)) { throw 'Previous successful run was not selected.' }
    $ort = Join-Path $PreviousRun 'ort-env\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $ort -PathType Leaf)) { throw 'This folder does not contain the prior DirectML environment. Select the run-... folder, not its parent.' }
    if (-not $Images.Count) {
        $picker = New-Object System.Windows.Forms.OpenFileDialog
        $picker.Title = 'Select subtitle screenshots (hold Ctrl to choose multiple)'
        $picker.Filter = 'Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg'
        $picker.Multiselect = $true
        if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $Images = @($picker.FileNames) }
        $picker.Dispose()
    }
    if (-not $Images.Count) { throw 'No screenshots selected.' }
    foreach ($image in $Images) { if (-not (Test-Path -LiteralPath $image -PathType Leaf)) { throw 'A selected screenshot was not found.' } }
    Write-Host 'Checking the RX 9070 XT adapter...'
    $json = & $ort (Join-Path $experiment 'dxgi_adapters.py')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate DirectX adapters.' }
    $adapter = Get-SelectedAmdAdapter -Json ($json -join "`n")
    $json | Set-Content -Encoding utf8 (Join-Path $logs 'dxgi-adapters.json')
    Write-Host "RX 9070 XT: DirectX adapter $adapter"
    Write-Host 'Open Task Manager with Ctrl+Shift+Esc, select Performance, then GPU. Watch the RX 9070 XT during the test.'
    Write-Host 'This test adds hash-verified PaddleX packages in a separate temporary folder and reuses your previous Python and models.'
    if ((Read-Host 'Download the additional verified packages? Type YES to continue') -cne 'YES') { throw 'Dependency download skipped.' }
    $deps = Join-Path $work 'paddlex-deps'
    $installLog = Join-Path $logs 'install.log'
    $before = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $ort -m pip install --index-url https://pypi.org/simple --only-binary=:all: --no-deps --require-hashes --target $deps -r (Join-Path $experiment 'locks\real-ocr-extra-win-py312.txt') 2>&1 | Out-File -Encoding utf8 $installLog; $installCode = $LASTEXITCODE }
    finally { $ErrorActionPreference = $before }
    if ($installCode -ne 0) { throw 'PaddleX package setup failed; see install.log in the report.' }
    $env:PYTHONPATH = $deps
    $env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
    $compare = Join-Path $experiment 'real_image_compare.py'
    $compareArgs = @($compare, '--run', $PreviousRun, '--out', (Join-Path $logs 'comparison'), '--adapter', "$adapter", '--images') + $Images
    Write-Host 'Running CPU and DirectML OCR comparisons. Please watch Task Manager now...'
    $before = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $ort @compareArgs 2>&1 | Out-File -Encoding utf8 (Join-Path $logs 'run.log'); $code = $LASTEXITCODE }
    finally { $ErrorActionPreference = $before }
    if ($code -ne 0) { throw 'One or more comparisons failed; inspect comparison/report.txt and run.log.' }
    $result = 'UNVERIFIED: review parity, ground truth, provider profiles and physical GPU activity.'
    Write-Host "[UNVERIFIED] $result"
} catch {
    $result = "FAIL: $_"
    Write-Host "[FAIL] $result"
} finally {
    $result | Set-Content -Encoding utf8 (Join-Path $logs 'summary.txt')
    $zip = Join-Path $root ('real-image-report-' + (Split-Path $work -Leaf) + '.zip')
    try {
        # Exclude model copies and installed packages; profiles, OCR text and paths remain.
        $entries = @(Get-ChildItem -LiteralPath $logs -File)
        $comparison = Join-Path $logs 'comparison'
        if (Test-Path $comparison) {
            $entries += @(Get-ChildItem -LiteralPath $comparison -File)
            $entries += @(Get-ChildItem -LiteralPath $comparison -Directory | Where-Object Name -ne 'model-configs')
        }
        if ($entries.Count) { Compress-Archive -Path $entries.FullName -DestinationPath $zip -Force }
        Write-Host "Report: $zip"
    } catch { Write-Host "Could not zip the report. Files are in: $logs" }
    Write-Host 'Review the report before sharing: it may contain subtitle text, file paths, and hardware information.'
}
if ($result -like 'FAIL*') { exit 1 }
