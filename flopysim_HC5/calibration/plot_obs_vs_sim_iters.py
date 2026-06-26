"""
plot_obs_vs_sim_iters.py  --  Compare observed vs simulated head across the
DIFFERENT PARAMETER SETS the calibration tried (one per GLM iteration).

Each pestpp iteration is a distinct parameter choice with its own residual file
(calib.rei1, calib.rei2, ...).  This draws one observed-vs-simulated 1:1 scatter
per parameter set, colored by residual on a shared scale, annotated with RMSE and
phi (and the parameter values from the matching calib.N.par if present) -- so you
can see how the fit changes as the parameters change.

File search (so it works after a later run overwrites calib.*):
  1. iteration files passed on the command line
  2. cal1_archive\\calib.rei*    (the recommended Cal_1 backup)
  3. calib.rei* in this folder

Saves obs_vs_sim_by_params.png + .svg to <MODEL_BASE_DIR>\\Figures\\Calibration_1
(or a directory passed as the 1st argument).  Needs pyemu.
"""
import os
import sys
import re
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyemu

HERE = os.path.dirname(os.path.abspath(__file__))


def out_dir():
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            return a
    try:
        sys.path.insert(0, os.path.dirname(HERE))
        from config import MODEL_BASE_DIR
        return os.path.join(MODEL_BASE_DIR, "Figures", "Calibration_1")
    except Exception:
        return os.path.join(HERE, "figures")


def find_rei_files():
    cli = [a for a in sys.argv[1:] if a.lower().endswith(tuple(f".rei{i}" for i in range(10)))
           or a.lower().endswith(".rei")]
    if cli:
        return cli
    for folder in (os.path.join(HERE, "cal1_archive"), HERE):
        hits = sorted(glob.glob(os.path.join(folder, "calib.rei[0-9]")),
                      key=lambda p: int(re.search(r"rei(\d+)$", p).group(1)))
        if hits:
            return hits
    return []


def read_res(path):
    res = pyemu.pst_utils.read_resfile(path)
    res.columns = [c.lower() for c in res.columns]
    if "group" not in res.columns:
        res = res.reset_index()
        res.columns = [c.lower() for c in res.columns]
    return res


def read_par(path):
    """key params from calib.N.par, if present, for the panel subtitle."""
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        return None
    try:
        pf = pyemu.pst_utils.read_parfile(path)
        return {k: float(v) for k, v in pf["parval1"].items()}
    except Exception:
        return None


rei_files = find_rei_files()
if not rei_files:
    sys.exit("No calib.reiN files found (looked in cal1_archive\\ and here). "
             "Run a calibration first, or pass .rei files explicitly.")
OUT = out_dir()
os.makedirs(OUT, exist_ok=True)

# load all parameter sets
sets = []
for p in rei_files:
    m = re.search(r"rei(\d+)$", p)
    it = m.group(1) if m else "?"
    df = read_res(p)
    par = read_par(os.path.join(os.path.dirname(p), f"calib.{it}.par"))
    sets.append((it, df, par))
print(f"parameter sets: {[s[0] for s in sets]}")

# shared axes + residual scale
allv = np.concatenate([np.r_[d["measured"].astype(float), d["modelled"].astype(float)]
                       for _, d, _ in sets])
lo, hi = float(np.nanmin(allv)), float(np.nanmax(allv))
pad = 0.03 * (hi - lo); lo -= pad; hi += pad
res_all = np.abs(np.concatenate([(d["modelled"].astype(float) - d["measured"].astype(float)).to_numpy()
                                 for _, d, _ in sets]))
lim = float(np.percentile(res_all, 97))

n = len(sets)
fig, axes = plt.subplots(1, n, figsize=(5.6 * n, 5.6), dpi=150)
axes = np.atleast_1d(axes)
sc = None
for ax, (it, d, par) in zip(axes, sets):
    o = d["measured"].astype(float).to_numpy()
    s = d["modelled"].astype(float).to_numpy()
    r = s - o
    sc = ax.scatter(o, s, c=r, s=8, alpha=0.75, cmap="RdBu_r", vmin=-lim, vmax=lim,
                    edgecolors="none")
    ax.plot([lo, hi], [lo, hi], "k--", lw=1.0)
    rmse = float(np.sqrt(np.mean(r ** 2)))
    phi = float(np.sum((d["weight"].astype(float) * r) ** 2))
    ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="observed head (m)",
           ylabel="simulated head (m)", title=f"parameter set — iteration {it}")
    ax.set_aspect("equal")
    txt = f"RMSE = {rmse:.2f} m\nphi = {phi:,.0f}"
    if par:
        # show ALL parameters, two per line
        items = [f"{k}={par[k]:.3g}" for k in par]
        for i in range(0, len(items), 2):
            txt += "\n" + "   ".join(items[i:i + 2])
    ax.text(0.04, 0.96, txt, transform=ax.transAxes, va="top", fontsize=8.5,
            bbox=dict(fc="white", ec="#888780", alpha=0.85))
    ax.grid(alpha=0.25)

cb = fig.colorbar(sc, ax=axes[-1], fraction=0.046, pad=0.04)
cb.set_label("residual: simulated − observed head (m)\n(red = too high, blue = too low)",
             fontsize=9)
fig.suptitle("Observed vs simulated head across the parameter sets the calibration tried",
             fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.95])
png = os.path.join(OUT, "obs_vs_sim_by_params.png")
svg = os.path.join(OUT, "obs_vs_sim_by_params.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"wrote {png}")
print(f"wrote {svg}")
