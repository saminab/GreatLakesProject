"""
plot_param_effects.py  --  Visualize HOW EACH PARAMETER AFFECTS THE SIMULATION.

Where plot_calib.py / plot_calib_report.py answer "how good is the fit?",
this script answers "what did each parameter DO?" -- the parameter-centric view
of a pestpp-glm run.  It reads the PEST++ iteration/sensitivity outputs and
writes one figure, param_effects.png, with up to three panels:

  (A) Composite sensitivity per parameter  (calib.isen / calib.sen)
        How strongly the weighted simulated heads respond to each parameter.
        Taller bar = the simulation is more sensitive to that knob = calibrating
        it has more effect.  THIS is "how each parameter affects the simulation."

  (B) Parameter trajectory across iterations  (calib.ipar)
        Each parameter's value at every GLM iteration, shown as a ratio to its
        starting value (log axis), so you can see which knobs the calibration
        actually moved and in which direction.

  (C) Objective-function (phi) reduction  (calib.iobj)
        Total phi and each per-layer group's phi vs iteration -- the payoff:
        how much the fit improved, and which layer drove the change.

Robust to missing files: each panel is drawn only if its source file exists,
and the script prints exactly which files it found and their newest timestamp
so you can confirm you are looking at the intended run (e.g. Cal_1, not a later
noptmax=0 validation that overwrote the same calib.* names).

Run from the calibration folder:   python plot_param_effects.py

Optionally point at a different basename (e.g. an archived copy):
    python plot_param_effects.py mycopy        # reads mycopy.isen / .ipar / .iobj
"""
import os
import sys
import glob
import datetime as _dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else "calib"


def _path(ext):
    """Newest file matching <base>.<ext> (handles calib.isen, calib.1.isen, ...)."""
    hits = sorted(glob.glob(os.path.join(HERE, f"{BASE}*.{ext}")),
                  key=os.path.getmtime)
    return hits[-1] if hits else None


def _stamp(p):
    return _dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")


def _read_csv(p):
    """PEST++ .iobj/.ipar/.isen are CSV with a leading 'iteration' column."""
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Locate the source files and report exactly what we are about to plot
# ---------------------------------------------------------------------------
sen_p  = _path("isen") or _path("sen")
ipar_p = _path("ipar")
iobj_p = _path("iobj")

print(f"Parameter-effect sources (base = '{BASE}'):")
for label, p in [("sensitivity", sen_p), ("parameter trajectory", ipar_p),
                 ("phi history", iobj_p)]:
    if p:
        print(f"  {label:22s}: {os.path.basename(p):20s}  (written {_stamp(p)})")
    else:
        print(f"  {label:22s}: --- not found ---")

if not any([sen_p, ipar_p, iobj_p]):
    sys.exit(f"\nNo {BASE}.isen/.sen/.ipar/.iobj files in {HERE}. "
             f"Run a pestpp-glm calibration first, or pass an archived basename.")

# Decide how many panels we can draw
panels = [bool(sen_p), bool(ipar_p), bool(iobj_p)]
n_panels = sum(panels)
fig, axes = plt.subplots(1, n_panels, figsize=(6.2 * n_panels, 5.4), dpi=130)
axes = np.atleast_1d(axes).ravel()
ax_i = 0

# Tab10 colors keyed by parameter name, shared across panels
_color = {}
def color(name):
    if name not in _color:
        _color[name] = plt.cm.tab10(len(_color) % 10)
    return _color[name]


# ---------------------------------------------------------------------------
# (A) Composite sensitivity per parameter  -- the headline "effect" panel
# ---------------------------------------------------------------------------
if sen_p:
    sen = _read_csv(sen_p)
    par_cols = [c for c in sen.columns
                if c not in ("iteration", "phi", "model_runs_completed")]
    last = sen.iloc[-1]                       # final-iteration sensitivities
    vals = {c: float(last[c]) for c in par_cols}
    order = sorted(vals, key=lambda k: vals[k], reverse=True)
    ax = axes[ax_i]; ax_i += 1
    ax.bar(range(len(order)), [vals[k] for k in order],
           color=[color(k) for k in order])
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=35, ha="right")
    ax.set(title="(A) Effect of each parameter\n(composite sensitivity, final iteration)",
           ylabel="composite sensitivity  (higher = bigger effect on heads)")
    ax.grid(alpha=0.3, axis="y")
    for i, k in enumerate(order):
        ax.text(i, vals[k], f"{vals[k]:.2g}", ha="center", va="bottom", fontsize=8)
    print("\nFinal composite sensitivity (most to least influential):")
    for k in order:
        print(f"  {k:14s} {vals[k]:.4g}")


# ---------------------------------------------------------------------------
# (B) Parameter trajectory (ratio to starting value, log axis)
# ---------------------------------------------------------------------------
if ipar_p:
    ipar = _read_csv(ipar_p)
    it = ipar["iteration"] if "iteration" in ipar.columns else np.arange(len(ipar))
    par_cols = [c for c in ipar.columns if c != "iteration"]
    ax = axes[ax_i]; ax_i += 1
    for c in par_cols:
        v = ipar[c].to_numpy(float)
        v0 = v[0] if v[0] != 0 else 1.0
        ax.plot(it, v / v0, "o-", color=color(c), label=c, lw=1.8, ms=4)
    ax.axhline(1.0, color="k", lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.set(title="(B) How calibration moved each parameter",
           xlabel="GLM iteration", ylabel="value / starting value  (log)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which="both")
    if len(ipar) > 1:
        print("\nParameter change (start -> final):")
        for c in par_cols:
            v = ipar[c].to_numpy(float)
            print(f"  {c:14s} {v[0]:.4g} -> {v[-1]:.4g}  "
                  f"(x{v[-1]/v[0]:.2f})" if v[0] else f"  {c}: {v[0]} -> {v[-1]}")
    else:
        print("\n[note] only one row in .ipar -- this looks like a noptmax=0 run, "
              "so there is no trajectory to show (parameters never moved).")


# ---------------------------------------------------------------------------
# (C) Phi reduction (total + per group)
# ---------------------------------------------------------------------------
if iobj_p:
    iobj = _read_csv(iobj_p)
    it = iobj["iteration"] if "iteration" in iobj.columns else np.arange(len(iobj))
    ax = axes[ax_i]; ax_i += 1
    tot = "total_phi" if "total_phi" in iobj.columns else (
          "measurement_phi" if "measurement_phi" in iobj.columns else None)
    grp_cols = [c for c in iobj.columns
                if c.startswith("hd_lay") or c.startswith("hd_") or "lay" in c]
    for g in grp_cols:
        ax.plot(it, iobj[g], "o-", lw=1.4, ms=3, label=g)
    if tot:
        ax.plot(it, iobj[tot], "k-s", lw=2.4, ms=5, label="TOTAL phi")
    ax.set(title="(C) Objective function (phi) reduction",
           xlabel="GLM iteration", ylabel="phi  (lower = better fit)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    if tot and len(iobj) > 1:
        p0, p1 = float(iobj[tot].iloc[0]), float(iobj[tot].iloc[-1])
        print(f"\nTotal phi: {p0:,.0f} -> {p1:,.0f}  "
              f"({100*(p1-p0)/p0:+.1f}%)")


fig.suptitle(f"How each parameter affects the simulation  --  '{BASE}' run", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.96])
out = os.path.join(HERE, "param_effects.png")
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"\nwrote {out}")
