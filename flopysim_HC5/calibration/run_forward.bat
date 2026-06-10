@echo off
REM ---------------------------------------------------------------------------
REM run_forward.bat  --  the model command PEST++ invokes each iteration.
REM Launches forward_run.py with the Python of the CURRENTLY ACTIVATED env.
REM Run pestpp-glm from an activated environment, e.g.:
REM     conda activate Samin_GWM2
REM     pestpp-glm calib.pst
REM so that `python` resolves to that env (which has flopy/pyogrio/pyemu).
REM ---------------------------------------------------------------------------
cd /d "%~dp0"
python "%~dp0forward_run.py"
