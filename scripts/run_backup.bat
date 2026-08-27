@echo off
REM Automated Backup Script for Windows Task Scheduler
REM This script runs the Python backup script

cd /d "C:\Users\Admin\Documents\dev\office-dev\unani-med-ai"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run backup script
python scripts\backup_script.py

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo Backup completed at %date% %time%