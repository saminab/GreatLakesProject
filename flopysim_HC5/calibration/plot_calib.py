"""
plot_calib.py  --  Visualize a PEST++ GLM calibration result.

Prefers the CALIBRATED residuals in calib.rei (the best/final solution PEST++
found). Falls back to sim_heads.dat (the most recent forward run) if no .rei
file is present yet.

Writes into this folder:
    calibfit_scatter.png      per-layer observed-vs-simulated 1:1 scatter
    calibfit_residuals.png    residual histogram + residual map on the grid
    calib_convergence.png     phi per iteration + parameter trajectory (if logs exist)

Prints per-layer n / bias / RMSE / MAE and the start->final parameter table.

Run from the calibration folder:   python plot_calib.py
"""
import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
obs = pd.read_csv(os.path.join(HERE, "obs_wells.csv"))
obs["obsname"] = obs["obsname"].astype(str)


# ---------------------------------------------------------------------------
# 1. Load the calibrated residuals (calib.rei) -- else fall back to sim_heads.dat
# ---------------------------------------------------------------------------
def _find(*names):
    for n in names:
        hits = sorted(glob.glob(os.path.join(HERE, n)))
        if hits:
            return hits[-1]          # highest-numbered / latest
    return None


rei = _find("calib.rei", "calib.*.rei")
if rei:
    import pyemu
    res = pyemu.pst_utils.read_resfile(rei).reset_index()
    res = res.rename(columns={"index": "obsname", "name": "obsname"})
    res["obsname"] = res["obsname"].astype(str)
    df = obs.merge(res[["obsname", "measured", "modelled"]], on="obsname")
    df["sim_head_m"] = df["modelled"].astype(float)
    df["obs_head_m"] = df["measured"].astype(float)
    source = f"calibrated solution ({os.path.basename(rei)})"
else:
    sim = pd.read_csv(os.path.join(HERE, "sim_heads.dat"), sep=r"\s+",
                      header=None, names=["obsname", "sim_head_m"])
    sim["obsname"] = sim["obsname"].astype(str)
    df = obs.merge(sim, on="obsname")
    source = "last forward run (sim_heads.dat)"

df["residual_m"] = df["sim_head_m"] - df["obs_head_m"]
print(f"Visualizing: {source}   ({len(df)} wells)")


def stats(d):
    r = d["residual_m"].to_numpy(float)
    return len(r), float(np.mean(r)), float(np.sqrt(np.mean(r ** 2))), float(np.mean(np.abs(r)))


n_all, bias_all, rmse_all, mae_all = stats(df)
print(f"ALL      n={n_all:5d}  bias={bias_all:+7.2f}  RMSE={rmse_all:6.2f}  MAE={mae_all:6.2f}")
for lay, g in df.groupby("layer"):
    nl, bl, rl, ml = stats(g)
    print(f"Layer {int(lay)+1}  n={nl:5d}  bias={bl:+7.2f}  RMSE={rl:6.2f}  MAE={ml:6.2f}")


# ---------------------------------------------------------------------------
# 2. Per-layer 1:1 scatter
# ---------------------------------------------------------------------------
layers = sorted(df["layer"].unique())
ncols, nrows = 3, -(-len(layers) // 3)
fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4.6 * nrows), dpi=130)
axes = np.atleast_1d(axes).ravel()
lo = float(min(df.obs_head_m.min(), df.sim_head_m.min()))
hi = float(max(df.obs_head_m.max(), df.sim_head_m.max()))
for ax, lay in zip(axes, layers):
    g = df[df.layer == lay]
    nl, bl, rl, _ = stats(g)
    ax.scatter(g.obs_head_m, g.sim_head_m, s=6, alpha=0.35)
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set(title=f"Layer {int(lay)+1}", xlabel="Observed head (m)", ylabel="Simulated head (m)")
    ax.grid(alpha=0.3)
    ax.text(0.04, 0.96, f"n = {nl}\nBias = {bl:+.2f} m\nRMSE = {rl:.2f} m",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="white", ec="black", alpha=0.8))
for ax in axes[len(layers):]:
    ax.axis("off")
fig.suptitle(f"Observed vs simulated head -- {source}\n"
             f"ALL: n={n_all:,}  bias={bias_all:+.2f} m  RMSE={rmse_all:.2f} m")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "calibfit_scatter.png"), bbox_inches="tight")
plt.close(fig)
print("wrote calibfit_scatter.png")


# ---------------------------------------------------------------------------
# 3. Residual histogram + residual map (where is the model wrong?)
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5), dpi=130)
ax1.hist(df.residual_m, bins=80)
ax1.axvline(0, color="k", lw=1)
ax1.set(xlabel="Residual  sim - obs  (m)", ylabel="Wells", title="Residual distribution")
ax1.grid(alpha=0.3)
lim = float(np.percentile(np.abs(df.residual_m), 95))
sc = ax2.scatter(df.col, -df.row, c=df.residual_m, s=8, cmap="RdBu_r", vmin=-lim, vmax=lim)
plt.colorbar(sc, ax=ax2, label="Residual (m)   red = sim too high")
ax2.set(title="Residual map (model grid)", xlabel="Column", ylabel="Row (flipped)")
ax2.set_aspect("equal")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "calibfit_residuals.png"), bbox_inches="tight")
plt.close(fig)
print("wrote calibfit_residuals.png")


# ---------------------------------------------------------------------------
# 4. Convergence + parameter movement (optional -- needs the PEST++ logs)
# ---------------------------------------------------------------------------
try:
    iobj = pd.read_csv(_find("calib.iobj"))
    phi_col = next((c for c in iobj.columns
                    if "measurement_phi" in c.lower() or c.lower() == "total_phi"),
                   iobj.columns[2])
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(13, 5), dpi=130)
    axa.plot(iobj["iteration"], iobj[phi_col], "o-")
    axa.set(xlabel="Iteration", ylabel="Phi (weighted SSE)",
            title="Objective function convergence")
    axa.grid(alpha=0.3)

    # parameter start -> final (normalized to start = 1.0)
    import pyemu
    pst = pyemu.Pst(os.path.join(HERE, "calib.pst"))
    init = pst.parameter_data.set_index("parnme")["parval1"].astype(float)
    parf = _find("calib.par", "calib.*.par")
    fin = pyemu.pst_utils.read_parfile(parf)["parval1"].astype(float)
    names = list(init.index)
    ratio = [fin[n] / init[n] for n in names]
    axb.bar(names, ratio)
    axb.axhline(1.0, color="k", lw=1)
    axb.set(ylabel="final / initial", title="Parameter change (1.0 = unchanged)")
    axb.tick_params(axis="x", rotation=30)
    for i, n in enumerate(names):
        axb.text(i, ratio[i], f"{init[n]:.3g}→{fin[n]:.3g}", ha="center",
                 va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "calib_convergence.png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote calib_convergence.png")
    print("\nstart -> final parameters:")
    for n in names:
        print(f"  {n:24s} {init[n]:.4g}  ->  {fin[n]:.4g}")
except Exception as e:
    print(f"(skipped convergence plot: {e})")
