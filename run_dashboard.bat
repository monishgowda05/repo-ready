@echo off
cd /d "%~dp0"
echo Starting RepoReady Streamlit Dashboard...
.\venv\Scripts\streamlit.exe run app.py
pause
