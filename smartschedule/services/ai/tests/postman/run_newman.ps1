param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$InternalApiKey = $env:INTERNAL_API_KEY,
    [string]$ReportDirectory = (Join-Path $PSScriptRoot "reports")
)

if (-not $InternalApiKey) {
    $InternalApiKey = "local_dev_internal_api_key_1234567890"
    Write-Warning "Using the local test default key. Set INTERNAL_API_KEY to match the AI service."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Collection = Join-Path $ScriptDir "ai_service.postman_collection.json"

New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

newman.cmd run $Collection `
    --env-var "base_url=$BaseUrl" `
    --env-var "internal_api_key=$InternalApiKey" `
    -r "cli,junit" `
    --reporter-junit-export (Join-Path $ReportDirectory "newman-junit.xml")
exit $LASTEXITCODE
