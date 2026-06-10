"""
make_obs.py  --  Build the fixed observation target set for PEST++ calibration.

Run this ONCE (it is slow: it reads the whole well GDB and intersects the grid).
It reproduces the well-processing from Cell 12 of Modeflow6_OutputProcess.ipynb,
through layer assignment, and writes a stable table of calibration targets:

    calibration/obs_wells.csv
        obsname, well_id, region, layer, row, col,
        land_elev_m, SWL_m, obs_head_m

The mapping well -> (layer,row,col) depends only on the model GRID
(top / botm / idomain), which none of the five calibration parameters change.
So this target set is computed once and reused by every PEST++ forward run.

Usage (from the calibration/ folder, via the env wrapper):
    env_python.bat make_obs.py
or directly with the climate interpreter once its DLL paths are on PATH.
"""
import os
import sys
from osgeo import gdal
gdal.PushErrorHandler("CPLQuietErrorHandler")
# Make `from config import *` resolve: the model code lives one level up.
HERE = os.path.dirname(os.path.abspath(__file__))
FLOPYSIM_DIR = os.path.dirname(HERE)
os.chdir(FLOPYSIM_DIR)
sys.path.insert(0, FLOPYSIM_DIR)

import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
import flopy

from config import (
    nameModel, MODEL_BASE_DIR, wells_gdb_path, WELL_LAYER,
    boundary_shp, FT_TO_M,
)

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
# Existing model run whose grid defines the cell mapping (any completed build).
SRC_MODEL    = "Testing_3"                      # e.g. "Testing_3"
SRC_SIM_WS   = os.path.join(MODEL_BASE_DIR, SRC_MODEL)
TARGET_CRS   = "EPSG:3174"
MAX_OBS      = 5000                            # cap; stratified by layer (None = keep all)
RANDOM_SEED  = 42
OUT_CSV      = os.path.join(HERE, "obs_wells.csv")

print(f"Building observation targets from grid of: {SRC_SIM_WS}")

# ---------------------------------------------------------------------------
# 1. LOAD MODEL GRID  (no heads needed -- mapping is geometry only)
# ---------------------------------------------------------------------------
sim = flopy.mf6.MFSimulation.load(sim_ws=SRC_SIM_WS, verbosity_level=0)
gwf = sim.get_model(SRC_MODEL)

top     = np.array(gwf.dis.top.array,     dtype=float)
botm    = np.array(gwf.dis.botm.array,    dtype=float)
idomain = np.array(gwf.dis.idomain.array, dtype=int)
nlay, nrow, ncol = idomain.shape
print(f"Grid: nlay={nlay} nrow={nrow} ncol={ncol}")

# ---------------------------------------------------------------------------
# 2. READ + CLIP WELLS  (mirrors Cell 12, sections 2-5)
# ---------------------------------------------------------------------------
print("Reading wells:", wells_gdb_path, "layer", WELL_LAYER)
all_cols = list(gpd.read_file(wells_gdb_path, layer=WELL_LAYER, rows=1,
                              engine="pyogrio").columns)
needed = [c for c in ["WELL_ID", "LAT", "LON", "SWL", "WELL_DEPTH",
                      "SCREEN_FRM", "SCREEN_TO", "AQ_TYPE", "WELL_TYPE",
                      "geometry"] if c in all_cols]

wells = gpd.read_file(wells_gdb_path, layer=WELL_LAYER, engine="pyogrio")[needed].copy()
wells = wells.to_crs(TARGET_CRS)

boundary = gpd.read_file(boundary_shp).to_crs(TARGET_CRS)

for c in ["SWL", "WELL_DEPTH", "SCREEN_FRM", "SCREEN_TO"]:
    if c in wells.columns:
        wells[c] = pd.to_numeric(wells[c], errors="coerce")

wells = wells.dropna(subset=["SWL", "geometry"]).copy()
print("After dropping missing SWL:", len(wells))

_bnd = boundary.geometry
_bnd_union = _bnd.union_all() if hasattr(_bnd, "union_all") else _bnd.unary_union
wells = wells[wells.geometry.within(_bnd_union)].copy()
print("Inside model boundary:", len(wells))

# feet -> metres, plausibility filter
wells["SWL_m"] = wells["SWL"] * FT_TO_M
if "WELL_DEPTH" in wells.columns:
    wells["WELL_DEPTH_m"] = wells["WELL_DEPTH"] * FT_TO_M
if "SCREEN_FRM" in wells.columns:
    wells["SCREEN_FRM_m"] = wells["SCREEN_FRM"] * FT_TO_M
if "SCREEN_TO" in wells.columns:
    wells["SCREEN_TO_m"] = wells["SCREEN_TO"] * FT_TO_M

