@echo off
REM ============================================================
REM  UnaniMed AI — Free Public HTTPS Tunnel & Webhook Generator
REM  Creates an instant, 100% free HTTPS public URL for Webhook
REM ============================================================

cd /d "%~dp0.."

echo ============================================================
echo  UnaniMed AI — Free Public HTTPS Tunnel
echo ============================================================
echo.
echo Select service to expose to public internet:
echo   [1] n8n Webhook (Port 5678) -- For Facebook Messenger Auto-Reply
echo   [2] UnaniMed AI Web Portal (Port 8010)
echo.
set /p choice="Enter choice (1 or 2, default is 1): "

if "%choice%"=="2" (
    python scripts\create_public_tunnel.py 8010
) else (
    python scripts\create_public_tunnel.py 5678
)
pause
