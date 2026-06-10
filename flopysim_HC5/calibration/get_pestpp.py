"""
get_pestpp.py  --  download the PEST++ executables (pestpp-glm, pestpp-ies, ...).

None are installed in the climate env yet.  This fetches the official binaries
into this calibration/ folder so you can run:  pestpp-glm calib.pst

Run via:  env_python.bat get_pestpp.py
"""
import os
import pyemu

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    pyemu.utils.get_pestpp(bindir=HERE)
    print("PEST++ binaries downloaded to:", HERE)
except Exception as e:
    print("Automatic download failed:", e)
    print("Manually download from https://github.com/usgs/pestpp/releases and "
          "place pestpp-glm.exe in this folder.")
