@echo off
REM Setup PostgreSQL database
echo Setting up PostgreSQL database...

REM Check if PostgreSQL is installed
WHERE psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PostgreSQL is not installed or psql is not in PATH
    echo Please install PostgreSQL from https://www.postgresql.org/download/windows/
    exit /b 1
)

REM Create database and user if not exists
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'insights_db'" | findstr /B "1" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Creating database and user...
    psql -U postgres -c "CREATE USER user WITH PASSWORD 'password';"
    psql -U postgres -c "CREATE DATABASE insights_db OWNER user;"
    psql -U postgres -c "ALTER USER user CREATEDB;"
    echo Database setup complete!
) else (
    echo Database already exists
)

REM Check if Redis is running
netstat -an | findstr "6379" >nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Redis is not running on port 6379
    echo Please start Redis Server
    echo Download: https://github.com/microsoftarchive/redis/releases
)

echo Setup complete! Run start-local.bat to start the application
pause
