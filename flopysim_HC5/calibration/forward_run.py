"""
forward_run.py  --  One PEST++ forward run (model command).

PEST++ calls this once per trial parameter set.  Steps:

  1. Tell config.py to read the trial parameters PEST++ just wrote into
     calibration/pest_params.dat  (via the GLB_PEST_PARAMS env var).
  2. Run MODFLOW 6 by executing Modeflow6_SImulation.ipynb headless.  The
     notebook does `from config import *`, so it uses the overridden knobs.
  3. Read the head file and extract the simulated head at each observation
     cell -- streaming one stress period at a time so RAM stays low.
  4. Write calibration/sim_heads.dat (one "obsname value" line per target),
     which the PEST instruction file (.ins) reads back.

------------------------------------------------------------------------------
TWO MODES (set SS_ONLY below):

  SS_ONLY = True   (recommended, ~2x faster)
      Run ONLY the warm-up spin-up cells of the notebook (everything before the
      transient model build) and compare against the warm-up EQUILIBRIUM heads
      in {nameModel_SS}.hds.  Static water levels are undated and the head
      comparison uses the long-term mean, which the warm-up equilibrium already
      represents -- so this is the physically appropriate, cheaper target.
      The transient (312-period) run is SKIPPED during calibration.

  SS_ONLY = False  (full transient)
      Run the whole notebook and compare against the temporal-mean head over all
      312 stress periods in {nameModel}.hds (identical statistic to Cell 12 of
      the output notebook).  Use this to VALIDATE the final calibrated set.
------------------------------------------------------------------------------
"""
import os
import sys
import time
import json
import subprocess

# --- mode switch -------------------------------------------------------------
SS_ONLY = False         # True = warm-up equilibrium only (fast);  False = full transient
#   NOTE: currently False for the transient VALIDATION run. Set back to True for
#   the SS calibration (each forward run = the fast warm-up only).
# -----------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
FLOPYSIM_DIR = os.path.dirname(HERE)

PARAM_FILE = os.path.join(HERE, "pest_params.dat")
OBS_FILE   = os.path.join(HERE, "obs_wells.csv")
SIM_OUT    = os.path.join(HERE, "sim_heads.dat")
NOTEBOOK   = os.path.join(FLOPYSIM_DIR, "Modeflow6_SImulation.ipynb")
TRIMMED_NB = os.path.join(HERE, "_calib_run.ipynb")         # generated each SS-only run
EXECUTED_NB = os.path.join(HERE, "Modeflow6_SImulation_lastrun.ipynb")

RUN_TIMEOUT_S = 86400        # 24-hour ceiling per forward run

# A kernel that points at THIS interpreter (the env that launched forward_run,
# i.e. whatever run_forward.bat invokes). Registering it on the fly guarantees
# the notebook executes in the same env -- no "wrong python3 kernel" mismatch.
KERNEL_NAME = "glb_calib"

# Marker identifying the cell that BUILDS the full transient model.  For SS-only
# we keep every cell BEFORE this one (build inputs + warm-up + clean heads).
TRANSIENT_MARKER = "sim_name=nameSim"

# Setup cell prepended to the executed notebook.  It (1) makes the model package
# importable (sys.path + cwd) and (2) registers the conda env's DLL folders so
# PROJ/GDAL load even when the kernel subprocess did NOT inherit a full conda
# activation.  That clean-kernel-env case is what produces "DLL load failed while
# importing _context" / "PROJ_LIB = None" in the notebook -- this fixes it at the
# source by calling os.add_dll_directory() inside the kernel before any geo import.
_SETUP_SRC = (
    "import os, sys\n"
    "_env = os.path.dirname(sys.executable)\n"
    "# NOTE: os.add_dll_directory needs NORMALIZED (backslash) paths on Windows -- "
    "forward slashes silently fail to register the directory.\n"
    "_dirs = [os.path.normpath(os.path.join(_env, s)) for s in "
    "('Library/bin', 'Library/mingw-w64/bin', 'Library/usr/bin', 'DLLs', '')]\n"
    "_dirs = [d for d in _dirs if os.path.isdir(d)]\n"
    "for _d in _dirs:\n"
    "    try:\n"
    "        os.add_dll_directory(_d)\n"
    "    except Exception as _e:\n"
    "        print('[setup] add_dll_directory FAILED for', _d, '->', _e, flush=True)\n"
    "os.environ['PATH'] = os.pathsep.join(_dirs) + os.pathsep + os.environ.get('PATH', '')\n"
    "os.environ['PROJ_LIB'] = os.path.normpath(os.path.join(_env, 'Library', 'share', 'proj'))\n"
    "os.environ['PROJ_DATA'] = os.environ['PROJ_LIB']\n"
    "os.environ['GDAL_DATA'] = os.path.normpath(os.path.join(_env, 'Library', 'share', 'gdal'))\n"
    "print('[setup] dll dirs registered:', _dirs, flush=True)\n"
    "print('[setup] PROJ_LIB:', os.environ['PROJ_LIB'], flush=True)\n"
    f"sys.path.insert(0, r'{FLOPYSIM_DIR}')\n"
    f"os.chdir(r'{FLOPYSIM_DIR}')\n"
)


