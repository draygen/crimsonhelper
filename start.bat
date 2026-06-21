@echo off
setlocal

REM ── CrimsonHelper Launcher ────────────────────────────────────────────────────
REM Starts the Python backend (which also launches the collab server) inside WSL.
REM The React dev server only runs when you're developing the frontend.
REM In production, `npm run build` copies the SPA into backend/static/ automatically.

set BACKEND_PORT=8000
set WSL_DISTRO=

echo [CrimsonHelper] Starting backend...

REM Launch the backend in WSL (auto-detects default distro)
if "%WSL_DISTRO%"=="" (
    wsl bash -c "cd /mnt/c/projects/crimsonhelper/backend && source venv/bin/activate 2>/dev/null || true && python -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
) else (
    wsl -d %WSL_DISTRO% bash -c "cd /mnt/c/projects/crimsonhelper/backend && source venv/bin/activate 2>/dev/null || true && python -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
)

pause
