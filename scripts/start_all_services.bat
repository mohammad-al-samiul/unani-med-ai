@echo off
REM ============================================================
REM  UnaniMed AI — Start All Services
REM  Services: ChromaDB, Ollama, STT, TTS, Patient Profile,
REM            Safety Check, Semantic Cache, Bangla Normalizer,
REM            Feedback, Analytics, Ollama Keep-Alive Manager
REM ============================================================

echo ============================================================
echo  UnaniMed AI Services Startup
echo ============================================================
echo.

REM ── Preflight: virtual environment check ──────────────────────
cd /d "%~dp0.."
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo         Run: python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM ── 1. ChromaDB (Docker) ──────────────────────────────────────
echo [1/11] Starting ChromaDB (Docker)...
docker start chromadb 2>nul
if %errorlevel% neq 0 (
    echo [WARN]  ChromaDB container not found — creating it now...
    docker run -d --name chromadb -p 8000:8000 ^
        -v "%CD%\chromadb_persist:/chroma/chroma" ^
        chromadb/chroma:latest
)
timeout /t 4 /nobreak > nul
echo [OK]    ChromaDB running on port 8000
echo.

REM ── 2. Ollama ─────────────────────────────────────────────────
echo [2/11] Starting Ollama...
start "Ollama Service" cmd /k "ollama serve"
timeout /t 5 /nobreak > nul
echo [OK]    Ollama running on port 11434
echo.

REM ── 3. STT Service (Port 8001) ────────────────────────────────
echo [3/11] Starting STT Service (Port 8001)...
start "STT Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\stt_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    STT Service started
echo.

REM ── 4. TTS Service (Port 8002) ────────────────────────────────
echo [4/11] Starting TTS Service (Port 8002)...
start "TTS Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\tts_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    TTS Service started
echo.

REM ── 5. Patient Profile Service (Port 8003) ────────────────────
echo [5/11] Starting Patient Profile Service (Port 8003)...
start "Patient Profile Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\patient_profile_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Patient Profile Service started
echo.

REM ── 6. Safety Check Service (Port 8004) ──────────────────────
echo [6/11] Starting Safety Check Service (Port 8004)...
start "Safety Check Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\safety_check_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Safety Check Service started
echo.

REM ── 7. Semantic Cache Service (Port 8005) ────────────────────
echo [7/11] Starting Semantic Cache Service (Port 8005)...
start "Semantic Cache Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\semantic_cache_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Semantic Cache Service started
echo.

REM ── 8. Bangla Normalizer (Port 8006) ─────────────────────────
echo [8/11] Starting Bangla Normalizer (Port 8006)...
start "Bangla Normalizer" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\utils\bangla_normalizer.py"
timeout /t 2 /nobreak > nul
echo [OK]    Bangla Normalizer started
echo.

REM ── 9. Feedback Service (Port 8007) ──────────────────────────
echo [9/11] Starting Feedback Service (Port 8007)...
start "Feedback Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\feedback_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Feedback Service started
echo.

REM ── 10. Analytics Service (Port 8008) ────────────────────────
echo [10/11] Starting Analytics Service (Port 8008)...
start "Analytics Service" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\services\analytics_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Analytics Service started
echo.

REM ── 11. Ollama Keep-Alive Manager (Port 8009) ────────────────
echo [11/11] Starting Ollama Keep-Alive Manager (Port 8009)...
start "Ollama Keep-Alive Manager" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python src\config\ollama_config.py"
timeout /t 3 /nobreak > nul
echo [OK]    Ollama Keep-Alive Manager started
echo.

REM ── Summary ───────────────────────────────────────────────────
echo ============================================================
echo  All Services Started!
echo ============================================================
echo.
echo  Service                    Port   URL
echo  ─────────────────────────────────────────────────────────
echo  ChromaDB (Docker)          8000   http://localhost:8000
echo  Ollama LLM                11434   http://localhost:11434
echo  STT  (Speech-to-Text)      8001   http://localhost:8001/health
echo  TTS  (Text-to-Speech)      8002   http://localhost:8002/health
echo  Patient Profile            8003   http://localhost:8003/health
echo  Safety Check               8004   http://localhost:8004/health
echo  Semantic Cache             8005   http://localhost:8005/health
echo  Bangla Normalizer          8006   http://localhost:8006/health
echo  Feedback                   8007   http://localhost:8007/health
echo  Analytics                  8008   http://localhost:8008/health
echo  Ollama Keep-Alive Mgr      8009   http://localhost:8009/health
echo.
echo  Next steps:
echo    1. Start n8n:  npx n8n start  (open http://localhost:5678)
echo    2. Import:     workflows\facebook-messenger-webhook-workflow-safety.json
echo    3. Import:     workflows\n8n-error-workflow.json
echo    4. Configure Telegram tokens in backup_config.json
echo.
echo  To stop all services: stop_all_services.bat
echo ============================================================
echo.
pause
