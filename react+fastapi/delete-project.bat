@echo off
setlocal EnableExtensions DisableDelayedExpansion

if not "%~2"=="" goto :usage
if "%~1"=="" goto :usage

set "PROJECT_NAME=%~1"

rem Only allow a simple directory name, never a path.
if "%PROJECT_NAME%"=="." goto :invalid_name
if "%PROJECT_NAME%"==".." goto :invalid_name
if not "%PROJECT_NAME:\=%"=="%PROJECT_NAME%" goto :invalid_name
if not "%PROJECT_NAME:/=%"=="%PROJECT_NAME%" goto :invalid_name

set "PROJECT_DIR=%~dp0%PROJECT_NAME%"

if not exist "%PROJECT_DIR%\NUL" (
    echo Error: project directory does not exist:
    echo   "%PROJECT_DIR%"
    exit /b 1
)

echo WARNING: This will permanently delete:
echo   "%PROJECT_DIR%"
set /p "CONFIRMATION=Retype the project name ""%PROJECT_NAME%"" to confirm: "

if not "%CONFIRMATION%"=="%PROJECT_NAME%" (
    echo Project name did not match. Deletion cancelled.
    exit /b 1
)

rmdir /s /q "%PROJECT_DIR%"

if exist "%PROJECT_DIR%\NUL" (
    echo Error: the project could not be completely deleted.
    exit /b 1
)

echo Deleted project: %PROJECT_NAME%
exit /b 0

:usage
echo Usage: %~nx0 ^<project-name^> >&2
exit /b 1

:invalid_name
echo Error: provide a project name, not a path. >&2
exit /b 1