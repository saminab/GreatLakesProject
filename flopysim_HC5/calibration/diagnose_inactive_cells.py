"""
diagnose_inactive_cells.py  --  Why is the model deactivating cells INSIDE the
basin?  (Salt-and-pepper holes in the active domain.)

Re-reads the aligned input rasters and replays the simulation notebook's
layer-geometry / thickness checks, then labels every cell inside the original
basin (IBOUND) with the FIRST reason it would be deactivated:

  active (kept)              passes all checks
  missing DEM                land-surface raster has no value
  missing bedrock contact    BOTM band-1 (bedrock contact) has no value
  thin Quaternary (<3 m)     DEM - bedrock < 3 * MIN_QUAT_SUBLAYER_M
  bedrock below -595 m       bedrock - 5 m <= -MAX_DEPTH_M  (no room for deep bedrock)
  inverted layer thickness   some layer top <= its bottom after the 5-layer build

Writes inactive_cause_map.png (+ .svg) and prints a count per reason, so you can
see what is driving the holes (and therefore how to fix them -- e.g. gap-fill a
contact raster or relax a threshold).

Run from the calibration folder (Samin_GWM2 env):  python diagnose_inactive_cells.py
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))            # flopysim_HC5/
from config import MODEL_BASE_DIR, FRAC_BEDROCK_THK_M, MAX_DEPTH_M, MIN_QUAT_SUBLAYER_M
from Inputs import top_aligned, botm_aligned, mid_quat_aligned, idomain_tif
from Helper import read_band1, read_all_bands, clean_continuous

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(MODEL_BASE_DIR, "Figures", "Calibration_1")
os.makedirs(OUT_DIR, exist_ok=True)


def _clean(a, nd):
    a = np.array(clean_continuous(a, nd, fill=np.nan), dtype=float)
    a[~np.isfinite(a)] = np.nan
    a[a <= -9000] = np.nan
    return a


# ---- read inputs (same sources as the build) ----
id_raw, _ = read_band1(idomain_tif, dtype="int32")
basin = np.asarray(id_raw) > 0                       # original active basin

top2d = _clean(*read_band1(top_aligned))
botm_raw, botm_nd = read_all_bands(botm_aligned)
quat_base = _clean(botm_raw[0], botm_nd)             # BOTM band 1 = bedrock contact
mid_raw = _clean(*read_band1(mid_quat_aligned))

# ---- rebuild the 5-layer geometry exactly as the notebook does ----
valid_mq = (np.isfinite(mid_raw) & (mid_raw > quat_base + MIN_QUAT_SUBLAYER_M)
            & (mid_raw < top2d - MIN_QUAT_SUBLAYER_M))
mid_quat = np.where(valid_mq, mid_raw, (top2d + quat_base) / 2.0)
b0 = (top2d + mid_quat) / 2.0
b1 = mid_quat
b2 = quat_base
b3 = quat_base - FRAC_BEDROCK_THK_M
b4 = np.full_like(top2d, -MAX_DEPTH_M)
thicks = [top2d - b0, b0 - b1, b1 - b2, b2 - b3, b3 - b4]
bad_thk = np.zeros_like(top2d, dtype=bool)
for t in thicks:
    bad_thk |= ~np.isfinite(t) | (t <= 0)

quat_thk = top2d - quat_base
min_total_quat = MIN_QUAT_SUBLAYER_M * 3

# ---- classify each cell by FIRST failing reason (only inside the basin) ----
LABELS = ["active (kept)", "outside basin", "missing DEM", "missing bedrock contact",
          "thin Quaternary (<3 m)", "bedrock below -595 m", "inverted layer thickness"]
COLORS = ["#dfe7df", "#ffffff", "#5f5e5a", "#7F77DD", "#e24b4a", "#EF9F27", "#1D9E75"]
cause = np.zeros(top2d.shape, dtype=int)
cause[~basin] = 1
inside = basin.copy()
for code, mask in [
    (2, np.isnan(top2d)),
    (3, np.isnan(quat_base)),
    (4, quat_thk < min_total_quat),
    (5, b3 <= b4),
    (6, bad_thk),
]:
    hit = inside & np.asarray(mask) & (cause == 0)
    cause[hit] = code
    inside &= ~hit

# ---- report ----
print("Cell classification (first failing reason):")
basin_n = int(basin.sum())
for code, lab in enumerate(LABELS):
    n = int((cause == code).sum())
    if code == 1:
        print(f"  {lab:26s}: {n:,}")
    else:
        print(f"  {lab:26s}: {n:,}  ({100*n/max(1,basin_n):.1f}% of basin)")
deact = int(((cause >= 2)).sum())
print(f"\nTotal deactivated INSIDE basin: {deact:,} "
      f"({100*deact/max(1,basin_n):.1f}% of the basin)")
worst = max(range(2, 7), key=lambda c: (cause == c).sum())
print(f"Dominant cause of interior holes: '{LABELS[worst]}'")

# ---- map ----
disp = cause.astype(float)
disp[cause == 1] = np.nan                            # outside basin -> transparent
fig, ax = plt.subplots(figsize=(10, 9), dpi=160)
ax.set_facecolor("white")
cmap = ListedColormap(COLORS)
norm = BoundaryNorm(np.arange(-0.5, 7.5, 1), cmap.N)
im = ax.imshow(np.ma.masked_invalid(disp), cmap=cmap, norm=norm)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, ticks=range(7))
cb.ax.set_yticklabels(LABELS)
ax.set(title=f"Why cells are inactive — {deact:,} interior cells deactivated "
       f"({100*deact/max(1,basin_n):.1f}% of basin)",
       xlabel="column", ylabel="row")
ax.set_aspect("equal")
fig.tight_layout()
png = os.path.join(OUT_DIR, "inactive_cause_map.png")
svg = os.path.join(OUT_DIR, "inactive_cause_map.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nwrote {png}")
print(f"wrote {svg}")
