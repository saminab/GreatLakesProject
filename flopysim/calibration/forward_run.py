"""
forward_run.py  --  One PEST++ forward run (model command).

PEST++ calls this once per trial parameter set.  Steps:

  1. Tell config.py to read the trial parameters that PEST++ just wrote into
     calibration/pest_params.dat  (via the GLB_PEST_PARAMS env var).
  2. Run the MODFLOW 6 build + solve by executing Modeflow6_SImulation.ipynb
     headless (nbconvert).  The notebook does `from config import *`, so it
     automatically uses the overridden calibration knobs.
  3. Read the head file and compute the temporal-mean simulated head at each
     observation cell -- streaming one stress period at a time so RAM stays low.
  4. Write calibration/sim_heads.dat  (one "obsname value" line per target),
     which the PEST instruction file (.ins) reads back.

PEST++ runs this from the calibration/ folder.  All paths are resolved
relative to this file, so the working directory does not matter.
"""
import os
import sys
import time
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FLOPYSIM_DIR = os.path.dirname(HERE)

PARAM_FILE = os.path.join(HERE, "pest_params.dat")
OBS_FILE   = os.path.join(HERE, "obs_wells.csv")
SIM_OUT    = os.path.join(HERE, "sim_heads.dat")
NOTEBOOK   = os.path.join(FLOPYSIM_DIR, "Modeflow6_SImulation.ipynb")

# Where nbconvert drops the executed copy (kept for debugging each run).
EXECUTED_NB = os.path.join(HERE, "Modeflow6_SImulation_lastrun.ipynb")

# 24-hour ceiling per forward run (a full 312-period solve can take hours).
RUN_TIMEOUT_S = 86400


def run_model():
    """Execute the simulation notebook with the trial parameters active."""
    env = os.environ.copy()
    env["GLB_PEST_PARAMS"] = PARAM_FILE          # <-- config.py picks this up

    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook", "--execute",
        f"--ExecutePreprocessor.timeout={RUN_TIMEOUT_S}",
        "--ExecutePreprocessor.kernel_name=python3",
        "--output", EXECUTED_NB,
        NOTEBOOK,
    ]
    print("[forward_run] launching MODFLOW build+solve ...", flush=True)
    t0 = time.time()
    # cwd = flopysim dir so the notebook's `from config import *` resolves.
    res = subprocess.run(cmd, cwd=FLOPYSIM_DIR, env=env)
    if res.returncode != 0:
        raise RuntimeError(f"Simulation notebook failed (exit {res.returncode})")
    print(f"[forward_run] solve finished in {(time.time()-t0)/60:.1f} min", flush=True)


def extract_sim_heads():
    """Temporal-mean simulated head at each target cell, streamed period-by-period."""
    import numpy as np
    import pandas as pd
    import flopy.utils.binaryfile as bf

    # config gives us sim_ws + nameModel for the head file location.
    os.chdir(FLOPYSIM_DIR)
    sys.path.insert(0, FLOPYSIM_DIR)
    os.environ["GLB_PEST_PARAMS"] = PARAM_FILE
    from config import nameModel, MODEL_BASE_DIR
    sim_ws = os.path.join(MODEL_BASE_DIR, nameModel)

    obs = pd.read_csv(OBS_FILE)
    k = obs["layer"].to_numpy(np.int64)
    i = obs["row"].to_numpy(np.int64)
    j = obs["col"].to_numpy(np.int64)
    n = len(obs)

    hds_path = os.path.join(sim_ws, f"{nameModel}.hds")
    print(f"[forward_run] reading heads: {hds_path}", flush=True)
    hds   = bf.HeadFile(hds_path)
    times = hds.get_times()

    HDRY = 1e20
    ssum = np.zeros(n, dtype=np.float64)        # sum of valid assigned-layer heads
    scnt = np.zeros(n, dtype=np.int64)          # count of valid periods
    wt_sum = np.zeros(n, dtype=np.float64)      # sum of water-table heads (fallback)
    wt_cnt = np.zeros(n, dtype=np.int64)

    for t in times:
        h = hds.get_data(totim=t)               # (nlay, nrow, ncol) for this period
        nlay = h.shape[0]

        # assigned-layer head
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

    # mean at assigned layer; fall back to water-table mean; else obs (no info)
    sim = np.full(n, np.nan, dtype=np.float64)
    has = scnt > 0
    sim[has] = ssum[has] / scnt[has]
    miss = ~has & (wt_cnt > 0)
    sim[miss] = wt_sum[miss] / wt_cnt[miss]
    still_missing = np.isnan(sim)
    if still_missing.any():
        # neutral fallback: observed value -> zero residual (no information)
        sim[still_missing] = obs["obs_head_m"].to_numpy()[still_missing]
        print(f"[forward_run] WARNING: {int(still_missing.sum())} dry targets "
              f"set to observed value (zero residual).", flush=True)

    with open(SIM_OUT, "w") as f:
        for name, val in zip(obs["obsname"], sim):
            f.write(f"{name}  {val:.6f}\n")
    print(f"[forward_run] wrote {n} simulated heads -> {SIM_OUT}", flush=True)


if __name__ == "__main__":
    run_model()
    extract_sim_heads()