wells = wells[(wells["SWL_m"] >= 0) & (wells["SWL_m"] < 150)].copy()
print("After SWL range filter [0,150) m:", len(wells))

# ---------------------------------------------------------------------------
# 3. MAP TO ROW/COL  (mirrors Cell 12, section 5)
# ---------------------------------------------------------------------------
wells["x_3174"] = wells.geometry.x
wells["y_3174"] = wells.geometry.y

rows, cols, valid = [], [], []
for x, y in zip(wells["x_3174"], wells["y_3174"]):
    try:
        r, c = gwf.modelgrid.intersect(x, y)
        if 0 <= int(r) < nrow and 0 <= int(c) < ncol:
            rows.append(int(r)); cols.append(int(c)); valid.append(True)
        else:
            rows.append(-1); cols.append(-1); valid.append(False)
    except Exception:
        rows.append(-1); cols.append(-1); valid.append(False)

wells["row"], wells["col"], wells["_in"] = rows, cols, valid
wells = wells[wells["_in"]].drop(columns="_in").copy()
print("Inside model grid:", len(wells))

wells["land_elev_m"] = top[wells["row"].astype(int), wells["col"].astype(int)]
wells["obs_head_m"]  = wells["land_elev_m"] - wells["SWL_m"]
wells = wells[(wells["obs_head_m"] > 0) & (wells["obs_head_m"] < 700)].copy()
print("After observed-head filter (0,700) m:", len(wells))

# ---------------------------------------------------------------------------
# 4. ASSIGN LAYER FROM SCREEN / WELL DEPTH  (mirrors Cell 12, section 6)
# ---------------------------------------------------------------------------
if "SCREEN_FRM_m" in wells.columns and "SCREEN_TO_m" in wells.columns:
    wells["screen_mid_m"] = (wells["SCREEN_FRM_m"] + wells["SCREEN_TO_m"]) / 2
else:
    wells["screen_mid_m"] = np.nan
if "WELL_DEPTH_m" in wells.columns:
    wells["screen_mid_m"] = wells["screen_mid_m"].fillna(wells["WELL_DEPTH_m"] / 2)
wells["screen_mid_m"] = wells["screen_mid_m"].fillna(5.0)

layers = []
for _, r in wells.iterrows():
    i_w, j_w = int(r["row"]), int(r["col"])
    screen_elev = r["land_elev_m"] - r["screen_mid_m"]
    assigned = 0
    for k in range(nlay):
        lay_top = top[i_w, j_w] if k == 0 else botm[k - 1, i_w, j_w]
        lay_bot = botm[k, i_w, j_w]
        if lay_bot <= screen_elev <= lay_top:
            assigned = k
            break
    layers.append(assigned)
wells["layer"] = layers

# ---------------------------------------------------------------------------
# 5. DROP INACTIVE CELLS  (mirrors Cell 12, section 7)
# ---------------------------------------------------------------------------
wells["_id"] = [int(idomain[int(r["layer"]), int(r["row"]), int(r["col"])])
                for _, r in wells.iterrows()]
wells = wells[wells["_id"] > 0].drop(columns="_id").copy()
print("In active cells:", len(wells))

# ---------------------------------------------------------------------------
# 6. WELL ID + (optional) STRATIFIED SUBSAMPLE
# ---------------------------------------------------------------------------
wells = wells.reset_index(drop=True)
if "WELL_ID" in wells.columns:
    wells["well_id"] = wells["WELL_ID"].astype(str)
else:
    wells["well_id"] = [f"WELL_{i:06d}" for i in range(len(wells))]

if MAX_OBS is not None and len(wells) > MAX_OBS:
    # proportional sample within each layer so all layers stay represented.
    # Iterate groups rather than groupby.apply -- on pandas >=2.2 apply drops
    # the grouping column ("layer"), which breaks the output selection below.
    frac = MAX_OBS / len(wells)
    parts = []
    for _lay, _g in wells.groupby("layer"):
        _n = max(1, int(round(len(_g) * frac)))
        parts.append(_g.sample(min(_n, len(_g)), random_state=RANDOM_SEED))
    wells = pd.concat(parts).reset_index(drop=True)
    print(f"Subsampled to {len(wells)} wells (cap {MAX_OBS}).")

# ---------------------------------------------------------------------------
# 7. WRITE TARGET TABLE
# ---------------------------------------------------------------------------
wells = wells.reset_index(drop=True)
wells["obsname"] = [f"obs_{i:06d}" for i in range(len(wells))]

out = wells[["obsname", "well_id", "layer", "row", "col",
             "land_elev_m", "SWL_m", "obs_head_m"]].copy()
out.to_csv(OUT_CSV, index=False)
print(f"\nWrote {len(out)} observation targets -> {OUT_CSV}")
print(out["layer"].value_counts().sort_index().to_string())
