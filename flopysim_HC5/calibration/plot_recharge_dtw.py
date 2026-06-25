"""
plot_recharge_dtw.py  --  Map mean annual recharge and depth-to-water-table from
the current model run.

Reads the warm-up (steady-state) model directory that calibration writes
(<MODEL_BASE_DIR>\\<nameModel_SS>) and produces two side-by-side maps:

  (left)  mean annual recharge   [mm/yr]   -- the recharge actually used by the
          run (fixed spatial pattern x RCH_MULT), averaged over its stress periods
  (right) depth to water table   [m]       -- land surface (DIS top) minus the
          simulated water table (shallowest active layer head per cell)

This is a SINGLE model state (the most recent run), because PEST++ overwrites the
head file each iteration -- per-iteration maps would need the model re-run at each
saved parameter set.

Saves recharge_dtw_maps.png + .svg to <MODEL_BASE_DIR>\\Figures\\Calibration_1
(or a directory passed as the 1st argument).  Optionally pass a model workspace
as the 2nd argument to map a different run:
    python plot_recharge_dtw.py  <out_dir>  <model_ws>

Needs flopy (Samin_GWM2 env on HC5).
"""
import os
import sys
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import flopy
import flopy.utils.binaryfile as bf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))            # flopysim_HC5/ for config
from config import MODEL_BASE_DIR, nameModel_SS, RCH_MULT

# ---------------------------------------------------------------------------
# args
# ---------------------------------------------------------------------------
args = sys.argv[1:]
OUT_DIR = args[0] if len(args) >= 1 else os.path.join(MODEL_BASE_DIR, "Figures", "Calibration_1")
SIM_WS = args[1] if len(args) >= 2 else os.path.join(MODEL_BASE_DIR, nameModel_SS)
os.makedirs(OUT_DIR, exist_ok=True)
print(f"model workspace : {SIM_WS}")
print(f"output dir      : {OUT_DIR}")

# ---------------------------------------------------------------------------
# load grid + heads
# ---------------------------------------------------------------------------
# load ONLY the DIS package (we just need top + idomain) -- loading the full
# simulation parses every package incl. the huge DRN/GHB cell lists, which can
# take many minutes for a model this size.
sim = flopy.mf6.MFSimulation.load(sim_ws=SIM_WS, verbosity_level=0,
                                  load_only=["dis"])
gwf = sim.get_model(sim.model_names[0])

top = np.array(gwf.dis.top.array, dtype=float)               # (nrow, ncol)
idomain = np.array(gwf.dis.idomain.array)
if idomain.ndim == 2:                                        # broadcast if 2D
    idomain = np.repeat(idomain[None, :, :], gwf.dis.nlay.array, axis=0)
nlay, nrow, ncol = idomain.shape

# read the head file directly (same approach as forward_run.py)
hds_files = sorted(glob.glob(os.path.join(SIM_WS, "*.hds")), key=os.path.getmtime)
if not hds_files:
    sys.exit(f"No .hds head file in {SIM_WS} -- has the model run?")
hf = bf.HeadFile(hds_files[-1])
head = hf.get_data(totim=hf.get_times()[-1])                 # (nlay, nrow, ncol), final
print(f"head file       : {os.path.basename(hds_files[-1])}")
HDRY = 1e20

# water table = shallowest active layer with a valid head
wt = np.full((nrow, ncol), np.nan)
for k in range(nlay):
    fill = (idomain[k] > 0) & (np.abs(head[k]) < HDRY) & np.isnan(wt)
    wt[fill] = head[k][fill]

land = idomain.max(axis=0) > 0          # cell column active in at least one layer
dtw = top - wt
dtw[~land] = np.nan

# classify the blank cells: truly inactive vs active-but-dry (no saturated layer)
inactive = ~land
dry_active = land & np.isnan(wt)        # active, but every layer dry -> no water table
print(f"cells: active {int(land.sum()):,} | inactive {int(inactive.sum()):,} | "
      f"active-but-DRY (no water table) {int(dry_active.sum()):,} "
      f"({100 * dry_active.sum() / max(1, land.sum()):.1f}% of active)")

# ---------------------------------------------------------------------------
# mean annual recharge from the saved rch_cache (already includes RCH_MULT)
# ---------------------------------------------------------------------------
cache = os.path.join(MODEL_BASE_DIR, "rch_cache")
cand = sorted(glob.glob(os.path.join(cache, f"rch_spd_RCH{RCH_MULT:.2f}*.npz")),
              key=os.path.getmtime)
if not cand:
    cand = sorted(glob.glob(os.path.join(cache, "rch_spd_RCH*.npz")), key=os.path.getmtime)
if not cand:
    cand = sorted(glob.glob(os.path.join(cache, "*.npz")), key=os.path.getmtime)
if not cand:
    sys.exit(f"No recharge npz found in {cache} -- cannot map recharge.")
rz = np.load(cand[-1])
periods = np.stack([np.asarray(rz[k], dtype=float) for k in rz.files], axis=0)
rch_mday = np.nanmean(periods, axis=0)                       # m/day, (nrow, ncol)
rch_mmyr = rch_mday * 365.25 * 1000.0                        # -> mm/yr
rch_mmyr[~land] = np.nan
print(f"recharge source : {os.path.basename(cand[-1])}  ({periods.shape[0]} periods)")

# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------
def summ(a, unit):
    v = a[np.isfinite(a)]
    print(f"  {unit:12s} min {np.nanpercentile(v,2):8.2f}  median {np.nanmedian(v):8.2f}  "
          f"max {np.nanpercentile(v,98):8.2f}")
print("Map summaries (2-98 percentile):")
summ(rch_mmyr, "recharge")
summ(dtw, "DTW (m)")

# ---------------------------------------------------------------------------
# plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), dpi=160)

r_lo, r_hi = np.nanpercentile(rch_mmyr, [2, 98])
im0 = axes[0].imshow(np.ma.masked_invalid(rch_mmyr), cmap="YlGnBu",
                     vmin=max(0, r_lo), vmax=r_hi)
axes[0].set_title("Mean annual recharge")
cb0 = fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)
cb0.set_label("recharge (mm/yr)")

d_lo, d_hi = np.nanpercentile(dtw, [2, 98])
im1 = axes[1].imshow(np.ma.masked_invalid(dtw), cmap="viridis_r",
                     vmin=max(0, d_lo), vmax=d_hi)
# overlay active-but-dry cells in red so they are not confused with inactive ones
axes[1].imshow(np.ma.masked_where(~dry_active, np.ones_like(dtw)),
               cmap=ListedColormap(["#e24b4a"]), vmin=0, vmax=1)
axes[1].set_title(f"Depth to water table  "
                  f"(red = active but dry: {int(dry_active.sum()):,} cells)")
cb1 = fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
cb1.set_label("depth to water table (m)   (deeper = darker)")

# gray background so genuinely inactive cells read as 'outside domain', not missing
for ax in axes:
    ax.set_facecolor("0.82")
    ax.set_xlabel("column"); ax.set_ylabel("row")
    ax.set_aspect("equal")

fig.suptitle(f"Recharge and depth-to-water-table — run '{os.path.basename(SIM_WS)}' "
             f"(RCH_MULT = {RCH_MULT})", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.95])
png = os.path.join(OUT_DIR, "recharge_dtw_maps.png")
svg = os.path.join(OUT_DIR, "recharge_dtw_maps.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"wrote {png}")
print(f"wrote {svg}")
