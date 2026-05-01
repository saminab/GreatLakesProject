"""
Conceptual cross-section figure — Great Lakes MODFLOW 6 model
Shows the 8-layer geological structure for both land and lake cells,
with boundary conditions, drain placement, and HK zones.
Run from the flopysim directory or anywhere; saves PNG to fig_dir.
"""

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — works without a display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import os

# ── Output path ──────────────────────────────────────────────────────────────
FIG_DIR = r"D:\Users\abolmaal\modelling\Figs\Testing_7"
os.makedirs(FIG_DIR, exist_ok=True)
OUT_FIG = os.path.join(FIG_DIR, "conceptual_model_layers.png")

# ─────────────────────────────────────────────────────────────────────────────
# LAYER DEFINITIONS  (visual height is schematic — not to scale)
# true_thick: label shown on figure (actual model thickness)
# vis_h     : visual rectangle height in data-units (schematic)
# ─────────────────────────────────────────────────────────────────────────────
#  name               color          true_thick (land)  true_thick (lake)   vis_h
LAYERS = [
    ("Layer 1\nSoil 1",          "#c8a46e",  "0.25 m",      "Water column\n(variable, ~5–400 m)", 1.2),
    ("Layer 2\nSoil 2",          "#b8945e",  "0.25 m",      "0.25 m (below lake floor)",          0.8),
    ("Layer 3\nSoil 3",          "#a8845e",  "0.50 m",      "0.50 m",                             0.8),
    ("Layer 4\nQuaternary 1",    "#e8d09a",  "variable\n(~1/3 Quat col.)", "variable",             1.4),
    ("Layer 5\nQuaternary 2",    "#d8c08a",  "variable\n(~1/3 Quat col.)", "variable",             1.4),
    ("Layer 6\nQuaternary 3",    "#c8b07a",  "variable\n(~1/3 Quat col.)", "variable",             1.4),
    ("Layer 7\nFract. Bedrock",  "#c09070",  "5 m (fixed)", "5 m (fixed)",                        1.0),
    ("Layer 8\nDeep Bedrock",    "#808080",  "variable\n(base at 600 m)", "variable\n(base at 600 m)", 1.4),
]

HK_LABELS = [
    "K_h = surficial\n(med. 13 m/d)",
    "K_h = surficial\n(med. 13 m/d)",
    "K_h = surficial\n(med. 13 m/d)",
    "K_h = Quat-1\n(med. 13 m/d)",
    "K_h = Quat-2\n(med. 8.6×10⁻³ m/d)",
    "K_h = Quat-3\n(med. 8.6×10⁻² m/d)",
    "K_h = bedrock-frac\n(med. 8.6×10⁻² m/d)",
    "K_h = bedrock-deep\n(med. 8.6×10⁻⁶ m/d)",
]

# cumulative y positions (top of each layer, going DOWN)
y_tops = [0.0]
for _, _, _, _, vh in LAYERS:
    y_tops.append(y_tops[-1] + vh)
total_height = y_tops[-1]

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE SETUP
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15, 13))
ax.set_xlim(0, 10)
ax.set_ylim(total_height + 0.6, -1.2)   # y increases downward
ax.axis("off")

# column x positions
LAND_X0, LAND_X1   = 0.5,  3.8
LAKE_X0, LAKE_X1   = 4.2,  7.5
HK_X0,   HK_X1     = 7.7,  9.9

LAND_MID = (LAND_X0 + LAND_X1) / 2
LAKE_MID = (LAKE_X0 + LAKE_X1) / 2
HK_MID   = (HK_X0   + HK_X1)   / 2

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN HEADERS
# ─────────────────────────────────────────────────────────────────────────────
header_kw = dict(fontsize=11, fontweight="bold", ha="center", va="bottom")
ax.text(LAND_MID, -0.95, "LAND CELL", **header_kw, color="#4a2c00")
ax.text(LAKE_MID, -0.95, "LAKE CELL", **header_kw, color="#003580")
ax.text(HK_MID,   -0.95, "HK / Kv per Layer\n(Kv = Kh / 10)", fontsize=9.5,
        fontweight="bold", ha="center", va="bottom", color="#333333")

# land surface line
ax.plot([LAND_X0, LAND_X1], [-0.05, -0.05], color="saddlebrown", lw=2.5, zorder=5)
ax.text(LAND_MID, -0.5, "Land surface", ha="center", fontsize=8.5,
        style="italic", color="saddlebrown")

