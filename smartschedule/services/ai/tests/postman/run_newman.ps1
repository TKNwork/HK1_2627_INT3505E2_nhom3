param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$InternalApiKey = "local_dev_internal_api_key_1234567890"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Collection = Join-Path $ScriptDir "ai_service.postman_collection.json"
$ReportDir = Join-Path $ScriptDir "reports"

New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

newman run $Collection `
    --env-var "base_url=$BaseUrl" `
    --env-var "internal_api_key=$InternalApiKey" `
    -r "cli,junit" `
    --reporter-junit-export (Join-Path $ReportDir "newman-junit.xml")
