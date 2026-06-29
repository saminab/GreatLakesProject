"""
plot_calib_report.py  --  Publication-quality visualization of a PEST++ result.

Reads the CALIBRATED residuals (calib.rei; falls back to sim_heads.dat) and
obs_wells.csv, then writes a richer figure set than plot_calib.py:

    report_1to1_density.png    hexbin (density) 1:1 plots: overall + per layer,
                               each with n / bias / RMSE / R^2 / NSE
    report_residual_maps.png   per-layer residual maps (+ combined), shared
                               diverging color scale -- reveals WHERE each layer
                               is biased (the per-layer split is the key view)
    report_diagnostics.png     residual boxplot by layer, residual-vs-observed
                               trend, per-layer bias/RMSE bars, and a normal Q-Q

Also prints a metrics table (overall + per layer):
    n, bias, MAE, RMSE, R^2, NSE, scaled-RMSE (% of observed range).

Run from the calibration folder:   python plot_calib_report.py
1 km cells are assumed for the map axes (delr = delc = 1000 m in this model).
"""
import os
import sys
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CELL_KM = 1.0   # delr = delc = 1000 m
# figures -> MODEL_BASE_DIR/Figures/<nameModel>  (or a directory passed as arg 1)
try:
    sys.path.insert(0, os.path.dirname(HERE))
    from config import MODEL_BASE_DIR, nameModel
    OUT_DIR = os.path.join(MODEL_BASE_DIR, "Figures", nameModel)
except Exception:
    OUT_DIR = HERE
if len(sys.argv) > 1:
    OUT_DIR = sys.argv[1]
os.makedirs(OUT_DIR, exist_ok=True)


def _find(*names):
    for n in names:
        hits = sorted(glob.glob(os.path.join(HERE, n)))
        if hits:
            return hits[-1]
    return None


# ---------------------------------------------------------------------------
# Load observed + simulated (calibrated)
# ---------------------------------------------------------------------------
obs = pd.read_csv(os.path.join(HERE, "obs_wells.csv"))
obs["obsname"] = obs["obsname"].astype(str)

rei = _find("calib.rei", "calib.*.rei")
if rei:
    import pyemu
    res = pyemu.pst_utils.read_resfile(rei)
    res.columns = [c.lower() for c in res.columns]
    if "name" not in res.columns:
        res = res.reset_index()
        res.columns = [c.lower() for c in res.columns]
        res = res.rename(columns={res.columns[0]: "name"})
    res = res.rename(columns={"name": "obsname"})
    res["obsname"] = res["obsname"].astype(str)
    df = obs.merge(res[["obsname", "measured", "modelled"]], on="obsname")
    df["obs_head_m"] = df["measured"].astype(float)
    df["sim_head_m"] = df["modelled"].astype(float)
    source = f"calibrated solution ({os.path.basename(rei)})"
else:
    sim = pd.read_csv(os.path.join(HERE, "sim_heads.dat"), sep=r"\s+",
                      header=None, names=["obsname", "sim_head_m"])
    sim["obsname"] = sim["obsname"].astype(str)
    df = obs.merge(sim, on="obsname")
    source = "last forward run (sim_heads.dat)"

df["residual_m"] = df["sim_head_m"] - df["obs_head_m"]
df["layer1"] = df["layer"].astype(int) + 1     # 1-based for labels
layers = sorted(df["layer1"].unique())
print(f"Visualizing: {source}   ({len(df):,} wells)")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def metrics(d):
    o = d["obs_head_m"].to_numpy(float)
    s = d["sim_head_m"].to_numpy(float)
    r = s - o
    rmse = float(np.sqrt(np.mean(r ** 2)))
    r2 = float(np.corrcoef(o, s)[0, 1] ** 2) if len(o) > 2 else np.nan
    nse = float(1 - np.sum(r ** 2) / np.sum((o - o.mean()) ** 2))
    rng = float(o.max() - o.min())
    return dict(n=len(o), bias=float(r.mean()), mae=float(np.mean(np.abs(r))),
                rmse=rmse, r2=r2, nse=nse, srmse=100 * rmse / rng if rng else np.nan)


