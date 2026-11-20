@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 wt_api_explorer.py %*
) else (
  python wt_api_explorer.py %*
)
if errorlevel 1 pause
