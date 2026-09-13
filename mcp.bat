@echo off
REM ─────────────────────────────────────────────────────────────
REM MCP MSSQL — Windows Helper Scripts
REM Run these from the project root folder
REM ─────────────────────────────────────────────────────────────

SET ACTION=%1

IF "%ACTION%"=="build" GOTO BUILD
IF "%ACTION%"=="up" GOTO UP
IF "%ACTION%"=="down" GOTO DOWN
IF "%ACTION%"=="logs" GOTO LOGS
IF "%ACTION%"=="restart" GOTO RESTART
IF "%ACTION%"=="shell" GOTO SHELL
IF "%ACTION%"=="clean" GOTO CLEAN
IF "%ACTION%"=="dev" GOTO DEV
GOTO HELP

:BUILD
echo [BUILD] Building Docker image...
docker compose build --no-cache
GOTO END

:UP
echo [UP] Starting services...
docker compose up -d
echo.
echo MCP Server running at: http://localhost:8000/sse
echo Redis running at:      localhost:6379
echo.
echo Use: mcp.bat logs  to watch logs
GOTO END

:DOWN
echo [DOWN] Stopping services...
docker compose down
GOTO END

:LOGS
echo [LOGS] Watching logs (Ctrl+C to stop)...
docker compose logs -f mcp-mssql
GOTO END

:RESTART
echo [RESTART] Restarting MCP server...
docker compose restart mcp-mssql
GOTO END

:SHELL
echo [SHELL] Opening shell in container...
docker compose exec mcp-mssql bash
GOTO END

:CLEAN
echo [CLEAN] Removing containers, images, volumes...
docker compose down --rmi local --volumes --remove-orphans
GOTO END

:DEV
echo [DEV] Starting in dev mode with live reload...
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
GOTO END

:HELP
echo.
echo Usage: mcp.bat [command]
echo.
echo Commands:
echo   build     Build the Docker image
echo   up        Start all services in background
echo   down      Stop all services
echo   logs      Watch MCP server logs
echo   restart   Restart MCP server only
echo   shell     Open bash shell in container
echo   clean     Remove everything (containers + images)
echo   dev       Start in dev mode with live reload
echo.

:END
