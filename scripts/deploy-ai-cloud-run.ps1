param(
    [string]$ProjectId = "boardsight-agent",
    [string]$Region = "us-central1",
    [string]$ServiceName = "boardsight-ai",
    [string]$AgentApiKey = "",
    [string]$AgentApiSecretName = "",
    [string]$DatabaseUrl = "",
    [string]$DatabaseUrlSecretName = "",
    [string]$GitLabBaseUrl = "",
    [string]$GitLabProjectId = "",
    [string]$GitLabPrivateToken = "",
    [string]$DataEncryptionSecretName = "",
    [string]$LlmProvider = "extractive",
    [string]$GeminiApiKey = "",
    [string]$GeminiApiSecretName = "",
    [string]$GeminiModel = "gemini-3.1-flash-lite",
    [string]$BootstrapAdminPassword = "",
    [string]$BootstrapAdminPasswordSecretName = "",
    [string]$ResendApiKey = "",
    [string]$ResendApiSecretName = "",
    [string]$Memory = "4Gi",
    [int]$Cpu = 2,
    [int]$TimeoutSeconds = 900,
    [int]$MaxInstances = 2,
    [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "python-ai"
$gcloudCmd = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue).Source

if (-not $gcloudCmd) {
    $candidate = "C:\Users\$env:USERNAME\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $candidate) {
        $gcloudCmd = $candidate
    }
}

if (-not (Test-Path $sourceRoot)) {
    throw "Unable to find python-ai source directory at $sourceRoot"
}
if (-not $gcloudCmd) {
    throw "Unable to locate gcloud.cmd. Install Google Cloud CLI or add it to PATH."
}

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }

Write-Host "Deploying BoardSight AI service to Cloud Run..."
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host "Source:  $sourceRoot"
if ($AgentApiKey) {
    Write-Host "Agent API key: configured"
}
if ($DatabaseUrl) {
    Write-Host "Database URL: configured"
}
if ($GitLabBaseUrl -or $GitLabProjectId -or $GitLabPrivateToken) {
    Write-Host "GitLab integration: configured"
}
if ($GeminiApiKey) {
    Write-Host "Gemini API: configured"
}
if ($GeminiApiSecretName) {
    Write-Host "Gemini API secret: configured"
}

& $gcloudCmd config set project $ProjectId | Out-Null
& $gcloudCmd config set run/region $Region | Out-Null

$envVars = @(
    "PYTHONIOENCODING=UTF-8",
    "MPLBACKEND=Agg",
    "HF_HUB_DISABLE_SYMLINKS_WARNING=1",
    "BOARDSIGHT_WARM_MODELS=0",
    "BOARDSIGHT_LLM_PROVIDER=$LlmProvider"
)
if ($GeminiApiSecretName) {
    $envVars += "BOARDSIGHT_GEMINI_MODEL=$GeminiModel"
} elseif ($GeminiApiKey) {
    $envVars += "GEMINI_API_KEY=$GeminiApiKey"
    $envVars += "BOARDSIGHT_GEMINI_MODEL=$GeminiModel"
}
if ($AgentApiSecretName) {
    $null = $null
} elseif ($AgentApiKey) {
    $envVars += "BOARDSIGHT_AGENT_API_KEY=$AgentApiKey"
}
if ($DatabaseUrlSecretName) {
    $null = $null
} elseif ($DatabaseUrl) {
    $envVars += "BOARDSIGHT_DATABASE_URL=$DatabaseUrl"
}
if ($GitLabBaseUrl) {
    $envVars += "BOARDSIGHT_GITLAB_BASE_URL=$GitLabBaseUrl"
}
if ($GitLabProjectId) {
    $envVars += "BOARDSIGHT_GITLAB_PROJECT_ID=$GitLabProjectId"
}
if ($GitLabPrivateToken) {
    $envVars += "BOARDSIGHT_GITLAB_PRIVATE_TOKEN=$GitLabPrivateToken"
}
if ($BootstrapAdminPasswordSecretName) {
    $null = $null
} elseif ($BootstrapAdminPassword) {
    $envVars += "BOARDSIGHT_BOOTSTRAP_ADMIN_PASSWORD=$BootstrapAdminPassword"
}
if ($ResendApiSecretName) {
    $null = $null
} elseif ($ResendApiKey) {
    $envVars += "BOARDSIGHT_RESEND_API_KEY=$ResendApiKey"
}

$secretVars = @()
if ($DataEncryptionSecretName) {
    $secretVars += "BOARDSIGHT_DATA_ENCRYPTION_KEY=$DataEncryptionSecretName`:latest"
}
if ($GeminiApiSecretName) {
    $secretVars += "GEMINI_API_KEY=$GeminiApiSecretName`:latest"
}
if ($AgentApiSecretName) {
    $secretVars += "BOARDSIGHT_AGENT_API_KEY=$AgentApiSecretName`:latest"
}
if ($DatabaseUrlSecretName) {
    $secretVars += "BOARDSIGHT_DATABASE_URL=$DatabaseUrlSecretName`:latest"
}
if ($BootstrapAdminPasswordSecretName) {
    $secretVars += "BOARDSIGHT_BOOTSTRAP_ADMIN_PASSWORD=$BootstrapAdminPasswordSecretName`:latest"
}
if ($ResendApiSecretName) {
    $secretVars += "BOARDSIGHT_RESEND_API_KEY=$ResendApiSecretName`:latest"
}

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--source", $sourceRoot,
    "--region", $Region,
    "--project", $ProjectId,
    "--port", "8000",
    "--memory", $Memory,
    "--cpu", $Cpu,
    "--timeout", $TimeoutSeconds,
    "--max-instances", $MaxInstances,
    "--set-env-vars", ($envVars -join ","),
    $authFlag
)
if ($secretVars.Count -gt 0) {
    $deployArgs += @("--set-secrets", ($secretVars -join ","))
}

& $gcloudCmd @deployArgs
