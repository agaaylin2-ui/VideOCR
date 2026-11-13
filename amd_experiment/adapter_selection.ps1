function Get-SelectedAmdAdapter {
    param([Parameter(Mandatory = $true)][string]$Json)
    $parsed = ConvertFrom-Json -InputObject $Json -ErrorAction Stop
    if ($null -eq $parsed) { throw 'DXGI adapter list is empty.' }
    $selected = @(
        foreach ($item in $parsed) {
            if ($item.vendor_id -eq '1002' -and $item.name -match 'Radeon RX 9070 XT') { $item }
        }
    )
    if ($selected.Count -ne 1) { throw "Expected exactly one RX 9070 XT; found $($selected.Count)." }
    $index = 0
    if (-not [int]::TryParse([string]$selected[0].index, [ref]$index) -or $index -lt 0) { throw 'DXGI adapter index is invalid.' }
    return $index
}
