@echo off

setlocal

cd /d "%~dp0"

echo Starting Spectral_Analyser pipeline orchestrator (Tk / tier GUI)...

echo   Target: pipeline_orchestrator_gui.py

echo   Full integrated CLI pipeline: python run_orchestrator.py

echo.

python pipeline_orchestrator_gui.py %*

if errorlevel 1 (

  echo.

  echo Orchestrator exited with an error ^(exit code %ERRORLEVEL%^).

  pause

  exit /b %ERRORLEVEL%

)

endlocal

