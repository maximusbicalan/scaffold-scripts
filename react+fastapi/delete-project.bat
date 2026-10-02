@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"

rem Projects are created one directory above react+fastapi.
for %%I in ("%SCRIPT_DIR%..") do set "PROJECTS_DIR=%%~fI"

if not "%~2"=="" goto :usage
if "%~1"=="" goto :usage

set "PROJECT_NAME=%~1"

rem Only allow a simple directory name, never a path.
if "%PROJECT_NAME%"=="." goto :invalid_name
if "%PROJECT_NAME%"==".." goto :invalid_name
if not "%PROJECT_NAME:\=%"=="%PROJECT_NAME%" goto :invalid_name
if not "%PROJECT_NAME:/=%"=="%PROJECT_NAME%" goto :invalid_name

set "PROJECT_DIR=%PROJECTS_DIR%\%PROJECT_NAME%"

if not exist "%PROJECT_DIR%\NUL" (
    echo Error: project directory does not exist:
    echo   "%PROJECT_DIR%"
    exit /b 1
)

echo WARNING: This will permanently delete:
echo   Project directory: "%PROJECT_DIR%"
echo   Docker containers, networks, and volumes belonging to this project
echo.

set /p "CONFIRMATION=Retype the project name ""%PROJECT_NAME%"" to confirm: "

if not "%CONFIRMATION%"=="%PROJECT_NAME%" (
    echo Project name did not match. Deletion cancelled.
    exit /b 1
)

rem Check whether the project contains a Docker Compose file.
set "HAS_COMPOSE="

if exist "%PROJECT_DIR%\compose.yaml" set "HAS_COMPOSE=1"
if exist "%PROJECT_DIR%\compose.yml" set "HAS_COMPOSE=1"
if exist "%PROJECT_DIR%\docker-compose.yaml" set "HAS_COMPOSE=1"
if exist "%PROJECT_DIR%\docker-compose.yml" set "HAS_COMPOSE=1"

if defined HAS_COMPOSE goto :remove_docker
goto :delete_project

:remove_docker
where docker >nul 2>&1

if errorlevel 1 (
    echo Error: Docker is required to remove the project's Docker resources. >&2
    echo The project directory was not deleted. >&2
    exit /b 1
)

echo Removing Docker resources...

pushd "%PROJECT_DIR%"

docker compose down -v --remove-orphans

if errorlevel 1 (
    popd
    echo Error: Docker cleanup failed. >&2
    echo The project directory was not deleted. >&2
    exit /b 1
)

popd

:delete_project
echo Deleting project directory...

rmdir /s /q "%PROJECT_DIR%"

if exist "%PROJECT_DIR%\NUL" (
    echo Error: the project directory could not be completely deleted. >&2
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