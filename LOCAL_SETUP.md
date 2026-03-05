# Local Development Setup - COMPLETE ✅

## Installation Status

### ✅ Already Done
- Python virtual environment created
- Python dependencies installed  
- Node.js dependencies installed
- `.env` files configured
- Startup scripts created
- **Redis installed** at `C:\Program Files\Redis`

### ⏳ Next Step: PostgreSQL Setup
You need to complete PostgreSQL installation (requires Admin privileges)

---

## STEP-BY-STEP SETUP

### 1️⃣ Complete PostgreSQL Installation

**Right-click and run as Administrator:**
```
setup-postgres-admin.ps1
```

This will:
- Install PostgreSQL 15 (if needed)
- Create database `insights_db`
- Create database user `user` with password `password`
- Start PostgreSQL service

**Time:** 2-3 minutes

---

### 2️⃣ Start Services

**Option A: Automatic (Recommended)**
```powershell
.\start-local.bat
```
This opens 2 windows automatically:
- Backend API terminal
- Frontend terminal

**Option B: Manual - Start Redis First**
```powershell
.\start-redis.bat
```
Then in another terminal:
```powershell
cd backend
.\venv\Scripts\activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then in another terminal:
```powershell
cd frontend
npm run dev
```

---

### 3️⃣ Verify Everything Works

✅ **Backend API**: Open http://localhost:8000/docs (shows interactive API docs)

✅ **Frontend**: Open http://localhost:3000

✅ **API Health Check**:
```powershell
curl http://localhost:8000/
```

---

## Connection Details

**PostgreSQL**
- Host: localhost
- Port: 5432
- User: user
- Password: password
- Database: insights_db

**Redis**
- Host: localhost
- Port: 6379

**Backend API**
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs

**Frontend**
- URL: http://localhost:3000

---

## Environment Files

### Backend `.env`
```
POSTGRES_SERVER=localhost
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=insights_db
REDIS_URL=redis://localhost:6379/0
SEARXNG_URL=http://localhost:8080
GEMINI_API_KEY=
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Database Migrations

Tables will be created automatically on first API startup.

To manually run migrations:
```powershell
cd backend
.\venv\Scripts\activate.ps1
alembic upgrade head
```

---

## Troubleshooting

### PostgreSQL Issues

**Error: "psql: command not found"**
- Run `setup-postgres-admin.ps1` as Administrator
- Or download from: https://www.postgresql.org/download/windows/

**Error: "connection refused"**
```powershell
# Start PostgreSQL service
net start postgresql-x64-15
```

**To manage PostgreSQL service:**
- Press `Win + R`, type `services.msc`
- Find `postgresql-x64-15`
- Right-click → Start/Stop/Restart

---

### Redis Issues

**Error: "redis-server: command not found"**
- Close and reopen PowerShell (terminal needs refresh)
- Or run `start-redis.bat`

**Error: "Connection refused on port 6379"**
```powershell
.\start-redis.bat
```

**To manage Redis service:**
- It runs in a window (no background service)
- Just run `start-redis.bat` when needed

---

### Backend/Frontend Issues

**Backend won't start**
1. Check PostgreSQL is running: `net start postgresql-x64-15`
2. Check logs in the backend terminal window
3. Verify database exists: `psql -U user -d insights_db -h localhost -c "SELECT 1;"`

**Frontend shows errors**
1. Check backend is running: `curl http://localhost:8000/`
2. Check `.env.local` file has correct API URL
3. Delete `frontend/.next` folder (Next.js cache)

**Port already in use (8000 or 3000)**
```powershell
# Find process using port 8000
netstat -ano | findstr ":8000"

# Kill it (replace PID with the number)
taskkill /PID <PID> /F
```

---

## Useful Commands

**Check if services are running:**
```powershell
# PostgreSQL
net start | findstr postgres

# Redis
redis-cli ping
```

**View backend logs:**
```powershell
cd backend
.\venv\Scripts\activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

**Stop everything:**
```powershell
# Close terminal windows (Ctrl+C)

# Stop PostgreSQL service
net stop postgresql-x64-15

# Or use Services app: services.msc
```

---

## Next Steps

1. **Run:** `.\setup-postgres-admin.ps1` (as Administrator)
2. **Wait:** ~2-3 minutes for installation
3. **Run:** `.\start-local.bat`
4. **Open:** http://localhost:3000 in your browser
5. **Check:** http://localhost:8000/docs for API documentation

---

**Need help?** Check the troubleshooting section above.

🚀 **Ready? Let's go!**
