@echo off
setlocal EnableExtensions
title SoundSpectrAnalyse - Installer
cd /d "%~dp0"
call "%~dp0Install and Run.bat"
exit /b %ERRORLEVEL%
