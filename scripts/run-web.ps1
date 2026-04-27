param(
    [int]$port = 8080
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$jarPath = Join-Path $projectRoot "java-app\build\boardsight.jar"

if (-not (Test-Path $jarPath)) {
    & (Join-Path $PSScriptRoot "build-java.ps1")
}

java -jar $jarPath --port $port
