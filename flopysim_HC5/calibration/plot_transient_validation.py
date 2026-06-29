"""
plot_transient_validation.py  --  Per-layer observed-vs-simulated figure for the
TRANSIENT validation run.

After forward_run.py is run with SS_ONLY=False, it writes sim_heads.dat = the
temporal-mean simulated head at each of the ~5000 observation wells (the same
statistic used for Testing_3).  This script pairs that with obs_wells.csv and
draws the overall + per-layer 1:1 scatter with n / bias / RMSE / MAE -- the
validation result, directly comparable to the Testing_3 figure.

Reads only sim_heads.dat + obs_wells.csv (no geopandas/pyproj), so it runs in any
python with numpy/pandas/matplotlib.

Saves transient_validation.png + .svg to <MODEL_BASE_DIR>\\Figures\\<nameModel>
(or a directory passed as the first argument).
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    sys.path.insert(0, os.path.dirname(HERE))
    from config import MODEL_BASE_DIR, nameModel
    _default_out = os.path.join(MODEL_BASE_DIR, "Figures", nameModel)
except Exception as e:
    print(f"[warn] could not import config ({e}); saving to script folder")
    _default_out = HERE
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else _default_out
os.makedirs(OUT_DIR, exist_ok=True)

# ---- load obs + simulated ----
obs = pd.read_csv(os.path.join(HERE, "obs_wells.csv"))
obs["obsname"] = obs["obsname"].astype(str)
sim = pd.read_csv(os.path.join(HERE, "sim_heads.dat"), sep=r"\s+",
                  header=None, names=["obsname", "sim_head_m"])
sim["obsname"] = sim["obsname"].astype(str)
df = obs.merge(sim, on="obsname")
df["resid"] = df["sim_head_m"] - df["obs_head_m"]
df["L"] = df["layer"].astype(int) + 1            # 1-based layer label
layers = sorted(df["L"].unique())
print(f"validation wells: {len(df):,}")


def stats(d):
    o = d["obs_head_m"].to_numpy(float)
    s = d["sim_head_m"].to_numpy(float)
    r = s - o
    return dict(n=len(o), bias=float(r.mean()), mae=float(np.mean(np.abs(r))),
                rmse=float(np.sqrt(np.mean(r ** 2))))


# ---- print table ----
print(f"\n{'group':8s} {'n':>7s} {'bias':>7s} {'MAE':>6s} {'RMSE':>6s}")
m_all = stats(df)
print(f"{'ALL':8s} {m_all['n']:7d} {m_all['bias']:+7.2f} {m_all['mae']:6.2f} {m_all['rmse']:6.2f}")
per = {}
for L in layers:
    per[L] = stats(df[df.L == L])
    print(f"Layer {L:<2d} {per[L]['n']:7d} {per[L]['bias']:+7.2f} {per[L]['mae']:6.2f} {per[L]['rmse']:6.2f}")

# ---- plot: ALL + per-layer 1:1 ----
lo = float(min(df.obs_head_m.min(), df.sim_head_m.min()))
hi = float(max(df.obs_head_m.max(), df.sim_head_m.max()))
pad = 0.03 * (hi - lo); lo -= pad; hi += pad
LCOL = {1: "#378ADD", 2: "#1D9E75", 3: "#BA7517", 4: "#D4537E", 5: "#7F77DD"}

panels = [("ALL layers", df, "#444441")] + [(f"Layer {L}", df[df.L == L], LCOL.get(L, "#444441"))
                                            for L in layers]
ncols = 3
nrows = -(-len(panels) // ncols)
fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.8 * nrows), dpi=140)
axes = np.atleast_1d(axes).ravel()
for ax, (title, d, col) in zip(axes, panels):
    m = stats(d)
    ax.scatter(d.obs_head_m, d.sim_head_m, s=5, alpha=0.25, c=col, edgecolors="none")
    ax.plot([lo, hi], [lo, hi], "k--", lw=1.0)
    ax.set(xlim=(lo, hi), ylim=(lo, hi), title=title,
           xlabel="observed head (m)", ylabel="simulated head (m)")
    ax.set_aspect("equal")
    ax.text(0.04, 0.96, f"n = {m['n']:,}\nbias = {m['bias']:+.2f} m\n"
            f"RMSE = {m['rmse']:.2f} m\nMAE = {m['mae']:.2f} m",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="white", ec="#888780", alpha=0.85))
    ax.grid(alpha=0.25)
for ax in axes[len(panels):]:
    ax.axis("off")
fig.suptitle(f"Transient validation -- observed vs simulated head  ('{nameModel}')"
             if "nameModel" in dir() else "Transient validation -- observed vs simulated head",
             fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.97])
png = os.path.join(OUT_DIR, "transient_validation.png")
svg = os.path.join(OUT_DIR, "transient_validation.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nwrote {png}")
print(f"wrote {svg}")
