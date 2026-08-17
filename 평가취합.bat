@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Vibe Editor - collect evaluations
echo ============================================
echo.
"%~dp0..\backend\venv\Scripts\python.exe" collect_evals.py
echo.
pause
