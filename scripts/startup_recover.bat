@echo off
setlocal
title ProSourcing Startup Recover

cd /d %~dp0..

echo =========================================
echo ProSourcing Startup Recover
echo =========================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=py
    ) else (
        echo [FAIL] Python not found in PATH
        pause
        exit /b 1
    )
)

%PY_CMD% scripts\startup_recover.py %*
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE%==0 (
    echo [OK] Script finished
) else (
    echo [FAIL] Script failed, exit code: %EXIT_CODE%
)

echo.
pause
exit /b %EXIT_CODE%
