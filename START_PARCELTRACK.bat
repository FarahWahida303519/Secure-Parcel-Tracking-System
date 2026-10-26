@echo off
title ParcelTrack - Keep this window open
cd /d "%~dp0"
python launch.py
if errorlevel 1 (
  echo.
  echo ParcelTrack could not start. Please share the error shown above.
  pause
)