def _write_ss_only_notebook():
    """Write a trimmed notebook = all cells before the transient build cell."""
    import nbformat
    nb = nbformat.read(NOTEBOOK, as_version=4)
    cut = None
    for idx, c in enumerate(nb.cells):
        if c.cell_type == "code" and TRANSIENT_MARKER in "".join(c.source):
            cut = idx
            break
    if cut is None:
        raise RuntimeError(
            f"Could not find transient build cell (marker '{TRANSIENT_MARKER}'). "
            f"Set SS_ONLY=False or update the marker.")
    nb.cells = nb.cells[:cut]
    # Prepend the setup cell (sys.path + cwd + DLL directories) so the imports
    # resolve and PROJ/GDAL load regardless of how the kernel was launched.
    nb.cells.insert(0, nbformat.v4.new_code_cell(_SETUP_SRC))

    # SAFETY (fails in milliseconds, not after a 3-hour transient + full disk):
    # the kept cells MUST contain the warm-up run and MUST NOT contain the
    # transient run.  The transient is `sim.run_simulation()`; the warm-up is
    # `sim_ss.run_simulation()` -- a different token -- so this is unambiguous.
    kept = "\n".join("".join(c.source) for c in nb.cells if c.cell_type == "code")
    if "sim.run_simulation()" in kept:
        raise RuntimeError(
            "SS-only trim FAILED: the transient run ('sim.run_simulation()') is "
            "still present in the kept cells. Aborting before the 312-period solve. "
            "Check TRANSIENT_MARKER against the notebook layout.")
    if "sim_ss.run_simulation" not in kept:
        raise RuntimeError(
            "SS-only trim looks wrong: the warm-up run ('sim_ss.run_simulation') "
            "was not found in the kept cells.")

    nbformat.write(nb, TRIMMED_NB)
    print(f"[forward_run] SS-only: keeping {cut} cells (skip transient from cell {cut}); "
          f"warm-up present, transient excluded.", flush=True)
    return TRIMMED_NB


def _write_full_notebook():
    """Full notebook (warm-up + transient) with the env-setup cell prepended, so
    the kernel finds the env DLLs even without a full conda activation."""
    import nbformat
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nb.cells.insert(0, nbformat.v4.new_code_cell(_SETUP_SRC))
    out = os.path.join(HERE, "_transient_run.ipynb")
    nbformat.write(nb, out)
    print("[forward_run] full transient: prepended env-setup cell.", flush=True)
    return out


def _clear_ss_outputs():
    """Force a fresh warm-up: delete old SS heads so the notebook rebuilds them.

    The notebook reuses {nameModel_SS}.hds if it exists -- but during calibration
    the parameters change every run, so a stale warm-up must NOT be reused.
    """
    sys.path.insert(0, FLOPYSIM_DIR)
    os.environ["GLB_PEST_PARAMS"] = PARAM_FILE
    from config import nameModel_SS, MODEL_BASE_DIR
    ss_hds = os.path.join(MODEL_BASE_DIR, nameModel_SS, f"{nameModel_SS}.hds")
    if os.path.exists(ss_hds):
        os.remove(ss_hds)
        print(f"[forward_run] removed stale warm-up heads: {ss_hds}", flush=True)


def run_model():
    env = os.environ.copy()
    env["GLB_PEST_PARAMS"] = PARAM_FILE          # <-- config.py picks this up

    if SS_ONLY:
        _clear_ss_outputs()
        target_nb = _write_ss_only_notebook()
    else:
        target_nb = _write_full_notebook()

    # Register the kernel, then write the conda env's ACTIVATION variables straight
    # into its kernel.json "env" block.  ipykernel's --env flag is not reliably
    # honored (the kernel still came up un-activated, PROJ_LIB=None), but jupyter
    # ALWAYS merges kernel.json "env" into the kernel's environment -- so this is
    # what finally makes PROJ load: CONDA_PREFIX (triggers the env python's own
    # DLL-dir init) + Library\bin on PATH + PROJ/GDAL data dirs.
    subprocess.run(
        [sys.executable, "-m", "ipykernel", "install", "--user",
         "--name", KERNEL_NAME, "--display-name", "GLB calibration"],
        env=env)

    _envroot = os.path.dirname(sys.executable)
    _lib = os.path.join(_envroot, "Library")
    _kdirs = [_envroot, os.path.join(_lib, "bin"),
              os.path.join(_lib, "mingw-w64", "bin"),
              os.path.join(_lib, "usr", "bin"),
              os.path.join(_envroot, "Scripts"),
              os.path.join(_envroot, "DLLs")]
    _kenv = {
        "CONDA_PREFIX": _envroot,
        "PROJ_LIB":  os.path.join(_lib, "share", "proj"),
        "PROJ_DATA": os.path.join(_lib, "share", "proj"),
        "GDAL_DATA": os.path.join(_lib, "share", "gdal"),
        "PATH": os.pathsep.join(_kdirs) + os.pathsep + os.environ.get("PATH", ""),
    }
    try:
        from jupyter_client.kernelspec import KernelSpecManager
        _kjson = os.path.join(KernelSpecManager().get_kernel_spec(KERNEL_NAME).resource_dir,
                              "kernel.json")
        with open(_kjson) as _f:
            _spec = json.load(_f)
        _spec["env"] = _kenv
        with open(_kjson, "w") as _f:
            json.dump(_spec, _f, indent=1)
        print(f"[forward_run] patched kernel env -> {_kjson}", flush=True)
    except Exception as _e:
        print(f"[forward_run] WARNING: could not patch kernel.json ({_e})", flush=True)

    # console diagnostic: confirm the env the kernel will use actually has the DLLs
    import glob as _glob
    _lb = os.path.join(_lib, "bin")
    print(f"[forward_run] kernel env root: {_envroot}", flush=True)
    print(f"[forward_run]   Library\\bin exists: {os.path.isdir(_lb)} | "
          f"proj dll: {[os.path.basename(p) for p in _glob.glob(os.path.join(_lb, 'proj*.dll'))][:3]}",
          flush=True)

    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook", "--execute",
        f"--ExecutePreprocessor.timeout={RUN_TIMEOUT_S}",
        f"--ExecutePreprocessor.kernel_name={KERNEL_NAME}",
        "--output", EXECUTED_NB,
        target_nb,
    ]
    mode = "warm-up equilibrium (SS-only)" if SS_ONLY else "full transient"
    print(f"[forward_run] launching MODFLOW [{mode}] ...", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=FLOPYSIM_DIR, env=env)   # cwd so `from config import *` resolves
    if res.returncode != 0:
        raise RuntimeError(f"Simulation notebook failed (exit {res.returncode})")
    print(f"[forward_run] solve finished in {(time.time()-t0)/60:.1f} min", flush=True)


