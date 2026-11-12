@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m streamlit run intake.py
if errorlevel 9009 py -m streamlit run intake.py
pause
