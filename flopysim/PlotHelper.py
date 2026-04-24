# Plot Imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap, BoundaryNorm, LinearSegmentedColormap
from matplotlib.ticker import FixedLocator
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm
# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------
def get_plot_extent(xorigin, yorigin, delr, delc, nrow, ncol):
    return [xorigin,
            xorigin + np.sum(delr),
            yorigin,
            yorigin + np.sum(delc)]

def rec_list_to_mask(rec_list, nrow, ncol):
    mask = np.full((nrow, ncol), np.nan, dtype=float)
    if rec_list is None or len(rec_list) == 0:
        return mask
    for rec in rec_list:
        try:
            k, i, j = rec[0]
            if 0 <= i < nrow and 0 <= j < ncol:
                mask[i, j] = 1.0
        except Exception:
            continue
    return mask

def ghb_df_to_mask(ghb_cells_df, nrow, ncol):
    mask = np.full((nrow, ncol), np.nan, dtype=float)
    if ghb_cells_df is None or len(ghb_cells_df) == 0:
        return mask
    for r in ghb_cells_df.itertuples(index=False):
        i, j = int(r.i), int(r.j)
        if 0 <= i < nrow and 0 <= j < ncol:
            mask[i, j] = 1.0
    return mask

def active_array(arr, idomain2d):
    out = np.array(arr, dtype=float).copy()
    out[idomain2d <= 0] = np.nan
    return out

def pct(arr, lo, hi):
    v = arr[np.isfinite(arr)]
    return (float(np.nanpercentile(v, lo)),
            float(np.nanpercentile(v, hi))) if v.size else (0, 1)

def add_scalebar(ax, length_km=100):
    fp = fm.FontProperties(size=9)
    ax.add_artist(AnchoredSizeBar(
        ax.transData, length_km * 1000,
        f"{length_km} km", "lower left",
        pad=0.3, color="black", frameon=False,
        size_vertical=max(delc[0], delr[0]) * 1.5,
        fontproperties=fp))

def add_north(ax, x=0.92, y=0.90, size=0.09):
    ax.annotate("N", xy=(x, y), xytext=(x, y - size),
                xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="center",
                fontsize=11, fontweight="bold",
                arrowprops=dict(facecolor="black", edgecolor="black",
                                width=2.5, headwidth=9))

def add_cbar(fig, ax, im, label, fontsize=9):
    cb = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.02)
    cb.set_label(label, fontsize=fontsize)
    cb.ax.tick_params(labelsize=8)
    return cb

def relabel_log_cbar(cb):
    ticks = cb.get_ticks()
    cb.ax.yaxis.set_major_locator(FixedLocator(ticks))
    cb.set_ticklabels([f"{10**t:.2g}" for t in ticks])
    
def compute_quantile_bounds(arr, n_classes):
    """
    Compute quantile-based class boundaries from a 2D array.
    Only uses finite values > 0.001.
    """
    vals = arr[np.isfinite(arr) & (arr > 0.001)]
    vals = np.sort(vals)
    if vals.size == 0:
        return np.linspace(0, 1, n_classes + 1), vals
    percentiles = np.linspace(0, 100, n_classes + 1)
    bounds = np.percentile(vals, percentiles)
    bounds = np.unique(bounds)
    return bounds, vals

