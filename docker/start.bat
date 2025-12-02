@echo off
REM NL2Py Docker - Start Script (Windows)

echo.
echo Starting NL2Py Docker Environment...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

REM Check if config file exists
if not exist "config\nl2py.conf" (
    echo Error: Configuration file not found
    echo Please ensure config\nl2py.conf exists
    pause
    exit /b 1
)

REM Check for OpenAI API key
findstr /C:"your-openai-api-key-here" config\nl2py.conf >nul
if %errorlevel%==0 (
    echo Warning: OpenAI API key not configured
    echo Please edit config\nl2py.conf and set your API key
    echo.
    set /p "continue=Continue anyway? (y/N): "
    if /i not "%continue%"=="y" exit /b 1
)

echo Building and starting services...
docker-compose up -d

echo.
echo Waiting for services to be healthy...
echo This may take 30-60 seconds...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo Service Status:
docker-compose ps

echo.
echo NL2Py Docker Environment Started!
echo.
echo Service URLs:
echo    RabbitMQ:    http://localhost:15672  (nl2py/nl2py123)
echo    MinIO:       http://localhost:9001   (nl2py/nl2py123)
echo    OpenSearch:  https://localhost:9200  (admin/Aibasic123!)
echo    MailHog:     http://localhost:8025
echo.
echo Access NL2Py:
echo    docker exec -it nl2py bash
echo.
echo View logs:
echo    docker-compose logs -f
echo.
echo Stop services:
echo    stop.bat
echo.
pause