# lake surface (water level)
ax.add_patch(mpatches.FancyBboxPatch(
    (LAKE_X0, -0.9), LAKE_X1 - LAKE_X0, 0.85,
    boxstyle="round,pad=0.02", fc="#add8f0", ec="#5090c0", lw=1.5, zorder=3))
ax.text(LAKE_MID, -0.5, "Lake surface (GHB stage)", ha="center", fontsize=8.5,
        style="italic", color="#003580")

# ─────────────────────────────────────────────────────────────────────────────
# DRAW LAYERS
# ─────────────────────────────────────────────────────────────────────────────
for k, (name, color, land_thk, lake_thk, vis_h) in enumerate(LAYERS):
    y0 = y_tops[k]
    y1 = y_tops[k + 1]
    mid_y = (y0 + y1) / 2

    # ── land rectangle ──
    land_fc = "#add8f0" if k == 0 else color   # water blue for lake Layer 1? No, land Layer 1 is soil
    ax.add_patch(mpatches.Rectangle(
        (LAND_X0, y0), LAND_X1 - LAND_X0, vis_h,
        fc=color, ec="white", lw=0.8, zorder=2))

    # layer label inside
    ax.text(LAND_MID, mid_y, name, ha="center", va="center",
            fontsize=8, fontweight="bold", color="white",
            path_effects=[pe.withStroke(linewidth=1.5, foreground="black")])

    # thickness label (right side of land column)
    ax.text(LAND_X1 + 0.07, mid_y, land_thk,
            ha="left", va="center", fontsize=7.5, color="#333333")

    # ── lake rectangle ──
    lake_color = "#4a9fcf" if k == 0 else color   # blue water column for Layer 1 in lake
    ax.add_patch(mpatches.Rectangle(
        (LAKE_X0, y0), LAKE_X1 - LAKE_X0, vis_h,
        fc=lake_color, ec="white", lw=0.8, zorder=2))

    lake_label = "Water column" if k == 0 else name
    ax.text(LAKE_MID, mid_y, lake_label, ha="center", va="center",
            fontsize=8, fontweight="bold", color="white",
            path_effects=[pe.withStroke(linewidth=1.5, foreground="black")])

    ax.text(LAKE_X1 + 0.07, mid_y, lake_thk,
            ha="left", va="center", fontsize=7.5, color="#333333")

    # ── HK column ──
    ax.add_patch(mpatches.Rectangle(
        (HK_X0, y0), HK_X1 - HK_X0, vis_h,
        fc=color, ec="white", lw=0.8, alpha=0.55, zorder=2))
    ax.text(HK_MID, mid_y, HK_LABELS[k],
            ha="center", va="center", fontsize=7, color="#111111")

    # ── horizontal separator line ──
    for x0, x1 in [(LAND_X0, LAND_X1), (LAKE_X0, LAKE_X1), (HK_X0, HK_X1)]:
        ax.plot([x0, x1], [y1, y1], color="white", lw=0.6, zorder=4)

# outer borders
for x0, x1 in [(LAND_X0, LAND_X1), (LAKE_X0, LAKE_X1), (HK_X0, HK_X1)]:
    ax.add_patch(mpatches.Rectangle(
        (x0, 0), x1 - x0, total_height,
        fc="none", ec="#555555", lw=1.5, zorder=5))

# ─────────────────────────────────────────────────────────────────────────────
# BOUNDARY CONDITION ANNOTATIONS — land side
# ─────────────────────────────────────────────────────────────────────────────
ann_kw = dict(fontsize=8, ha="left", va="center",
              bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#888888", alpha=0.85))

# Stream/wetland drain — Layer 2 (soil 2), 0.5 m below surface
drn_y = y_tops[1] + (y_tops[2] - y_tops[1]) * 0.45
ax.annotate(
    "Stream / Wetland DRN\n(0.5 m below surface → Layer 2)",
    xy=(LAND_X0, drn_y), xytext=(-0.3, drn_y),
    ha="right", va="center", fontsize=8,
    bbox=dict(boxstyle="round,pad=0.3", fc="#fffbe6", ec="#e6a800", alpha=0.95),
    arrowprops=dict(arrowstyle="-|>", color="#e6a800", lw=1.4),
)

# Surface seepage drain — Layer 4, 5 m below surface
surf_y = y_tops[3] + (y_tops[4] - y_tops[3]) * 0.45
ax.annotate(
    "Surface seepage DRN\n(5 m below surface → Layer 4)",
    xy=(LAND_X0, surf_y), xytext=(-0.3, surf_y),
    ha="right", va="center", fontsize=8,
    bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec="#2e7d32", alpha=0.95),
    arrowprops=dict(arrowstyle="-|>", color="#2e7d32", lw=1.4),
)

