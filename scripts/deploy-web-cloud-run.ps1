param(
    [string]$ProjectId = "boardsight-agent",
    [string]$Region = "us-central1",
    [string]$ServiceName = "boardsight-web",
    [string]$AiServiceUrl = "",
    [string]$Memory = "1Gi",
    [int]$Cpu = 1,
    [int]$TimeoutSeconds = 300,
    [int]$MaxInstances = 2,
    [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "java-app"
$gcloudCmd = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue).Source

if (-not $gcloudCmd) {
    $candidate = "C:\Users\$env:USERNAME\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $candidate) {
        $gcloudCmd = $candidate
    }
}

if (-not (Test-Path $sourceRoot)) {
    throw "Unable to find java-app source directory at $sourceRoot"
}
if (-not $gcloudCmd) {
    throw "Unable to locate gcloud.cmd. Install Google Cloud CLI or add it to PATH."
}
if (-not $AiServiceUrl) {
    throw "AiServiceUrl is required. Pass the deployed BoardSight AI Cloud Run URL."
}

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }

Write-Host "Deploying BoardSight web service to Cloud Run..."
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host "Source:  $sourceRoot"
Write-Host "AI URL:  $AiServiceUrl"

& $gcloudCmd config set project $ProjectId | Out-Null
& $gcloudCmd config set run/region $Region | Out-Null

$envVars = @(
    "JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8",
    "BOARDSIGHT_AI_URL=$AiServiceUrl"
)

& $gcloudCmd run deploy $ServiceName `
    --source $sourceRoot `
    --region $Region `
    --project $ProjectId `
    --port 8080 `
    --memory $Memory `
    --cpu $Cpu `
    --timeout $TimeoutSeconds `
    --max-instances $MaxInstances `
    --set-env-vars ($envVars -join ",") `
    $authFlag
