$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\amd_experiment\adapter_selection.ps1')
function Assert-Fails([string]$json) {
    $failed = $false
    try { Get-SelectedAmdAdapter -Json $json | Out-Null } catch { $failed = $true }
    if (-not $failed) { throw "Expected selection failure: $json" }
}
$case = '[{"index":0,"name":"Other GPU","vendor_id":"8086"},{"index":2,"name":"AMD Radeon RX 9070 XT","vendor_id":"1002"}]'
if ((Get-SelectedAmdAdapter -Json $case) -ne 2) { throw 'Wrong nonzero index' }
Assert-Fails '[]'
Assert-Fails 'not-json'
Assert-Fails '[{"index":0,"name":"AMD Radeon RX 9070 XT","vendor_id":"1002"},{"index":1,"name":"AMD Radeon RX 9070 XT","vendor_id":"1002"}]'
Assert-Fails '[{"index":"oops","name":"AMD Radeon RX 9070 XT","vendor_id":"1002"}]'
Write-Host 'Adapter selection tests passed.'
