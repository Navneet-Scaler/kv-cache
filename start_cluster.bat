@echo off
REM Quick start script for KV-Cache cluster (Windows)

echo === KV-Cache Cluster Quick Start ===
echo.

echo Step 1: Building Docker images...
docker compose build

if %errorlevel% neq 0 (
    echo ERROR: Build failed
    exit /b 1
)

echo.
echo Step 2: Starting cluster (3 nodes)...
docker compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start cluster
    exit /b 1
)

echo.
echo Step 3: Waiting for nodes to start...
timeout /t 5 /nobreak > nul

echo.
echo Step 4: Checking node health...
for %%p in (5001 5002 5003) do (
    powershell -Command "Test-NetConnection -ComputerName localhost -Port %%p -InformationLevel Quiet" > nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] Node on port %%p is UP
    ) else (
        echo   [!!] Node on port %%p is DOWN
    )
)

echo.
echo === Cluster Started Successfully ===
echo.
echo Node URLs:
echo   Node 1: localhost:5001
echo   Node 2: localhost:5002
echo   Node 3: localhost:5003
echo.
echo Quick test (using Python):
echo   python -c "import socket; s=socket.socket(); s.connect(('localhost',5001)); s.send(b'PUT test hello\n'); print(s.recv(1024).decode())"
echo.
echo View logs:
echo   docker compose logs -f
echo.
echo Stop cluster:
echo   docker compose down
echo.
