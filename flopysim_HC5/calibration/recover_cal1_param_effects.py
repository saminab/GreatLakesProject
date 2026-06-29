"""
recover_cal1_param_effects.py  --  Rebuild the Calibration_1 parameter-effect
figure from the SURVIVING per-iteration files.

Cal_1's tidy summary CSVs (calib.iobj / .ipar / .isen) were overwritten (emptied)
by a later noptmax=0 validation run that reused the same `calib.*` basename.  But
the richer per-iteration outputs from the 6/11-6/15 Cal_1 run survived:

    calib.jco                 final Jacobian  (d sim_head / d parameter)
    calib.rei1 / rei2 / rei3  residuals at iterations 1..3  (measured, modelled, weight, group)
    calib.1.par / 2.par / 3.par  parameter values at iterations 1..3

This script reads those and writes  cal1_param_effects.png  with:

  (A) Composite weighted sensitivity per parameter  (from calib.jco + weights)
        For each parameter, CSS = sqrt( mean_i (w_i * J_ij)^2 ).  Because Cal_1
        parameters are log-transformed, J is d(sim)/d(log10 par), so the bars are
        directly comparable: tallest = the knob the simulated heads respond to
        most = where calibrating has the biggest effect.
  (B) Parameter trajectory across iterations  (from calib.*.par)
        Each parameter value at iters 1..3, as a ratio to its iteration-1 value
        (log axis) -- shows which knobs the GLM actually moved.
  (C) Phi reduction, total and per layer  (recomputed from calib.rei*)
        phi_group = sum (weight * (modelled - measured))^2 -- the payoff, and
        which layer drove the change.

Needs pyemu (already in the Samin_GWM2 env).  Run from the calibration folder:
    python recover_cal1_param_effects.py
"""
import os
import sys
import glob
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyemu

HERE = os.path.dirname(os.path.abspath(__file__))
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


def _exists(name):
    p = os.path.join(HERE, name)
    return p if os.path.exists(p) and os.path.getsize(p) > 0 else None


def _read_res(path):
    """Return a DataFrame indexed by obs name with measured/modelled/weight/group."""
    res = pyemu.pst_utils.read_resfile(path)
    res.columns = [c.lower() for c in res.columns]
    if "name" not in res.columns:
        res = res.reset_index().rename(columns={res.reset_index().columns[0]: "name"})
        res.columns = [c.lower() for c in res.columns]
    return res.set_index("name")


# ---------------------------------------------------------------------------
# Discover the surviving Cal_1 files
# ---------------------------------------------------------------------------
jco_p = _exists("calib.jco") or _exists("calib.jcb")
rei_iters = sorted(glob.glob(os.path.join(HERE, "calib.rei[0-9]")),
                   key=lambda p: int(re.search(r"rei(\d+)$", p).group(1)))
par_iters = sorted(glob.glob(os.path.join(HERE, "calib.[0-9].par")),
                   key=lambda p: int(re.search(r"calib\.(\d+)\.par$", p).group(1)))
par_iters = [p for p in par_iters if os.path.getsize(p) > 0]

print("Surviving Cal_1 sources:")
print(f"  Jacobian   : {os.path.basename(jco_p) if jco_p else '--- missing ---'}")
print(f"  residuals  : {[os.path.basename(p) for p in rei_iters] or '--- missing ---'}")
print(f"  par files  : {[os.path.basename(p) for p in par_iters] or '--- missing ---'}")

# weights (and a name list) come from the last residual file
weights = None
if rei_iters:
    last_res = _read_res(rei_iters[-1])
    weights = last_res["weight"].astype(float)

panels = [bool(jco_p and weights is not None), bool(par_iters), bool(rei_iters)]
n_panels = max(1, sum(panels))
fig, axes = plt.subplots(1, n_panels, figsize=(6.4 * n_panels, 5.4), dpi=130)
axes = np.atleast_1d(axes).ravel()
ax_i = 0
_color = {}
def color(name):
    _color.setdefault(name, plt.cm.tab10(len(_color) % 10))
    return _color[name]


