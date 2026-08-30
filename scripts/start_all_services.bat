@echo off
REM ============================================================
REM  UnaniMed AI — Start All Services (Multimodal Production)
REM  Services: ChromaDB, Ollama, STT, TTS, Patient Profile,
REM            Safety Check, Semantic Cache, Bangla Normalizer,
REM            Feedback, Analytics, Ollama Keep-Alive Manager,
REM            Unified AI Web Portal & Orchestrator (Port 8010)
REM ============================================================

echo ============================================================
echo  UnaniMed AI Multimodal Services Startup
echo ============================================================
echo.

REM ── Preflight: virtual environment check ──────────────────────
cd /d "%~dp0.."
if not exist "venv\Scripts\activate.bat" (
    if not exist ".venv\Scripts\activate.bat" (
        echo [WARN] Virtual environment not found in venv or .venv!
        echo        Running with global Python...
    )
)

REM ── 1. ChromaDB (Docker) ──────────────────────────────────────
echo [1/12] Starting ChromaDB (Docker)...
docker start chromadb 2>nul
if %errorlevel% neq 0 (
    echo [WARN]  ChromaDB container not found — creating it now...
    docker run -d --name chromadb -p 8000:8000 ^
        -v "%CD%\chromadb_persist:/chroma/chroma" ^
        chromadb/chroma:latest 2>nul
)
timeout /t 3 /nobreak > nul
echo [OK]    ChromaDB check complete
echo.

REM ── 2. Ollama ─────────────────────────────────────────────────
echo [2/12] Starting Ollama Local LLM Engine...
start "Ollama Service" cmd /k "ollama serve"
timeout /t 4 /nobreak > nul
echo [OK]    Ollama running on port 11434
echo.

REM ── 3. STT Service (Port 8001) ────────────────────────────────
echo [3/12] Starting STT Service (Port 8001)...
start "STT Service" cmd /k "cd /d %CD% && python src\services\stt_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    STT Service started
echo.

REM ── 4. TTS Service (Port 8002) ────────────────────────────────
echo [4/12] Starting TTS Service (Port 8002)...
start "TTS Service" cmd /k "cd /d %CD% && python src\services\tts_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    TTS Service started
echo.

REM ── 5. Patient Profile Service (Port 8003) ────────────────────
echo [5/12] Starting Patient Profile Service (Port 8003)...
start "Patient Profile Service" cmd /k "cd /d %CD% && python src\services\patient_profile_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Patient Profile Service started
echo.

REM ── 6. Safety Check Service (Port 8004) ──────────────────────
echo [6/12] Starting Safety Check Service (Port 8004)...
start "Safety Check Service" cmd /k "cd /d %CD% && python src\services\safety_check_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Safety Check Service started
echo.

REM ── 7. Semantic Cache Service (Port 8005) ────────────────────
echo [7/12] Starting Semantic Cache Service (Port 8005)...
start "Semantic Cache Service" cmd /k "cd /d %CD% && python src\services\semantic_cache_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Semantic Cache Service started
echo.

REM ── 8. Bangla Normalizer (Port 8006) ─────────────────────────
echo [8/12] Starting Bangla Normalizer (Port 8006)...
start "Bangla Normalizer" cmd /k "cd /d %CD% && python src\utils\bangla_normalizer.py"
timeout /t 2 /nobreak > nul
echo [OK]    Bangla Normalizer started
echo.

REM ── 9. Feedback Service (Port 8007) ──────────────────────────
echo [9/12] Starting Feedback Service (Port 8007)...
start "Feedback Service" cmd /k "cd /d %CD% && python src\services\feedback_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Feedback Service started
echo.

REM ── 10. Analytics Service (Port 8008) ────────────────────────
echo [10/12] Starting Analytics Service (Port 8008)...
start "Analytics Service" cmd /k "cd /d %CD% && python src\services\analytics_service.py"
timeout /t 2 /nobreak > nul
echo [OK]    Analytics Service started
echo.

REM ── 11. Ollama Keep-Alive Manager (Port 8009) ────────────────
echo [11/12] Starting Ollama Keep-Alive Manager (Port 8009)...
start "Ollama Keep-Alive Manager" cmd /k "cd /d %CD% && python src\config\ollama_config.py"
timeout /t 2 /nobreak > nul
echo [OK]    Ollama Keep-Alive Manager started
echo.

REM ── 12. Unified AI Master Web Portal & Orchestration (Port 8010) ──
echo [12/12] Starting Unified AI Orchestrator & Web Portal (Port 8010)...
start "UnaniMed AI Unified Portal" cmd /k "cd /d %CD% && python src\services\unified_ai_service.py"
timeout /t 3 /nobreak > nul
echo [OK]    Unified Web Portal running at http://localhost:8010
echo.

REM ── Summary ───────────────────────────────────────────────────
echo ============================================================
echo  UnaniMed AI Multimodal System Ready!
echo ============================================================
echo.
echo  Service                            Port    URL
echo  ─────────────────────────────────────────────────────────────
echo  🌟 UNIFIED WEB PORTAL (Voice/Vision) 8010   http://localhost:8010
echo  Ollama LLM (llama3.1:8b)          11434    http://localhost:11434
echo  STT  (Speech-to-Text)              8001    http://localhost:8001/health
echo  TTS  (Text-to-Speech)              8002    http://localhost:8002/health
echo  Patient Profile                    8003    http://localhost:8003/health
echo  Safety Check                       8004    http://localhost:8004/health
echo  Customer Leads DB & Telegram       8010    http://localhost:8010/api/leads
echo  Herbal Visual Catalog              8010    http://localhost:8010/api/herbs
echo.
echo  To open the Web Portal:
echo    Start browser and visit http://localhost:8010
echo.
echo  To stop all services: scripts\stop_all_services.bat
echo ============================================================
echo.
pause
