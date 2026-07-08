@echo off
REM LunaLink - one command to install dependencies and launch the dashboard.
REM   Usage:  run.bat          (installs on first run and opens the GUI)
REM           run.bat sim      (runs the headless simulation instead)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv 2>nul || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r code\requirements.txt
)

set MPLCONFIGDIR=.cache\matplotlib
if "%1"=="sim" (
  .venv\Scripts\python code\main_simulation.py --out outputs\baseline
) else (
  .venv\Scripts\streamlit run code\main_gui.py
)
