# AssetIQ Full Data Cleanup Trigger

Write-Host "Searching for containers..." -ForegroundColor Cyan

$plantContainer = docker ps --filter "name=plant_backend" --format '{{.Names}}' | Select-Object -First 1
$hqContainer = docker ps --filter "name=hq_backend" --format '{{.Names}}' | Select-Object -First 1

if (-not $plantContainer) {
    Write-Warning "Plant container not found. Skipping Plant cleanup."
}
if (-not $hqContainer) {
    Write-Warning "HQ container not found. Skipping HQ cleanup."
}

if (-not $plantContainer -and -not $hqContainer) {
    Write-Error "No containers found. Please ensure AssetIQ is running."
    exit 1
}

Write-Host "WARNING: This will permanently delete ALL data from BOTH Plant and HQ databases." -ForegroundColor Red
$confirm = Read-Host "Are you sure? (y/n)"

if ($confirm.ToLower() -ne 'y') {
    Write-Host "Cleanup cancelled."
    exit 0
}

# Clean Plant
if ($plantContainer) {
    Write-Host "`nCleaning Plant ($plantContainer)..." -ForegroundColor Yellow
    docker exec -i $plantContainer python tools/clean_demo.py --no-prompt
}

# Clean HQ
if ($hqContainer) {
    Write-Host "`nCleaning HQ ($hqContainer)..." -ForegroundColor Yellow
    docker exec -i $hqContainer python tools/clean_hq.py
}

Write-Host "`nCleanup process finished." -ForegroundColor Green
