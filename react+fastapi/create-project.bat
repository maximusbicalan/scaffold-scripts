@echo off
setlocal

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required: https://docs.astral.sh/uv/getting-started/installation/
  exit /b 1
)

uv run --no-project python "%~dp0create_fullstack_project.py" %*