print(f"\n{'group':8s} {'n':>5s} {'bias':>7s} {'MAE':>6s} {'RMSE':>6s} "
      f"{'R2':>6s} {'NSE':>6s} {'sRMSE%':>7s}")
m_all = metrics(df)
print(f"{'ALL':8s} {m_all['n']:5d} {m_all['bias']:+7.2f} {m_all['mae']:6.2f} "
      f"{m_all['rmse']:6.2f} {m_all['r2']:6.3f} {m_all['nse']:6.3f} {m_all['srmse']:7.2f}")
per_layer = {}
for L in layers:
    mL = metrics(df[df.layer1 == L])
    per_layer[L] = mL
    print(f"Layer {L:<2d} {mL['n']:5d} {mL['bias']:+7.2f} {mL['mae']:6.2f} "
          f"{mL['rmse']:6.2f} {mL['r2']:6.3f} {mL['nse']:6.3f} {mL['srmse']:7.2f}")


# ---------------------------------------------------------------------------
# FIGURE 1: hexbin density 1:1 -- overall + per layer
# ---------------------------------------------------------------------------
lo = float(min(df.obs_head_m.min(), df.sim_head_m.min()))
hi = float(max(df.obs_head_m.max(), df.sim_head_m.max()))
panels = [("ALL", df, m_all)] + [(f"Layer {L}", df[df.layer1 == L], per_layer[L]) for L in layers]
ncols = 3
nrows = -(-len(panels) // ncols)
fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.8 * nrows), dpi=130)
axes = np.atleast_1d(axes).ravel()
for ax, (title, d, m) in zip(axes, panels):
    hb = ax.hexbin(d.obs_head_m, d.sim_head_m, gridsize=40, cmap="viridis",
                   mincnt=1, extent=(lo, hi, lo, hi))
    ax.plot([lo, hi], [lo, hi], "r--", lw=1.2)
    ax.set(title=title, xlabel="Observed head (m)", ylabel="Simulated head (m)",
           xlim=(lo, hi), ylim=(lo, hi))
    ax.set_aspect("equal")
    fig.colorbar(hb, ax=ax, label="wells / bin", shrink=0.8)
    ax.text(0.04, 0.96,
            f"n = {m['n']:,}\nBias = {m['bias']:+.2f} m\nRMSE = {m['rmse']:.2f} m\n"
            f"R² = {m['r2']:.3f}\nNSE = {m['nse']:.3f}",
            transform=ax.transAxes, va="top", fontsize=8.5,
            bbox=dict(fc="white", ec="black", alpha=0.85))
for ax in axes[len(panels):]:
    ax.axis("off")
fig.suptitle(f"Observed vs simulated head (density) -- {source}", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "report_1to1_density.png"), bbox_inches="tight")
plt.close(fig)
print("\nwrote report_1to1_density.png")


# ---------------------------------------------------------------------------
# FIGURE 2: per-layer residual maps (shared diverging scale)
# ---------------------------------------------------------------------------
lim = float(np.percentile(np.abs(df.residual_m), 97))
x_km = df["col"] * CELL_KM
y_km = -df["row"] * CELL_KM
map_panels = [("ALL layers", df)] + [(f"Layer {L}", df[df.layer1 == L]) for L in layers]
fig, axes = plt.subplots(nrows, ncols, figsize=(5.4 * ncols, 5.0 * nrows), dpi=130)
axes = np.atleast_1d(axes).ravel()
sc = None
for ax, (title, d) in zip(axes, map_panels):
    sc = ax.scatter(d["col"] * CELL_KM, -d["row"] * CELL_KM, c=d["residual_m"],
                    s=7, cmap="RdBu_r", vmin=-lim, vmax=lim)
    mb = d["residual_m"].mean()
    ax.set(title=f"{title}  (mean {mb:+.1f} m)", xlabel="grid E (km)",
           ylabel="grid N (km)")
    ax.set_aspect("equal")
