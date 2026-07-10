param(
    [ValidateSet("Summary", "Participants")]
    [string]$View = "Summary"
)

$ErrorActionPreference = "Stop"
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    $fallback = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (-not (Test-Path $fallback)) {
        throw "Google Cloud CLI was not found."
    }
    $gcloudPath = $fallback
} else {
    $gcloudPath = $gcloud.Source
}

$apiPath = if ($View -eq "Participants") { "participants" } else { "stats" }
$remoteScript = @"
set -e
set -a
source /etc/cosyvoice-usage.env
set +a
curl -fsS -H "Authorization: Bearer `$ADMIN_TOKEN" \
  http://127.0.0.1:8092/v1/$apiPath
"@
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteScript))

& $gcloudPath compute ssh instance-20260605-064354 `
    --project project-65fdc892-c06d-4b52-a92 `
    --zone asia-northeast3-a `
    --command "echo $encoded | base64 -d | sudo bash"
