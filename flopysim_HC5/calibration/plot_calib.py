"""
plot_calib.py  --  Visualize a PEST++ forward run: observed vs simulated heads.

Reads (from this folder):
    obs_wells.csv    observation targets written by make_obs.py
    sim_heads.dat    simulated equivalents from the latest forward run

Writes (to this folder):
    calibfit_scatter.png     1:1 observed-vs-simulated scatter, one panel per layer
    calibfit_residuals.png   residual histogram + residual map on the model grid

Prints overall and per-layer n / bias / RMSE / MAE to the console.

Run from the calibration folder:   python plot_calib.py
Works after ANY forward run (baseline or during/after calibration) -- it always
shows the fit of the most recent sim_heads.dat.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # no display needed; just write PNGs
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

obs = pd.read_csv(os.path.join(HERE, "obs_wells.csv"))
sim = pd.read_csv(os.path.join(HERE, "sim_heads.dat"), sep=r"\s+",
                  header=None, names=["obsname", "sim_head_m"])
df = obs.merge(sim, on="obsname", how="inner")
df["residual_m"] = df["sim_head_m"] - df["obs_head_m"]


def stats(d):
    r = d["residual_m"].to_numpy(float)
    return len(r), float(np.mean(r)), float(np.sqrt(np.mean(r ** 2))), float(np.mean(np.abs(r)))


n_all, bias_all, rmse_all, mae_all = stats(df)
print(f"ALL      n={n_all:5d}  bias={bias_all:+7.2f} m  RMSE={rmse_all:6.2f} m  MAE={mae_all:6.2f} m")
for lay, g in df.groupby("layer"):
    nl, bl, rl, ml = stats(g)
    print(f"Layer {int(lay)+1}  n={nl:5d}  bias={bl:+7.2f} m  RMSE={rl:6.2f} m  MAE={ml:6.2f} m")

# ---------------------------------------------------------------------------
# Figure 1: 1:1 scatter per layer
# ---------------------------------------------------------------------------
layers = sorted(df["layer"].unique())
ncols = 3
nrows = -(-len(layers) // ncols)
fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4.6 * nrows), dpi=130)
axes = np.atleast_1d(axes).ravel()
lo = float(min(df.obs_head_m.min(), df.sim_head_m.min()))
hi = float(max(df.obs_head_m.max(), df.sim_head_m.max()))

for ax, lay in zip(axes, layers):
    g = df[df.layer == lay]
    nl, bl, rl, _ = stats(g)
    ax.scatter(g.obs_head_m, g.sim_head_m, s=6, alpha=0.35)
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set_title(f"Layer {int(lay)+1}")
    ax.set_xlabel("Observed head (m)")
    ax.set_ylabel("Simulated head (m)")
    ax.grid(alpha=0.3)
    ax.text(0.04, 0.96, f"n = {nl}\nBias = {bl:+.2f} m\nRMSE = {rl:.2f} m",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="white", ec="black", alpha=0.8))
for ax in axes[len(layers):]:
    ax.axis("off")

fig.suptitle(f"Observed vs simulated head -- warm-up equilibrium   "
             f"(ALL: n={n_all:,}, bias={bias_all:+.2f} m, RMSE={rmse_all:.2f} m)")
fig.tight_layout()
out1 = os.path.join(HERE, "calibfit_scatter.png")
fig.savefig(out1, bbox_inches="tight")
plt.close(fig)
print("wrote", out1)

# ---------------------------------------------------------------------------
# Figure 2: residual histogram + residual map on the model grid
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5), dpi=130)

ax1.hist(df.residual_m, bins=80)
ax1.axvline(0, color="k", lw=1)
ax1.set_xlabel("Residual  sim - obs  (m)")
ax1.set_ylabel("Number of wells")
ax1.set_title("Residual distribution")
ax1.grid(alpha=0.3)

# residual map: model column/row as pseudo-coordinates (row axis flipped so
# north is up); red = simulated too HIGH, blue = simulated too LOW
lim = float(np.percentile(np.abs(df.residual_m), 95))
sc = ax2.scatter(df.col, -df.row, c=df.residual_m, s=8,
                 cmap="RdBu_r", vmin=-lim, vmax=lim)
plt.colorbar(sc, ax=ax2, label="Residual (m)   red = sim too high")
ax2.set_title("Residual map (model grid)")
ax2.set_xlabel("Column")
ax2.set_ylabel("Row (flipped)")
ax2.set_aspect("equal")

fig.tight_layout()
out2 = os.path.join(HERE, "calibfit_residuals.png")
fig.savefig(out2, bbox_inches="tight")
plt.close(fig)
print("wrote", out2)
