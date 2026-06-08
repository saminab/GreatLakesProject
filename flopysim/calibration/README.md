# PEST++ calibration of the Great Lakes MODFLOW 6 model

Automated inverse calibration of five parameters against static water-level
observations from the well database. Built with **pyEMU + PEST++**.

## What gets calibrated

| config.py knob        | PEST name  | start | bounds       | transform |
|-----------------------|-----------|-------|--------------|-----------|
| `RCH_MULT`            | rch_mult  | 0.45  | 0.20 – 0.90  | log       |
| `KV_ANISOTROPY_RATIO` | kv_aniso  | 10.0  | 1 – 100      | log       |
| `GHB_COND_MULT`       | ghb_mult  | 0.5   | 0.05 – 5     | log       |
| `DRN_COND_MULT`       | drn_mult  | 1.0   | 0.1 – 10     | log       |
| `DRN_DEPTH_M`         | drn_depth | 2.0   | 0.5 – 10 m   | linear    |

**Targets:** observed groundwater head (`land_elev - SWL`) at each well,
mapped to its `(layer, row, col)` exactly as in Cell 12 of
`Modeflow6_OutputProcess.ipynb`. Capped at ~5000 wells (stratified by layer).

**Simulated equivalent:** by default (`SS_ONLY=True` in `forward_run.py`) the
warm-up **equilibrium** head — see "Fast mode" below. Static water levels are
undated, so the long-term equilibrium is the right thing to match.

## Fast mode (SS_ONLY) — why it is ~2× cheaper

A full notebook run = warm-up spin-up (~300 periods) **+** transient (312
periods). The warm-up's final heads already represent the long-term
equilibrium, which is exactly what undated static water levels record and what
the temporal-mean comparison approximates. So during calibration
`forward_run.py` runs **only the cells before the transient build** (cell 58),
reads `{nameModel_SS}.hds`, and **skips the 312-period transient (cell 59)** —
the single most expensive cell.

- `SS_ONLY = True`  → calibrate on warm-up equilibrium (fast). **Default.**
- `SS_ONLY = False` → full transient, temporal-mean head (use to **validate**
  the final calibrated parameter set).

> **Caveat to weigh:** the warm-up solver in the notebook uses `complexity=SIMPLE`
> with `outer/inner_dvclose = 5.0 m` — loose enough that solver slop is
> comparable to the calibration RMSE. For a cleaner objective, tighten the
> warm-up `ModflowIms` tolerances (e.g. `dvclose ≈ 0.5 m`) in Cell 56 of
> `Modeflow6_SImulation.ipynb` before calibrating. It costs more warm-up
> iterations but removes noise from the fit.

## Observation weighting

`build_pest.py` sets `WEIGHT_MODE = "layer_balanced"`: each model layer
contributes equally to the objective, so the deep bedrock (Layer 5 — fewest
wells, worst fit in Testing_3) is not drowned out by the shallow layers. Switch
to `"uniform"` to weight every well equally (objective ≈ total RMSE).

## How it fits together

```
pest_params.dat.tpl  --(PEST writes)-->  pest_params.dat  --(config reads via GLB_PEST_PARAMS)
                                                                        |
run_forward.bat -> forward_run.py:  run sim notebook -> extract heads --+--> sim_heads.dat
                                                                        |
sim_heads.dat.ins  --(PEST reads)-->  residuals vs obs_wells.csv  -->  objective (phi)
```

`config.py` only honors the override when the `GLB_PEST_PARAMS` env var is set,
so **your normal notebook runs are unaffected**.

## Order of operations (run from the `calibration/` folder)

**Step 0 — one-time prep (already done):** `config.py` has
`nameModel = "Calibration_1"`, so calibration won't overwrite `Testing_3`.
Run the simulation notebook once for `Calibration_1` so the model grid exists
on disk (`make_obs.py` reads the grid from it).

```bat
:: 1. fetch the PEST++ executables (once)
env_python.bat get_pestpp.py

:: 2. build the fixed observation targets  (slow; run once)
env_python.bat make_obs.py

:: 3. assemble calib.pst  (noptmax=0 so it only validates)
env_python.bat build_pest.py

:: 4. TEST a single forward run end-to-end
pestpp-glm.exe calib.pst
::    -> confirms sim_heads.dat is produced and calib.rei looks sane

:: 5. launch the real calibration
::    set pst.control_data.noptmax = 10 in build_pest.py, re-run step 3, then:
pestpp-glm.exe calib.pst

:: 6. VALIDATE: copy calibrated values from calib.par into config.py,
::    set SS_ONLY = False in forward_run.py, and run the FULL transient once
::    (the normal notebook) to confirm the fit on the 312-period model.
```

**Why pestpp-glm (not -ies) for this problem:** with only 5 parameters, GLM's
finite-difference Jacobian is just **5 runs per iteration** (+ base + a few
lambda tests) and it converges in a handful of iterations — fewer total runs
than an ensemble method, which pays off when each model run is expensive. IES
wins only when there are *hundreds* of parameters. The real speed-up here is
**SS-only forward runs** (see "Fast mode" above), not the engine.

**Cost:** each SS-only forward run is the warm-up solve (~300 periods, SIMPLE
solver). Roughly 6 runs/iteration × a few iterations. If you have spare
machines, GLM parallelises: `pestpp-glm calib.pst /h :4004` (master) +
`pestpp-glm calib.pst /h HOST:4004` (workers) — but each worker needs its own
copy of the model directory.

## Outputs

| file              | meaning                                            |
|-------------------|----------------------------------------------------|
| `calib.par`       | best-fit parameter values                          |
| `calib.rei`       | residuals (obs vs sim) at the final iteration      |
| `calib.iobj`      | objective function (phi) per iteration             |
| `calib.ipar`      | parameter values per iteration                     |

Copy the calibrated values from `calib.par` back into `config.py` for
production runs.

## Switching engine

`pestpp-ies` (iterative ensemble smoother) can be cheaper for expensive models —
it works with an ensemble instead of a finite-difference Jacobian. The same
`calib.pst` works; just run `pestpp-ies.exe calib.pst` after adding the relevant
`++ies_*` options to `pestpp_options` in `build_pest.py`.
