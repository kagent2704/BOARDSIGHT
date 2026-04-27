param(
    [string]$python = "python",
    [int]$port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$servicePath = Join-Path $projectRoot "python-ai\boardsight_ai\service.py"

& $python $servicePath --host "127.0.0.1" --port $port
