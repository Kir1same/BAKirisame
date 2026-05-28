param(
    [Parameter(Mandatory = $true)]
    [string]$Url
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvPath = Join-Path $Root ".env"
$BaseUrl = $Url.TrimEnd("/")

if (-not $BaseUrl.EndsWith("/cards")) {
    $BaseUrl = "$BaseUrl/cards"
}

$lines = @()
if (Test-Path $EnvPath) {
    $lines = Get-Content -Encoding UTF8 $EnvPath
}

$foundBase = $false
$foundDir = $false
$updated = foreach ($line in $lines) {
    if ($line -match "^IMAGE_PUBLIC_BASE_URL=") {
        $foundBase = $true
        "IMAGE_PUBLIC_BASE_URL=$BaseUrl"
    } elseif ($line -match "^IMAGE_PUBLIC_DIR=") {
        $foundDir = $true
        "IMAGE_PUBLIC_DIR=artifacts/public/cards"
    } else {
        $line
    }
}

if (-not $foundBase) {
    $updated += "IMAGE_PUBLIC_BASE_URL=$BaseUrl"
}
if (-not $foundDir) {
    $updated += "IMAGE_PUBLIC_DIR=artifacts/public/cards"
}

[System.IO.File]::WriteAllLines($EnvPath, $updated, [System.Text.UTF8Encoding]::new($false))
Write-Host "Updated IMAGE_PUBLIC_BASE_URL=$BaseUrl"
