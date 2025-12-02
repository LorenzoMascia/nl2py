@echo off
REM NL2Py Docker - Stop Script (Windows)

echo.
echo Stopping NL2Py Docker Environment...
echo.

docker-compose down

echo.
echo All services stopped
echo.
echo To remove all data volumes, run:
echo    docker-compose down -v
echo.
echo To start again, run:
echo    start.bat
echo.
pause
