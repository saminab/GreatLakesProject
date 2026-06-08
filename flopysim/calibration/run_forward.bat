@echo off
REM ---------------------------------------------------------------------------
REM run_forward.bat  --  the model command PEST++ invokes each iteration.
REM Runs forward_run.py under the climate env.  Always executes relative to its
REM own folder so PEST++ can call it from anywhere.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"
call "%~dp0env_python.bat" "%~dp0forward_run.py"