# Recharge arrow at land surface
ax.annotate(
    "Recharge (RCH)\nmonthly NLDAS",
    xy=(LAND_MID, 0.0), xytext=(LAND_MID, -0.85),
    ha="center", va="top", fontsize=8,
    bbox=dict(boxstyle="round,pad=0.3", fc="#e3f2fd", ec="#1565c0", alpha=0.95),
    arrowprops=dict(arrowstyle="-|>", color="#1565c0", lw=1.4),
)

# ─────────────────────────────────────────────────────────────────────────────
# BOUNDARY CONDITION ANNOTATIONS — lake side
# ─────────────────────────────────────────────────────────────────────────────
# GHB at lake side
ghb_y = y_tops[0] + (y_tops[1] - y_tops[0]) * 0.5
ax.annotate(
    "GHB — Great Lakes\n(monthly stage, Kv lakebed)",
    xy=(LAKE_X1, ghb_y), xytext=(LAKE_X1 + 0.15, ghb_y - 0.3),
    ha="left", va="center", fontsize=8,
    bbox=dict(boxstyle="round,pad=0.3", fc="#e3f2fd", ec="#1565c0", alpha=0.95),
    arrowprops=dict(arrowstyle="-|>", color="#1565c0", lw=1.4),
)

# Lake floor label
lake_floor_y = y_tops[1] - 0.01
ax.plot([LAKE_X0, LAKE_X1], [lake_floor_y, lake_floor_y],
        color="saddlebrown", lw=2.0, ls="--", zorder=6)
ax.text(LAKE_MID, lake_floor_y - 0.12, "Lake floor (bathymetry)",
        ha="center", fontsize=7.5, color="saddlebrown", style="italic")

# ─────────────────────────────────────────────────────────────────────────────
# VERTICAL SCALE LABEL (not to scale notice)
# ─────────────────────────────────────────────────────────────────────────────
ax.text(0.05, total_height + 0.45,
        "⚠  Vertical scale is SCHEMATIC (not to scale)\n"
        "   True depths: Soil 0–1 m  |  Quaternary variable  |  Base at 600 m",
        fontsize=8, color="#555555", style="italic",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fffff0", ec="#aaaaaa", alpha=0.9))

# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL LEGEND
# ─────────────────────────────────────────────────────────────────────────────
legend_handles = [
    mpatches.Patch(fc="#c8a46e", ec="grey", label="Soil layers (L1–L3, 0–1 m)"),
    mpatches.Patch(fc="#e8d09a", ec="grey", label="Quaternary deposits (L4–L6, variable)"),
    mpatches.Patch(fc="#c09070", ec="grey", label="Fractured bedrock (L7, 5 m fixed)"),
    mpatches.Patch(fc="#808080", ec="grey", label="Deep bedrock (L8, base 600 m)"),
    mpatches.Patch(fc="#4a9fcf", ec="grey", label="Lake water column (L1, lake cells only)"),
    mpatches.Patch(fc="#fffbe6", ec="#e6a800", label="Stream/wetland drain (DRN, 0.5 m depth)"),
    mpatches.Patch(fc="#e8f5e9", ec="#2e7d32", label="Surface seepage drain (DRN, 5 m depth)"),
    mpatches.Patch(fc="#e3f2fd", ec="#1565c0", label="GHB / Recharge (lake stage / NLDAS)"),
]
ax.legend(handles=legend_handles, loc="lower right",
          bbox_to_anchor=(1.0, -0.01), fontsize=8,
          framealpha=0.95, edgecolor="#888888", ncol=2)

# ─────────────────────────────────────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────────────────────────────────────
ax.set_title(
    "Great Lakes Basin — MODFLOW 6 Conceptual Model\n"
    "8-Layer Geological Structure  |  1 km × 1 km grid  |  Jan 2000 – Dec 2025",
    fontsize=13, fontweight="bold", pad=14)

plt.tight_layout()
plt.savefig(OUT_FIG, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT_FIG}")
plt.show()
