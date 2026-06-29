"""Diagnose the PROJ DLL load in a CLEAN environment (mimics the nbconvert kernel).

Run:  F:\\python_envs\\Samin_GWM2\\python.exe test_dll.py
It tries to import pyproj two ways inside a fresh subprocess whose environment has
the conda activation stripped out (no PROJ_LIB / CONDA_PREFIX, no Library\\bin on
PATH) -- the same condition the kernel runs in -- so we can see which fix works.
"""
import os
import sys
import glob
import subprocess

env_root = os.path.dirname(sys.executable)
lib_bin = os.path.normpath(os.path.join(env_root, "Library", "bin"))
print("python      :", sys.executable)
print("env root    :", env_root)
print("Library\\bin :", lib_bin, "| exists:", os.path.isdir(lib_bin))
print("proj dlls   :", [os.path.basename(p) for p in glob.glob(os.path.join(lib_bin, "proj*.dll"))])
print("sqlite/tiff :", [os.path.basename(p) for p in
                        glob.glob(os.path.join(lib_bin, "*sqlite*.dll")) +
                        glob.glob(os.path.join(lib_bin, "*tiff*.dll"))][:6])

# build a clean env: drop conda activation vars and remove Library\bin from PATH
clean = {k: v for k, v in os.environ.items()
         if k.upper() not in ("PROJ_LIB", "PROJ_DATA", "GDAL_DATA", "CONDA_PREFIX")}
clean["PATH"] = os.pathsep.join(
    p for p in clean.get("PATH", "").split(os.pathsep) if lib_bin.lower() not in p.lower())


def run(label, code, env):
    print("\n====", label, "====")
    r = subprocess.run([sys.executable, "-c", code], env=env,
                       capture_output=True, text=True)
    print("exit", r.returncode)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        print("STDERR (tail):")
        print(r.stderr[-1600:])


# A) clean env, register Library\bin via add_dll_directory, import pyproj
run("A) clean env + os.add_dll_directory(Library\\bin)",
    "import os\n"
    f"os.add_dll_directory(r'{lib_bin}')\n"
    "import pyproj; print('pyproj', pyproj.__version__, 'OK')\n",
    clean)

# B) clean env, put Library\bin on PATH, import pyproj
clean_path = dict(clean)
clean_path["PATH"] = lib_bin + os.pathsep + clean["PATH"]
run("B) clean env + Library\\bin on PATH",
    "import pyproj; print('pyproj', pyproj.__version__, 'OK')\n",
    clean_path)

# C) clean env, set CONDA_PREFIX (lets the env python self-init its DLL dirs)
clean_cp = dict(clean)
clean_cp["CONDA_PREFIX"] = env_root
run("C) clean env + CONDA_PREFIX set",
    "import pyproj; print('pyproj', pyproj.__version__, 'OK')\n",
    clean_cp)
