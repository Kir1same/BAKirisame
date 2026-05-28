$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$PublicDir = Join-Path $Root "artifacts\public"

New-Item -ItemType Directory -Force (Join-Path $PublicDir "cards") | Out-Null

Write-Host "Starting local image server on http://localhost:8080 ..."
Start-Process powershell.exe -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Set-Location '$Root'; & '$Python' -m http.server 8080 --directory '$PublicDir'"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Starting Cloudflare quick tunnel."
Write-Host "Copy the https://*.trycloudflare.com URL, then set:"
Write-Host "IMAGE_PUBLIC_BASE_URL=https://your-tunnel.trycloudflare.com/cards"
Write-Host ""
cloudflared tunnel --url http://localhost:8080
