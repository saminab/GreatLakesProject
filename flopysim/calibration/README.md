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

**Simulated equivalent:** temporal-mean head over all stress periods at the
target cell — the same statistic Cell 12 uses for RMSE/Bias.

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

## One-time setup

> Recommended: set `nameModel = "Calib"` in `config.py` first, so calibration
> runs don't overwrite your `Testing_3` outputs. Run the sim notebook once for
> `Calib` so the grid exists before `make_obs.py`.

Run each from the `calibration/` folder:

```bat
env_python.bat get_pestpp.py     :: download pestpp-glm.exe etc.
env_python.bat make_obs.py       :: build obs_wells.csv (slow, run once)
env_python.bat build_pest.py     :: write calib.pst (+ .tpl/.ins)
```

## Test one forward run (noptmax = 0)

`build_pest.py` writes `calib.pst` with `noptmax = 0` — PEST++ runs the model
once and verifies the .pst is internally consistent.

```bat
pestpp-glm.exe calib.pst
```

Check that `sim_heads.dat` is produced and `calib.rei` shows sensible residuals.

## Run the real calibration

Edit `PARAMS`/options in `build_pest.py`, set `pst.control_data.noptmax = 10`,
re-run `build_pest.py` (or edit `calib.pst` directly), then:

```bat
pestpp-glm.exe calib.pst
```

**Cost warning:** each forward run = a full 312-period MF6 solve (hours).
pestpp-glm needs ~6 runs per iteration (base + one per parameter for the
finite-difference Jacobian) plus a few lambda tests. Budget accordingly. If you
have spare machines, pestpp-glm supports parallel workers
(`pestpp-glm calib.pst /h :4004` master + `/h host:4004` workers), but each
worker needs its own model directory and ~19 GB of head output.

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
