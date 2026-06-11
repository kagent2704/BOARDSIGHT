param(
    [string]$ProjectId = "boardsight-agent",
    [string]$Region = "us-central1",
    [string]$ServiceName = "boardsight-agent-runtime",
    [string]$BackendUrl = "",
    [string]$BackendApiKey = "",
    [string]$GitLabBaseUrl = "",
    [string]$GitLabProjectId = "",
    [string]$GitLabPrivateToken = "",
    [string]$AgentModel = "gemini-2.5-flash",
    [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "python-agent"
$gcloudCmd = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue).Source

if (-not $gcloudCmd) {
    $candidate = "C:\Users\$env:USERNAME\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $candidate) {
        $gcloudCmd = $candidate
    }
}

if (-not (Test-Path $sourceRoot)) {
    throw "Unable to find python-agent source directory at $sourceRoot"
}
if (-not $gcloudCmd) {
    throw "Unable to locate gcloud.cmd. Install Google Cloud CLI or add it to PATH."
}
if (-not $BackendUrl) {
    throw "BackendUrl is required. Pass the deployed BoardSight backend Cloud Run URL."
}
if (-not $BackendApiKey) {
    throw "BackendApiKey is required. Pass the BoardSight agent API key."
}

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }

Write-Host "Deploying BoardSight ADK agent to Cloud Run..."
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host "Source:  $sourceRoot"
Write-Host "Backend: $BackendUrl"

& $gcloudCmd config set project $ProjectId | Out-Null
& $gcloudCmd config set run/region $Region | Out-Null

$envVars = @(
    "GOOGLE_GENAI_USE_VERTEXAI=true",
    "GOOGLE_CLOUD_PROJECT=$ProjectId",
    "GOOGLE_CLOUD_LOCATION=$Region",
    "BOARDSIGHT_AGENT_MODEL=$AgentModel",
    "BOARDSIGHT_AGENT_BACKEND_URL=$BackendUrl",
    "BOARDSIGHT_AGENT_BACKEND_API_KEY=$BackendApiKey",
    "BOARDSIGHT_AGENT_SERVE_WEB=true"
)

if ($GitLabBaseUrl) {
    $envVars += "BOARDSIGHT_GITLAB_BASE_URL=$GitLabBaseUrl"
}
if ($GitLabProjectId) {
    $envVars += "BOARDSIGHT_GITLAB_PROJECT_ID=$GitLabProjectId"
}
if ($GitLabPrivateToken) {
    $envVars += "BOARDSIGHT_GITLAB_PRIVATE_TOKEN=$GitLabPrivateToken"
}

& $gcloudCmd run deploy $ServiceName `
    --source $sourceRoot `
    --region $Region `
    --project $ProjectId `
    --quiet `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --timeout 300 `
    --max-instances 2 `
    --set-env-vars ($envVars -join ",") `
    $authFlag