def extract_sim_heads():
    """Simulated head at each target cell; HDRY -> water-table fallback."""
    import numpy as np
    import pandas as pd
    import flopy.utils.binaryfile as bf

    os.chdir(FLOPYSIM_DIR)
    sys.path.insert(0, FLOPYSIM_DIR)
    os.environ["GLB_PEST_PARAMS"] = PARAM_FILE
    from config import nameModel, nameModel_SS, MODEL_BASE_DIR

    if SS_ONLY:
        sim_ws   = os.path.join(MODEL_BASE_DIR, nameModel_SS)
        hds_path = os.path.join(sim_ws, f"{nameModel_SS}.hds")
    else:
        sim_ws   = os.path.join(MODEL_BASE_DIR, nameModel)
        hds_path = os.path.join(sim_ws, f"{nameModel}.hds")

    obs = pd.read_csv(OBS_FILE)
    k = obs["layer"].to_numpy(np.int64)
    i = obs["row"].to_numpy(np.int64)
    j = obs["col"].to_numpy(np.int64)
    n = len(obs)

    print(f"[forward_run] reading heads: {hds_path}", flush=True)
    hds = bf.HeadFile(hds_path)

    HDRY = 1e20
    ssum = np.zeros(n, dtype=np.float64)         # sum of valid assigned-layer heads
    scnt = np.zeros(n, dtype=np.int64)
    wt_sum = np.zeros(n, dtype=np.float64)       # water-table fallback
    wt_cnt = np.zeros(n, dtype=np.int64)

    if SS_ONLY:
        # single equilibrium snapshot = last timestep
        times = [hds.get_times()[-1]]
    else:
        # temporal mean over all stress periods (matches output Cell 12)
        times = hds.get_times()

    for t in times:
        h = hds.get_data(totim=t)                # (nlay, nrow, ncol)
        nlay = h.shape[0]

        v = h[k, i, j]
        good = np.abs(v) < HDRY
        ssum[good] += v[good]
        scnt[good] += 1

        # water table this period = shallowest valid layer at each obs column
        wt = np.full(n, np.nan, dtype=np.float64)
        remaining = np.ones(n, dtype=bool)
        for kk in range(nlay):
            vv = h[kk, i, j]
            ok = remaining & (np.abs(vv) < HDRY)
            wt[ok] = vv[ok]
            remaining &= ~ok
            if not remaining.any():
                break
        wgood = ~np.isnan(wt)
        wt_sum[wgood] += wt[wgood]
        wt_cnt[wgood] += 1

    sim = np.full(n, np.nan, dtype=np.float64)
    has = scnt > 0
    sim[has] = ssum[has] / scnt[has]
    miss = ~has & (wt_cnt > 0)
    sim[miss] = wt_sum[miss] / wt_cnt[miss]
    still = np.isnan(sim)
    if still.any():
        sim[still] = obs["obs_head_m"].to_numpy()[still]   # neutral -> zero residual
        print(f"[forward_run] WARNING: {int(still.sum())} dry targets set to observed "
              f"value (zero residual).", flush=True)

    with open(SIM_OUT, "w") as f:
        for name, val in zip(obs["obsname"], sim):
            f.write(f"{name}  {val:.6f}\n")
    print(f"[forward_run] wrote {n} simulated heads -> {SIM_OUT}", flush=True)


if __name__ == "__main__":
    run_model()
    extract_sim_heads()
