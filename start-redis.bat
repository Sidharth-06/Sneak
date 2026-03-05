@echo off
REM Start Redis Server
echo Starting Redis Server...
echo.

if exist "C:\Program Files\Redis\redis-server.exe" (
    echo Redis found at: C:\Program Files\Redis
    start "Redis Server" "C:\Program Files\Redis\redis-server.exe" redis.windows.conf
    timeout /t 2 /nobreak
    
    REM Verify Redis is running
    echo.
    echo Checking Redis connection...
    "C:\Program Files\Redis\redis-cli.exe" ping
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ✓ Redis is running on port 6379
    ) else (
        echo.
        echo ✗ Redis failed to start
    )
) else (
    echo ✗ Redis not found at C:\Program Files\Redis
    echo Please ensure Redis was installed successfully
    pause
    exit /b 1
)
