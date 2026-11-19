[CmdletBinding()]
param([string]$Video, [string]$OutputFile, [string]$ImageRun, [string]$RuntimeRun)
$ErrorActionPreference = 'Stop'
$experiment = Join-Path $PSScriptRoot 'amd_experiment'
. (Join-Path $experiment 'adapter_selection.ps1')
Add-Type -AssemblyName System.Windows.Forms

function Select-RunFolder($title) {
    $dialog = New-Object Windows.Forms.FolderBrowserDialog
    try {
        $dialog.Description = $title
        if ($dialog.ShowDialog() -ne 'OK') { throw 'Folder selection cancelled.' }
        return $dialog.SelectedPath
    } finally { $dialog.Dispose() }
}

function Find-PreviousRun($pattern, $required) {
    $downloads = Join-Path $env:USERPROFILE 'Downloads'
    $folders = @((Join-Path $PSScriptRoot 'amd-work'))
    if (Test-Path -LiteralPath $downloads) {
        foreach ($repo in (Get-ChildItem -LiteralPath $downloads -Directory -Filter 'VideOCR*')) {
            $folders += Join-Path $repo.FullName 'amd-work'
            foreach ($inner in (Get-ChildItem -LiteralPath $repo.FullName -Directory -Filter 'VideOCR*')) {
                $folders += Join-Path $inner.FullName 'amd-work'
            }
        }
    }
    $matches = foreach ($folder in ($folders | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $folder) {
            foreach ($run in (Get-ChildItem -LiteralPath $folder -Directory -Filter $pattern)) {
                if (Test-Path -LiteralPath (Join-Path $run.FullName $required)) { $run }
            }
        }
    }
    $latest = $matches | Sort-Object Name -Descending | Select-Object -First 1
    if ($latest) { return $latest.FullName }
}

try {
    if (-not $Video) {
        $picker = New-Object Windows.Forms.OpenFileDialog
        try {
            $picker.Title = 'Choose a video with English subtitles visible near the bottom'
            $picker.Filter = 'Video files|*.mp4;*.mkv;*.avi;*.mov;*.webm;*.m4v;*.ts;*.wmv|All files|*.*'
            if ($picker.ShowDialog() -ne 'OK') { return }
            $Video = $picker.FileName
        } finally { $picker.Dispose() }
    }
    $Video = (Get-Item -LiteralPath $Video).FullName
    if (-not $OutputFile) {
        $save = New-Object Windows.Forms.SaveFileDialog
        try {
            $save.Title = 'Choose a NEW subtitle filename'
            $save.Filter = 'SubRip subtitles (*.srt)|*.srt'
            $save.InitialDirectory = Split-Path $Video -Parent
            $save.FileName = [IO.Path]::GetFileNameWithoutExtension($Video) + '.amd.srt'
            if ($save.ShowDialog() -ne 'OK') { return }
            $OutputFile = $save.FileName
        } finally { $save.Dispose() }
    }
    if (Test-Path -LiteralPath $OutputFile) { throw 'That file already exists. Run again and enter a new subtitle filename.' }
    if (-not $ImageRun) { $ImageRun = Find-PreviousRun 'real-image-*' 'diagnostics\comparison\model-configs\rec\inference.onnx' }
    if (-not $ImageRun) { $ImageRun = Select-RunFolder 'Select your successful real-image-... folder inside amd-work' }
    if (-not $RuntimeRun) { $RuntimeRun = Find-PreviousRun 'run-*' 'ort-env\Scripts\python.exe' }
    if (-not $RuntimeRun) { $RuntimeRun = Select-RunFolder 'Select the earlier run-... folder containing ort-env inside amd-work' }
    $ort = Join-Path $RuntimeRun 'ort-env\Scripts\python.exe'
    $deps = Join-Path $ImageRun 'paddlex-deps'
    if (-not (Test-Path -LiteralPath $ort) -or -not (Test-Path -LiteralPath (Join-Path $deps 'paddlex'))) {
        throw 'Your earlier test files are incomplete. Keep both original test folders including ort-env and paddlex-deps.'
    }
    Write-Host "Using the DirectML environment in $RuntimeRun"
    Write-Host "Using OCR models and packages from $ImageRun"
    $adapters = & $ort (Join-Path $experiment 'dxgi_adapters.py')
    if ($LASTEXITCODE -ne 0) { throw 'Windows could not list the DirectX adapters.' }
    $adapter = Get-SelectedAmdAdapter -Json ($adapters -join [Environment]::NewLine)
    Write-Host "Using Radeon RX 9070 XT (DirectX adapter $adapter)."
    $work = Join-Path $PSScriptRoot 'amd-work'
    [IO.Directory]::CreateDirectory($work) | Out-Null
    $id = [guid]::NewGuid().ToString('N')
    $logs = Join-Path $work ("video-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $id.Substring(0,8))
    [IO.Directory]::CreateDirectory($logs) | Out-Null
    $lock = Join-Path $experiment 'locks\video-win-py312.txt'
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $digest = [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($lock))).Replace('-', '') }
    finally { $sha.Dispose() }
    $cache = Join-Path $work ('video-deps-' + $digest.Substring(0,16))
    if (-not (Test-Path -LiteralPath $cache)) {
        Write-Host 'First use: downloading five hash-checked video packages into this folder.'
        $stage = Join-Path $work ("setup-" + $id)
        & $ort -m pip --disable-pip-version-check install --index-url https://pypi.org/simple --only-binary=:all: --no-deps --require-hashes --target $stage -r $lock
        if ($LASTEXITCODE -ne 0) { throw 'Video package setup failed. Check your internet connection and try again.' }
        try { [IO.Directory]::Move($stage, $cache) }
        catch { if (-not (Test-Path -LiteralPath $cache)) { throw } }
    }
    $oldPath = $env:PYTHONPATH
    $oldEncoding = $env:PYTHONIOENCODING
    try {
        $env:PYTHONPATH = "$cache;$deps"
        $env:PYTHONIOENCODING = 'utf-8'
        Write-Host 'Reading your video. Keep this window open until it displays the subtitle path.'
        & $ort (Join-Path $experiment 'video_export.py') --video $Video --output $OutputFile --image-run $ImageRun --adapter $adapter --diagnostics $logs
        if ($LASTEXITCODE -ne 0) { throw "Extraction stopped. See the message above. Execution details: $logs" }
    } finally {
        $env:PYTHONPATH = $oldPath
        $env:PYTHONIOENCODING = $oldEncoding
    }
    if (-not $PSBoundParameters.ContainsKey('Video')) {
        [Windows.Forms.MessageBox]::Show("Open this subtitle file in your video player:`n`n$OutputFile", 'VideOCR export complete') | Out-Null
    }
} catch {
    Write-Host ("Could not export subtitles: " + $_.Exception.Message)
    exit 1
}
