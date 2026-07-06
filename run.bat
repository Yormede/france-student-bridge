@echo off
setlocal

if "%FS_EMAIL%"=="" (
    echo [WARNING] FS_EMAIL n'est pas defini. Set-le via set FS_EMAIL=ton@email.com
)
if "%FS_PASSWORD%"=="" (
    echo [WARNING] FS_PASSWORD n'est pas defini. Set-le via set FS_PASSWORD=ton_mdp
)

if "%BIND_HOST%"=="" set BIND_HOST=0.0.0.0
if "%BIND_PORT%"=="" set BIND_PORT=8765

echo ========================================
echo   Bridge Service - France Student API
echo ========================================
echo.
echo Endpoints:
echo   Health:  http://%BIND_HOST%:%BIND_PORT%/health
echo   Models:  http://%BIND_HOST%:%BIND_PORT%/models
echo   Chat:    http://%BIND_HOST%:%BIND_PORT%/chat/completions
echo   Images:  http://%BIND_HOST%:%BIND_PORT%/images/^<filename^>
echo.

python bridge_server.py
