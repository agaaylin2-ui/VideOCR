# Build the Windows x64 console launcher using the Windows .NET Framework compiler.
param([string]$OutputDirectory = (Join-Path $PSScriptRoot '..'))
$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$output = Join-Path (Resolve-Path -LiteralPath $OutputDirectory).Path 'VideOCR-AMD.exe'
& $compiler /nologo /optimize+ /platform:x64 /target:exe /reference:System.Windows.Forms.dll "/out:$output" (Join-Path $PSScriptRoot 'AmdLauncher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Could not compile the AMD launcher.' }
Write-Host "Built $output"
