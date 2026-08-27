@echo off
REM ============================================================
REM  UnaniMed AI — Stop All Services
REM ============================================================

echo ============================================================
echo  UnaniMed AI Services Stop
echo ============================================================
echo.

echo [1/11]  Stopping Ollama Keep-Alive Manager...
taskkill /FI "WINDOWTITLE eq Ollama Keep-Alive Manager*" /T /F > nul 2>&1
echo [OK]

echo [2/11]  Stopping Analytics Service...
taskkill /FI "WINDOWTITLE eq Analytics Service*" /T /F > nul 2>&1
echo [OK]

echo [3/11]  Stopping Feedback Service...
taskkill /FI "WINDOWTITLE eq Feedback Service*" /T /F > nul 2>&1
echo [OK]

echo [4/11]  Stopping Bangla Normalizer...
taskkill /FI "WINDOWTITLE eq Bangla Normalizer*" /T /F > nul 2>&1
echo [OK]

echo [5/11]  Stopping Semantic Cache Service...
taskkill /FI "WINDOWTITLE eq Semantic Cache Service*" /T /F > nul 2>&1
echo [OK]

echo [6/11]  Stopping Safety Check Service...
taskkill /FI "WINDOWTITLE eq Safety Check Service*" /T /F > nul 2>&1
echo [OK]

echo [7/11]  Stopping Patient Profile Service...
taskkill /FI "WINDOWTITLE eq Patient Profile Service*" /T /F > nul 2>&1
echo [OK]

echo [8/11]  Stopping TTS Service...
taskkill /FI "WINDOWTITLE eq TTS Service*" /T /F > nul 2>&1
echo [OK]

echo [9/11]  Stopping STT Service...
taskkill /FI "WINDOWTITLE eq STT Service*" /T /F > nul 2>&1
echo [OK]

echo [10/11] Stopping Ollama Service...
taskkill /FI "WINDOWTITLE eq Ollama Service*" /T /F > nul 2>&1
echo [OK]

echo [11/11] Stopping ChromaDB (Docker)...
docker stop chromadb > nul 2>&1
echo [OK]

echo.
echo ============================================================
echo  All Services Stopped.
echo ============================================================
echo.
pause
