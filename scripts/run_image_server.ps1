$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$PublicDir = Join-Path $Root "artifacts\public"

New-Item -ItemType Directory -Force (Join-Path $PublicDir "cards") | Out-Null
Set-Location $Root
& $Python -m http.server 8080 --directory $PublicDir
