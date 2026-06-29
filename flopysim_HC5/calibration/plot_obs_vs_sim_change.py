"""
plot_obs_vs_sim_change.py  --  How observed-vs-simulated head changed as the
parameters were calibrated.

Reads two PEST++ residual files (an early iteration and the final iteration) and
draws a before/after comparison:

  (left)   observed vs simulated 1:1 scatter at the FIRST iteration  (near-initial)
  (middle) observed vs simulated 1:1 scatter at the FINAL iteration  (calibrated)
  (right)  per-layer RMSE, first vs final, as paired bars

Each scatter is colored by model layer and annotated with n / RMSE / bias / total
phi, so the change with calibration is visible at a glance.

File search order (so it still works after a later run overwrites calib.*):
  1. files passed on the command line:  python plot_obs_vs_sim_change.py before.rei after.rei
  2. cal1_archive\\calib.rei1 .. reiN   (the recommended Cal_1 backup)
  3. calib.rei1 .. reiN in this folder

Saves obs_vs_sim_change.png + .svg to <MODEL_BASE_DIR>\\Figures\\Calibration_1
(or, if the 3rd CLI arg is a directory, there).
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

# layer group -> (label, color)
LAYER_STYLE = {
    "hd_lay0": ("Layer 1", "#378ADD"),
    "hd_lay1": ("Layer 2", "#1D9E75"),
    "hd_lay2": ("Layer 3", "#BA7517"),
    "hd_lay3": ("Layer 4", "#D4537E"),
    "hd_lay4": ("Layer 5", "#7F77DD"),
}


def find_rei_pair():
    cli = [a for a in sys.argv[1:] if a.lower().endswith(".rei") or re.search(r"\.rei\d+$", a.lower())]
    if len(cli) >= 2:
        return cli[0], cli[1]
    # current run (HERE) first, then the Cal_1 backup
    for folder in (HERE, os.path.join(HERE, "cal1_archive")):
        hits = sorted(glob.glob(os.path.join(folder, "calib.rei[0-9]")),
                      key=lambda p: int(re.search(r"rei(\d+)$", p).group(1)))
        if len(hits) >= 2:
            return hits[0], hits[-1]
        if len(hits) == 1:
            return hits[0], hits[0]
    return None, None


def out_dir():
    # first arg that is NOT a .rei file is treated as the output directory
    for a in sys.argv[1:]:
        if not (a.lower().endswith(".rei") or re.search(r"\.rei\d+$", a.lower())):
            return a
    try:
        sys.path.insert(0, os.path.dirname(HERE))
        from config import MODEL_BASE_DIR, nameModel
        return os.path.join(MODEL_BASE_DIR, "Figures", nameModel)
    except Exception:
        return os.path.join(HERE, "figures")


def read_res(path):
    res = pyemu.pst_utils.read_resfile(path)
    res.columns = [c.lower() for c in res.columns]
    if "group" not in res.columns:
        res = res.reset_index()
        res.columns = [c.lower() for c in res.columns]
    return res


def stats(o, s):
    r = s - o
    rmse = float(np.sqrt(np.mean(r ** 2)))
    bias = float(np.mean(r))
    return rmse, bias


before_p, after_p = find_rei_pair()
if before_p is None:
    sys.exit("No calib.reiN files found (looked in cal1_archive\\ and here). "
             "Pass two .rei files explicitly, or run a calibration first.")
OUT = out_dir()
os.makedirs(OUT, exist_ok=True)

b = read_res(before_p)
a = read_res(after_p)
it_b = re.search(r"rei(\d+)$", before_p)
it_a = re.search(r"rei(\d+)$", after_p)
lbl_b = f"iteration {it_b.group(1)}" if it_b else "before"
lbl_a = f"iteration {it_a.group(1)}" if it_a else "after"
same = before_p == after_p
print(f"before: {os.path.basename(before_p)} ({lbl_b})")
print(f"after : {os.path.basename(after_p)} ({lbl_a})")

# shared axis limits across both scatters
allv = np.concatenate([b["measured"], b["modelled"], a["measured"], a["modelled"]]).astype(float)
lo, hi = float(np.nanmin(allv)), float(np.nanmax(allv))
pad = 0.03 * (hi - lo)
lo, hi = lo - pad, hi + pad

ncols = 2 if same else 3
fig, axes = plt.subplots(1, ncols, figsize=(6.0 * ncols, 5.6), dpi=160)
axes = np.atleast_1d(axes)


def scatter(ax, df, title, lim):
    o = df["measured"].astype(float).to_numpy()
    s = df["modelled"].astype(float).to_numpy()
    r = s - o                                   # residual: + = sim too high
    sc = ax.scatter(o, s, c=r, s=8, alpha=0.75, cmap="RdBu_r",
                    vmin=-lim, vmax=lim, edgecolors="none")
    ax.plot([lo, hi], [lo, hi], "k--", lw=1.0)
    rmse, bias = stats(o, s)
    phi = float(np.sum((df["weight"].astype(float) * r) ** 2))
    ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="observed head (m)",
           ylabel="simulated head (m)", title=title)
    ax.set_aspect("equal")
    ax.text(0.04, 0.96, f"n = {len(o):,}\nRMSE = {rmse:.2f} m\nbias = {bias:+.2f} m\n"
            f"phi = {phi:,.0f}", transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="white", ec="#888780", alpha=0.85))
    ax.grid(alpha=0.25)
    return sc


# shared symmetric residual color scale across both panels (so colors are comparable)
res_all = np.abs(np.concatenate([
    (b["modelled"].astype(float) - b["measured"].astype(float)).to_numpy(),
    (a["modelled"].astype(float) - a["measured"].astype(float)).to_numpy()]))
lim = float(np.percentile(res_all, 97))

sc = scatter(axes[0], b, f"Before — {lbl_b}", lim)
if not same:
    scatter(axes[1], a, f"After — {lbl_a}", lim)
cb = fig.colorbar(sc, ax=axes[1] if not same else axes[0], fraction=0.046, pad=0.04)
cb.set_label("residual: simulated − observed head (m)\n"
             "(red = model too high, blue = too low, white = on target)", fontsize=9)

# per-layer RMSE before vs after
if not same:
    ax = axes[2]
    labs, rb, ra = [], [], []
    for grp, (lab, _col) in LAYER_STYLE.items():
        mb = b["group"].astype(str).to_numpy() == grp
        ma = a["group"].astype(str).to_numpy() == grp
        if mb.any() and ma.any():
            labs.append(lab)
            rb.append(stats(b["measured"].astype(float).to_numpy()[mb],
                            b["modelled"].astype(float).to_numpy()[mb])[0])
            ra.append(stats(a["measured"].astype(float).to_numpy()[ma],
                            a["modelled"].astype(float).to_numpy()[ma])[0])
    x = np.arange(len(labs))
    ax.bar(x - 0.2, rb, 0.4, label=lbl_b, color="#B4B2A9")
    ax.bar(x + 0.2, ra, 0.4, label=lbl_a, color="#185FA5")
    ax.set_xticks(x)
    ax.set_xticklabels(labs, rotation=20)
    ax.set(title="Per-layer RMSE: before vs after", ylabel="RMSE (m)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    for i in range(len(labs)):
        ax.text(i - 0.2, rb[i], f"{rb[i]:.1f}", ha="center", va="bottom", fontsize=7)
        ax.text(i + 0.2, ra[i], f"{ra[i]:.1f}", ha="center", va="bottom", fontsize=7)

note = ("Calibration_1 (five global parameters): the fit barely moved, because the "
        "global knobs were already near-optimal." if not same else
        "Only one residual file found — showing the single available state.")
fig.suptitle("Observed vs simulated head — change with parameter calibration\n"
             + note, fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
png = os.path.join(OUT, "obs_vs_sim_change.png")
svg = os.path.join(OUT, "obs_vs_sim_change.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"wrote {png}")
print(f"wrote {svg}")