for ax in axes[len(map_panels):]:
    ax.axis("off")
cbar = fig.colorbar(sc, ax=axes.tolist(), shrink=0.6, label="Residual sim - obs (m)   red = too high")
fig.suptitle(f"Residual maps by layer -- {source}", fontsize=13)
fig.savefig(os.path.join(OUT_DIR, "report_residual_maps.png"), bbox_inches="tight")
plt.close(fig)
print("wrote report_residual_maps.png")


# ---------------------------------------------------------------------------
# FIGURE 3: diagnostics (boxplot / residual-vs-obs / bias-RMSE bars / Q-Q)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(2, 2, figsize=(14, 11), dpi=130)

# (a) residual boxplot by layer
box_data = [df[df.layer1 == L]["residual_m"].to_numpy(float) for L in layers]
ax[0, 0].boxplot(box_data, showfliers=False)        # positions default 1..N
ax[0, 0].set_xticklabels([f"L{L}" for L in layers])  # avoids labels/tick_labels API churn
ax[0, 0].axhline(0, color="r", lw=1)
ax[0, 0].set(title="Residual distribution by layer", ylabel="Residual sim - obs (m)")
ax[0, 0].grid(alpha=0.3, axis="y")

# (b) residual vs observed head + binned-mean trend
ax[0, 1].scatter(df.obs_head_m, df.residual_m, s=5, alpha=0.15)
ax[0, 1].axhline(0, color="r", lw=1)
bins = np.linspace(df.obs_head_m.min(), df.obs_head_m.max(), 20)
idx = np.digitize(df.obs_head_m, bins)
bx = [df.obs_head_m[idx == k].mean() for k in range(1, len(bins))]
by = [df.residual_m[idx == k].mean() for k in range(1, len(bins))]
ax[0, 1].plot(bx, by, "k-o", lw=2, ms=4, label="binned mean")
ax[0, 1].legend()
ax[0, 1].set(title="Residual vs observed head", xlabel="Observed head (m)",
             ylabel="Residual (m)")
ax[0, 1].grid(alpha=0.3)

# (c) per-layer RMSE bars with bias markers
Ls = list(layers)
rmses = [per_layer[L]["rmse"] for L in Ls]
biases = [per_layer[L]["bias"] for L in Ls]
xpos = np.arange(len(Ls))
ax[1, 0].bar(xpos, rmses, color="steelblue", label="RMSE")
ax[1, 0].plot(xpos, biases, "D-", color="darkorange", label="Bias")
ax[1, 0].axhline(0, color="k", lw=0.8)
ax[1, 0].set_xticks(xpos)
ax[1, 0].set_xticklabels([f"Layer {L}" for L in Ls])
ax[1, 0].set(title="Per-layer RMSE and bias", ylabel="m")
ax[1, 0].legend()
ax[1, 0].grid(alpha=0.3, axis="y")
for i, L in enumerate(Ls):
    ax[1, 0].text(i, rmses[i] + 0.2, f"{rmses[i]:.1f}", ha="center", fontsize=8)

# (d) normal Q-Q of residuals
try:
    from scipy import stats
    stats.probplot(df.residual_m.to_numpy(float), dist="norm", plot=ax[1, 1])
    ax[1, 1].set_title("Normal Q-Q plot of residuals")
except Exception:
    r = np.sort(df.residual_m.to_numpy(float))
    ax[1, 1].plot(np.linspace(0, 100, len(r)), r)
    ax[1, 1].set(title="Residual CDF", xlabel="percentile", ylabel="residual (m)")
ax[1, 1].grid(alpha=0.3)

fig.suptitle(f"Calibration diagnostics -- {source}", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "report_diagnostics.png"), bbox_inches="tight")
plt.close(fig)
print("wrote report_diagnostics.png")
print("\nDone. Three report_*.png files written to the calibration folder.")
