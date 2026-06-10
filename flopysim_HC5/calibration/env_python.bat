@echo off
REM ---------------------------------------------------------------------------
REM env_python.bat  --  run a script with the standalone "climate" Python so its
REM compiled deps (flopy/geopandas/rasterio) find their DLLs without conda activate.
REM Usage:  env_python.bat <script.py> [args...]
REM ---------------------------------------------------------------------------
set "CLIMATE=D:\Users\abolmaal\softwaters\climate"
set "PATH=%CLIMATE%;%CLIMATE%\Library\bin;%CLIMATE%\Library\mingw-w64\bin;%CLIMATE%\Library\usr\bin;%CLIMATE%\Scripts;%CLIMATE%\bin;%CLIMATE%\DLLs;%PATH%"
"%CLIMATE%\python.exe" %*
