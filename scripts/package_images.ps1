# ProSourcing Docker Packaging Script (Frontend Priority)

$IMAGES = @(
    "prosourcing-frontend:v20260327",
    "prosourcing-backend:v20260327",
    "postgres:15-alpine"
)

$OUTPUT_DIR = "deployment_package/20260327/images"
if (-not (Test-Path $OUTPUT_DIR)) { New-Item -ItemType Directory -Path $OUTPUT_DIR -Force }

Write-Host ">>> Packing images (FRONTEND FIRST)..." -ForegroundColor Cyan

foreach ($image in $IMAGES) {
    $safe_name = $image -replace ":", "_"
    $output_file = Join-Path $OUTPUT_DIR "$($safe_name).tar"
    Write-Host "Exporting: $image"
    docker save $image -o $output_file
}
Write-Host ">>> Done!" -ForegroundColor Cyan
