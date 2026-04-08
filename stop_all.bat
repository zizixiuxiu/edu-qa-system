@echo off
echo [INFO] Stopping all backend and frontend processes...

:: Kill Python processes (backend & experiments)
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul

:: Kill Node processes (frontend)
taskkill /F /IM node.exe 2>nul
taskkill /F /IM npm.exe 2>nul

:: Kill Uvicorn
taskkill /F /IM uvicorn.exe 2>nul

echo [INFO] Checking port status...
python -c "import socket; s=socket.socket(); result=s.connect_ex(('localhost',8000)); print('  Port 8000 (backend):', 'CLOSED' if result!=0 else 'STILL OPEN'); s.close()" 2>nul
python -c "import socket; s=socket.socket(); result=s.connect_ex(('localhost',3002)); print('  Port 3002 (frontend):', 'CLOSED' if result!=0 else 'STILL OPEN'); s.close()" 2>nul

echo [INFO] All processes stopped!
pause
