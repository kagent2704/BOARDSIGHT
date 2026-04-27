param(
    [Parameter(Mandatory = $true)]
    [string]$video,

    [string]$python = "python",

    [string]$output = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$jarPath = Join-Path $projectRoot "java-app\build\boardsight.jar"

if (-not (Test-Path $jarPath)) {
    & (Join-Path $PSScriptRoot "build-java.ps1")
}

$argsList = @("-jar", $jarPath, "--video", $video, "--python", $python)
if ($output) {
    $argsList += @("--output", $output)
}

java @argsList
