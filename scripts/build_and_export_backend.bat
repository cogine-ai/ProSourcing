@echo off
echo [1/2] Building Backend Docker Image...
docker build -f Dockerfile.backend -t prosourcing-backend:20260516 .
if %errorlevel% neq 0 (
    echo Error: Docker build failed!
    exit /b %errorlevel%
)
echo [2/2] Exporting Backend Image to tar...
if not exist "deployment_package\20260516" mkdir "deployment_package\20260516"
docker save prosourcing-backend:20260516 -o deployment_package/20260516/prosourcing-backend_20260516.tar
echo Success! Image saved to deployment_package/20260516/
