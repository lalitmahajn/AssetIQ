# AssetIQ Demo Simulation Trigger

Write-Host "Searching for Plant Backend container..." -ForegroundColor Cyan

# Try to find the container name
$containerName = docker ps --filter "name=plant_backend" --format "{{.Names}}" | Select-Object -First 1

if (-not $containerName) {
    Write-Error "Could not find a running container for 'plant_backend'. Please ensure the Plant Docker stack is running."
    exit 1
}

Write-Host "Found container: $containerName" -ForegroundColor Green
Write-Host "Running simulation script inside container..." -ForegroundColor Cyan

docker exec -it $containerName python tools/simulate_demo.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSimulation completed successfully!" -ForegroundColor Green
    Write-Host "Check your Plant UI to see the new data." -ForegroundColor White
}
else {
    Write-Error "Simulation failed. Please check the error messages above."
}
