# Package Chrome Extension for distribution
# Usage: .\scripts\package-extension.ps1 [-Version "1.0.0-beta.1"]

param(
    [string]$Version = "1.0.0-beta.1"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$extensionDir = Join-Path $projectRoot "chrome-extension"
$distDir = Join-Path $projectRoot "dist"
$zipName = "digg-daily-extension-$Version.zip"
$zipPath = Join-Path $distDir $zipName

Write-Host "Packaging Digg Daily Extension v$Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Create dist directory
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
    Write-Host "Created dist/ directory"
}

# Remove old ZIP if exists
if (Test-Path $zipPath) {
    Remove-Item $zipPath
    Write-Host "Removed existing $zipName"
}

# Verify icons exist
$requiredIcons = @("icon16.png", "icon48.png", "icon128.png")
foreach ($icon in $requiredIcons) {
    $iconPath = Join-Path $extensionDir "icons\$icon"
    if (-not (Test-Path $iconPath)) {
        Write-Host "ERROR: Missing icon: $iconPath" -ForegroundColor Red
        Write-Host "Please create the required icons first. See chrome-extension/icons/README.md" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "All required icons found" -ForegroundColor Green

# Update version in manifest.json
$manifestPath = Join-Path $extensionDir "manifest.json"
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$manifest.version = $Version
$manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8
Write-Host "Updated manifest.json version to $Version" -ForegroundColor Green

# Create ZIP file
$filesToInclude = @(
    "manifest.json",
    "popup.html",
    "popup.css",
    "popup.js",
    "background.js",
    "content.js",
    "content.css",
    "icons"
)

# Change to extension directory and create ZIP
Push-Location $extensionDir
try {
    Compress-Archive -Path $filesToInclude -DestinationPath $zipPath -Force
    Write-Host "Created: $zipPath" -ForegroundColor Green
} finally {
    Pop-Location
}

# Show file info
$zipFile = Get-Item $zipPath
Write-Host ""
Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "  File: $zipName"
Write-Host "  Size: $([math]::Round($zipFile.Length / 1KB, 2)) KB"
Write-Host "  Path: $zipPath"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test the extension by loading it unpacked in Chrome"
Write-Host "  2. Submit to Chrome Web Store: https://chrome.google.com/webstore/devconsole"
Write-Host "  3. Or create a GitHub release with this ZIP attached"
