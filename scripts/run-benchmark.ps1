param(
    [Parameter(Mandatory = $true)]
    [string]$video,

    [string]$python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $projectRoot "output\benchmark-run"

& $python (Join-Path $projectRoot "python-ai\boardsight_ai\cli.py") --video $video --output-dir $outputDir
Write-Host "Benchmark artifacts written to $outputDir"
