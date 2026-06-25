"""
plot_param_table.py  --  Presentation table of the calibration parameters:
the value we chose, its bounds/transform, what it controls, and WHY that prior.

Companion to plot_model_schematic.py (which shows WHERE each parameter acts).
This answers "what values did you use and why."  Content is documentation of the
Calibration_1 parameter set (the five global knobs); the footer notes how
Calibration_2 reparameterizes K per layer.

Saves param_table.png + .svg to <MODEL_BASE_DIR>\\Figures\\Calibration_1
(or a directory passed on the command line).
"""
import os
import sys
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) > 1:
    OUT_DIR = sys.argv[1]
else:
    try:
        sys.path.insert(0, os.path.dirname(HERE))
        from config import MODEL_BASE_DIR
        OUT_DIR = os.path.join(MODEL_BASE_DIR, "Figures", "Calibration_1")
    except Exception as e:
        print(f"[param_table] could not import config ({e}); using ./figures")
        OUT_DIR = os.path.join(HERE, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# parameter | value | bounds | transform | controls | why this prior
ROWS = [
    ("RCH_MULT\n(rch_mult)", "0.45", "0.20 – 0.90", "log",
     "Net recharge — the water entering the system",
     "Dominant control on head magnitude. The raw climate/soil-water-balance "
     "recharge carries large bias, so a basin-wide multiplier corrects the "
     "overall water balance. 0.45 inherited from the Testing_3 history."),
    ("KV_ANISO_RATIO\n(kv_aniso)", "10", "1 – 100", "log",
     "Vertical : horizontal K (Kv = Kh / ratio)",
     "Sets vertical head gradients between layers. 10:1 is a typical anisotropy "
     "for layered glacial sediments; wide bounds let the data tighten it."),
    ("GHB_COND_MULT\n(ghb_mult)", "0.5", "0.05 – 5", "log",
     "Aquifer <-> Great Lake exchange",
     "Lakebed sediment conductance is poorly known. The multiplier spans the "
     "plausible range around the geometric estimate."),
    ("DRN_COND_MULT\n(drn_mult)", "1.0", "0.1 – 10", "log",
     "Stream discharge rate (baseflow)",
     "Streambed conductance is uncertain and governs how readily groundwater "
     "discharges to streams, hence baseflow and how high the water table sits."),
    ("DRN_DEPTH_M\n(drn_depth)", "2.0 m", "0.5 – 10 m", "linear",
     "Water-table ceiling at streams",
     "At 1 km resolution the cell-mean DEM sits 1-3 m above the real channel. "
     "0.5 m pinned the water table basin-wide, so it was raised to 2 m."),
]

# column left edges and widths in 0..100 space
COLS = [
    ("parameter", 1.5, 13),
    ("value",     15, 7),
    ("bounds",    22.5, 11),
    ("transform", 34, 8),
    ("controls",  42.5, 21),
    ("why this prior", 64, 34.5),
]
HEADER = "#185FA5"
ROW_A, ROW_B = "#F4F7FB", "#FFFFFF"
TXT = "#2C2C2A"

# pre-wrap the two prose columns to compute row heights
def wrap(text, width):
    return "\n".join(textwrap.wrap(text, width))

wrapped = []
for p, v, b, t, ctrl, why in ROWS:
    cw = wrap(ctrl, 28)
    ww = wrap(why, 50)
    nlines = max(cw.count("\n"), ww.count("\n"), p.count("\n")) + 1
    wrapped.append((p, v, b, t, cw, ww, nlines))

fig, ax = plt.subplots(figsize=(15, 6.2), dpi=150)
ax.set_xlim(0, 100)
ax.axis("off")

# layout from top; accumulate y downward
y = 96
header_h = 5
ax.add_patch(Rectangle((1, y - header_h), 97.5, header_h, facecolor=HEADER, edgecolor="none"))
for name, x, w in COLS:
    ax.text(x + 0.4, y - header_h / 2, name, ha="left", va="center",
            fontsize=11, color="white", fontweight="medium")
y -= header_h

for ri, (p, v, b, t, cw, ww, nlines) in enumerate(wrapped):
    row_h = 2.0 + nlines * 2.1
    fc = ROW_A if ri % 2 == 0 else ROW_B
    ax.add_patch(Rectangle((1, y - row_h), 97.5, row_h, facecolor=fc, edgecolor="#D3D1C7", linewidth=0.6))
    cy = y - row_h / 2
    cells = [p, v, b, t, cw, ww]
    for (name, x, w), val in zip(COLS, cells):
        weight = "medium" if name in ("parameter", "value") else "normal"
        ax.text(x + 0.4, cy, val, ha="left", va="center", fontsize=9.5,
                color=TXT, fontweight=weight)
    y -= row_h

# footer note about Calibration_2
y -= 1.5
ax.text(1.5, y, "Calibration_2 reparameterizes hydraulic conductivity per layer: "
        "kh_l1..kh_l5  (init 1.0, bounds 0.1 - 10x, log)  -- one horizontal-K "
        "multiplier per geologic layer, replacing the single basin-wide K story.",
        ha="left", va="top", fontsize=9.5, color="#0F6E56", style="italic")

# pin the y-range so bbox_inches="tight" can't blow up from autoscaling
ax.set_ylim(y - 4, 98)

png = os.path.join(OUT_DIR, "param_table.png")
svg = os.path.join(OUT_DIR, "param_table.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"wrote {png}")
print(f"wrote {svg}")
