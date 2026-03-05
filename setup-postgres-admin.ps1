# Admin script to complete PostgreSQL installation and setup databases
# Right-click and "Run as Administrator" to execute

Write-Host "========================================"
Write-Host "PostgreSQL & Database Setup"
Write-Host "========================================"
Write-Host ""

# Check if PostgreSQL is already installed
if (Test-Path "C:\Program Files\PostgreSQL\15\bin\psql.exe") {
    Write-Host "[OK] PostgreSQL is already installed"
} else {
    Write-Host "Installing PostgreSQL 15..."
    $pgInstaller = "$env:TEMP\postgresql-15-installer.exe"
    
    # Download if not exists
    if (-not (Test-Path $pgInstaller)) {
        Write-Host "Downloading PostgreSQL..."
        $url = 'https://get.enterprisedb.com/postgresql/postgresql-15.17-1-windows-x64.exe'
        Invoke-WebRequest -Uri $url -OutFile $pgInstaller -ErrorAction Stop
    }
    
    # Install
    Write-Host "Running PostgreSQL installer (this may take a few minutes)..."
    & $pgInstaller /S /D='C:\Program Files\PostgreSQL\15' | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] PostgreSQL installed successfully"
    } else {
        Write-Host "[ERROR] PostgreSQL installation failed"
        exit 1
    }
}

# Add PostgreSQL to PATH for this session
$env:Path += ";C:\Program Files\PostgreSQL\15\bin"

Write-Host ""
Write-Host "Setting up database and user..."

# Wait a moment for PostgreSQL service to start
Start-Service -Name postgresql-x64-15 -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Create database and user (matches backend .env)
$dbUser = "user"
$dbPassword = "test123"
try {
    # Create user
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE USER `"$dbUser`" WITH PASSWORD '$dbPassword';" 2>&1 | Out-Null
    Write-Host "[OK] Database user '$dbUser' created (or already exists)"
} catch {
    Write-Host "[WARNING] Could not create user: $_"
}

try {
    # Create database
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE insights_db OWNER `"$dbUser`";" 2>&1 | Out-Null
    Write-Host "[OK] Database 'insights_db' created"
} catch {
    Write-Host "[WARNING] Could not create database: $_"
}

Write-Host ""
Write-Host "========================================"
Write-Host "Setup Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Database Connection Details:"
Write-Host "  Host: localhost"
Write-Host "  Port: 5432"
Write-Host "  User: $dbUser"
Write-Host "  Password: $dbPassword"
Write-Host "  Database: insights_db"
Write-Host ""
Write-Host "PostgreSQL Service Status:"
Get-Service -Name postgresql-x64-15 -ErrorAction SilentlyContinue | Select-Object Status, DisplayName
Write-Host ""
Write-Host "You can now run: .\start-local.bat"
Write-Host ""
pause