# ---------------------------------------------------------------------------
# (A) Composite weighted sensitivity from the Jacobian
# ---------------------------------------------------------------------------
if jco_p and weights is not None:
    jco = pyemu.Jco.from_binary(jco_p)
    J = jco.to_dataframe()                       # rows = obs, cols = parameters
    common = J.index.intersection(weights.index)
    w = weights.loc[common].to_numpy(float)
    Jc = J.loc[common]
    css = {}
    for par in Jc.columns:
        col = Jc[par].to_numpy(float)
        css[par] = float(np.sqrt(np.mean((w * col) ** 2)))
    order = sorted(css, key=lambda k: css[k], reverse=True)
    ax = axes[ax_i]; ax_i += 1
    ax.bar(range(len(order)), [css[k] for k in order], color=[color(k) for k in order])
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=35, ha="right")
    ax.set(title="(A) Effect of each parameter\n(composite weighted sensitivity, final Jacobian)",
           ylabel="CSS  (higher = bigger effect on simulated heads)")
    ax.grid(alpha=0.3, axis="y")
    for i, k in enumerate(order):
        ax.text(i, css[k], f"{css[k]:.2g}", ha="center", va="bottom", fontsize=8)
    print("\nComposite sensitivity (most to least influential):")
    for k in order:
        print(f"  {k:14s} {css[k]:.4g}")
else:
    print("\n[A] skipped -- need both calib.jco and a residual file (for weights).")


# ---------------------------------------------------------------------------
# (B) Parameter trajectory from calib.{1,2,3}.par
# ---------------------------------------------------------------------------
if par_iters:
    traj = {}
    iters = []
    for p in par_iters:
        it = int(re.search(r"calib\.(\d+)\.par$", p).group(1))
        iters.append(it)
        pf = pyemu.pst_utils.read_parfile(p)         # index = parnme, col parval1
        for parnme, row in pf.iterrows():
            traj.setdefault(parnme, {})[it] = float(row["parval1"])
    ax = axes[ax_i]; ax_i += 1
    iters = sorted(set(iters))
    for parnme, d in traj.items():
        ys = np.array([d[i] for i in iters], float)
        y0 = ys[0] if ys[0] != 0 else 1.0
        ax.plot(iters, ys / y0, "o-", color=color(parnme), label=parnme, lw=1.8, ms=5)
    ax.axhline(1.0, color="k", lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.set(title="(B) How calibration moved each parameter",
           xlabel="GLM iteration", ylabel="value / iteration-1 value  (log)")
    ax.set_xticks(iters)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which="both")
    print("\nParameter values per iteration:")
    for parnme, d in traj.items():
        print(f"  {parnme:14s} " + "  ".join(f"it{i}={d[i]:.4g}" for i in iters))
else:
    print("\n[B] skipped -- no non-empty calib.N.par files found.")


# ---------------------------------------------------------------------------
# (C) Phi reduction recomputed from the per-iteration residual files
# ---------------------------------------------------------------------------
if rei_iters:
    rows = []
    for p in rei_iters:
        it = int(re.search(r"rei(\d+)$", p).group(1))
        r = _read_res(p)
        wr2 = (r["weight"].astype(float) * (r["modelled"].astype(float)
                                            - r["measured"].astype(float))) ** 2
        by_grp = wr2.groupby(r["group"]).sum()
        rec = {"iteration": it, "TOTAL": float(wr2.sum())}
        for g, v in by_grp.items():
            rec[g] = float(v)
        rows.append(rec)
    phi = pd.DataFrame(rows).sort_values("iteration").set_index("iteration")
    ax = axes[ax_i]; ax_i += 1
    grp_cols = [c for c in phi.columns if c != "TOTAL"]
    for g in grp_cols:
        ax.plot(phi.index, phi[g], "o-", lw=1.4, ms=4, label=g)
    ax.plot(phi.index, phi["TOTAL"], "k-s", lw=2.4, ms=6, label="TOTAL phi")
    ax.set(title="(C) Objective (phi) reduction over iterations",
           xlabel="GLM iteration", ylabel="phi  (lower = better fit)")
    ax.set_xticks(phi.index)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    print("\nPhi per iteration (recomputed from residuals):")
    print(phi.to_string(float_format=lambda v: f"{v:,.0f}"))
else:
    print("\n[C] skipped -- no calib.reiN files found.")


fig.suptitle("Calibration_1 -- how each parameter affects the simulation "
             "(recovered from surviving per-iteration files)", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.95])
out = os.path.join(OUT_DIR, "cal1_param_effects.png")
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"\nwrote {out}")
