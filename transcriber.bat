@echo off
REM Change to the directory where this script is located
cd /d %~dp0

REM Activate the virtual environment located in the "venv" folder in the current directory
call venv\Scripts\activate.bat

REM Run the transcriber script (ensure the script name matches exactly)
python meet.py

REM Optional: Pause to keep the window open after the script finishes
pause
