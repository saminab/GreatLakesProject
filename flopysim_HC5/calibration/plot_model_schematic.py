"""
plot_model_schematic.py  --  Conceptual cross-section of the Great Lakes model
showing WHERE each calibration parameter acts in the flow system.

A presentation/paper schematic (not data-driven): a vertical slice through the
model with the Great Lake, recharge in, a draining stream, and the five stacked
geologic layers.  Numbered markers locate the five Calibration-1 global
parameters; teal tags on each layer mark the Calibration-2 per-layer horizontal
hydraulic-conductivity multipliers (kh_l1..kh_l5).

Writes model_parameter_cross_section.png + .svg to (in priority order):
  1. a directory given on the command line:   python plot_model_schematic.py "D:\\some\\dir"
  2. else  <MODEL_BASE_DIR>\\Figures\\Calibration_1   (from config.py)
  3. else  ./figures   (fallback if config can't be imported)
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Resolve output directory
# ---------------------------------------------------------------------------
if len(sys.argv) > 1:
    OUT_DIR = sys.argv[1]
else:
    try:
        sys.path.insert(0, os.path.dirname(HERE))      # flopysim_HC5/ holds config.py
        from config import MODEL_BASE_DIR
        OUT_DIR = os.path.join(MODEL_BASE_DIR, "Figures", "Calibration_1")
    except Exception as e:
        print(f"[schematic] could not import config ({e}); using ./figures")
        OUT_DIR = os.path.join(HERE, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Palette (fixed light-mode colors -- this is a saved figure)
# ---------------------------------------------------------------------------
AMBER_F, AMBER_E = "#FAEEDA", "#BA7517"
GRAY_F,  GRAY_E  = "#D3D1C7", "#5F5E5A"
BLUE_F,  BLUE_E  = "#B5D4F4", "#185FA5"
WATER            = "#378ADD"
TEAL_F,  TEAL_E, TEAL_T = "#9FE1CB", "#0F6E56", "#04342C"
CORAL            = "#D85A30"
TXT              = "#2C2C2A"

# SVG-style coordinates: x 0..680, y 0..560 with y increasing DOWNWARD
fig, ax = plt.subplots(figsize=(11, 9), dpi=200)
ax.set_xlim(0, 680)
ax.set_ylim(560, 0)          # invert so y grows downward like a cross-section
ax.axis("off")


def rect(x, y, w, h, fc, ec):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=1.2))


def pill(x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0,rounding_size=4",
                 facecolor=TEAL_F, edgecolor=TEAL_E, linewidth=1.0))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=9, color=TEAL_T)


def marker(x, y, n, r=11):
    ax.add_patch(Circle((x, y), r, facecolor=CORAL, edgecolor="none"))
    ax.text(x, y, str(n), ha="center", va="center", fontsize=10,
            color="white", fontweight="medium")


def varrow(x, y0, y1, color=WATER, double=False):
    style = "<|-|>" if double else "-|>"
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=2))


def harrow(x0, x1, y, color=GRAY_E, double=True):
    style = "<|-|>" if double else "-|>"
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle=style, color=color, lw=2))


# --- recharge (1) -----------------------------------------------------------
ax.text(395, 58, "net recharge (precipitation in)", ha="center", va="center",
        fontsize=9, color=TXT)
for xr in (245, 295, 345, 445, 495, 545):
    varrow(xr, 84, 147)
marker(395, 76, 1)

# --- geologic layers --------------------------------------------------------
rect(95, 150, 525, 48, AMBER_F, AMBER_E)
rect(95, 198, 525, 48, AMBER_F, AMBER_E)
rect(95, 246, 525, 52, AMBER_F, AMBER_E)
rect(95, 298, 525, 26, GRAY_F,  GRAY_E)
rect(95, 324, 525, 72, GRAY_F,  GRAY_E)
for txt, yy in [("Quaternary 1 — surficial", 174), ("Quaternary 2", 222),
                ("Quaternary 3", 272), ("fractured bedrock", 311),
                ("deep bedrock (to −600 m)", 360)]:
    ax.text(612, yy, txt, ha="right", va="center", fontsize=10, color=TXT)

# --- per-layer Kh tags (Calibration 2) --------------------------------------
for lab, yy in [("kh_l1", 164), ("kh_l2", 212), ("kh_l3", 262),
                ("kh_l4", 301), ("kh_l5", 350)]:
    pill(44, yy, 48, 20, lab)

# --- lake + GHB (3) ---------------------------------------------------------
rect(95, 124, 105, 26, BLUE_F, BLUE_E)
ax.text(147, 137, "Great Lake", ha="center", va="center", fontsize=10, color=BLUE_E)
varrow(150, 150, 178, double=True)
marker(183, 166, 3)

# --- water table ------------------------------------------------------------
xt = np.linspace(200, 620, 100)
yt = 160 + 6 * np.sin((xt - 200) / 120) - (xt - 200) * 0.004
ax.plot(xt, yt, color=WATER, lw=1.5, ls=(0, (5, 4)))
ax.text(225, 148, "water table", ha="left", va="center", fontsize=9, color=BLUE_E)

# --- anisotropy (2): Kh >> Kv in Quaternary 2 -------------------------------
harrow(278, 360, 222)
varrow(318, 210, 236, color=GRAY_E, double=True)
marker(247, 222, 2)

# --- stream + drain depth (4, 5) --------------------------------------------
ax.add_patch(plt.Polygon([[368, 150], [380, 162], [392, 150]], facecolor=WATER))
ax.text(380, 140, "stream", ha="center", va="center", fontsize=9, color=TXT)
marker(345, 170, 4)
marker(415, 170, 5)

# --- observation wells ------------------------------------------------------
for xw, yw in [(270, 161), (540, 159)]:
    ax.plot([xw, xw], [150, 250], color=GRAY_E, lw=2)
    ax.add_patch(Circle((xw, yw), 3.5, facecolor=BLUE_E, edgecolor="none"))
ax.text(95, 420, "observation wells (blue dot = measured head) are the calibration targets",
        ha="left", va="center", fontsize=9, color=TXT)

# --- key --------------------------------------------------------------------
ax.plot([95, 620], [436, 436], color="#B4B2A9", lw=1)
key_left = [
    (1, "RCH_MULT — net recharge (water in)"),
    (2, "KV_ANISO_RATIO — vertical : horizontal K"),
    (3, "GHB_COND_MULT — Great-Lake exchange"),
]
key_right = [
    (4, "DRN_COND_MULT — stream discharge rate"),
    (5, "DRN_DEPTH_M — water-table ceiling"),
]
for i, (n, txt) in enumerate(key_left):
    yy = 458 + i * 24
    ax.add_patch(Circle((103, yy), 8, facecolor=CORAL, edgecolor="none"))
    ax.text(103, yy, str(n), ha="center", va="center", fontsize=9, color="white")
    ax.text(118, yy, txt, ha="left", va="center", fontsize=9, color=TXT)
for i, (n, txt) in enumerate(key_right):
    yy = 458 + i * 24
    ax.add_patch(Circle((383, yy), 8, facecolor=CORAL, edgecolor="none"))
    ax.text(383, yy, str(n), ha="center", va="center", fontsize=9, color="white")
    ax.text(398, yy, txt, ha="left", va="center", fontsize=9, color=TXT)
# teal entry for Cal-2 Kh
ax.add_patch(FancyBboxPatch((375, 500), 16, 13,
             boxstyle="round,pad=0,rounding_size=3",
             facecolor=TEAL_F, edgecolor=TEAL_E, linewidth=1.0))
ax.text(398, 506, "kh_l1–l5 — per-layer horizontal K (Cal 2)",
        ha="left", va="center", fontsize=9, color=TXT)

# ---------------------------------------------------------------------------
png = os.path.join(OUT_DIR, "model_parameter_cross_section.png")
svg = os.path.join(OUT_DIR, "model_parameter_cross_section.svg")
fig.savefig(png, bbox_inches="tight", facecolor="white")
fig.savefig(svg, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"wrote {png}")
print(f"wrote {svg}")
