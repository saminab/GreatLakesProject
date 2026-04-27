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

def add_scalebar(ax, delr, delc, length_km=100):
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

def base_ax(ax, letter, title):
    """Apply standard axis formatting for model input summary plots."""
    ax.set_title(f"{letter} {title}", loc="left", fontweight="bold", fontsize=10)
    ax.set_xlabel("Easting (m)", fontsize=8)
    ax.set_ylabel("Northing (m)", fontsize=8)
    ax.tick_params(labelsize=7)

def outline_ring(ax, ring_mask_2d, extent, n_ring=None):
    """Overlay a red contour outline of the GHB ring cells on ax."""
    if n_ring is not None and n_ring == 0:
        return
    if not np.any(ring_mask_2d):
        return
    ax.contour(
        ring_mask_2d.astype(float),
        levels=[0.5],
        colors="#cc0033",
        linewidths=0.6,
        extent=extent,
        origin="upper",
    )

def pct_terrestrial(arr, lo, hi, terrestrial_mask):
    """Return (lo, hi) percentile of arr over terrestrial (non-lake) active cells."""
    v = arr[terrestrial_mask & np.isfinite(arr)]
    return (float(np.nanpercentile(v, lo)),
            float(np.nanpercentile(v, hi))) if v.size else (0, 1)

def row(name, arr, terr, ring, unit=""):
    """Print one summary statistics row split by terrestrial vs GHB-ring cells."""
    t = arr[terr][np.isfinite(arr[terr])]
    r = arr[ring][np.isfinite(arr[ring])]
    print(f"{name:8s} "
          f"{t.min():>7.2g} {np.median(t):>7.2g} {t.max():>7.2g} "
          f"| {r.min():>6.2g} {np.median(r):>6.2g} {r.max():>6.2g} {unit}")

def add_north_arrow(ax, x=0.92, y=0.90, size=0.10):
    """Add a north arrow annotation to ax using axes-fraction coordinates."""
    ax.annotate(
        "N",
        xy=(x, y), xytext=(x, y - size),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="center", va="center",
        fontsize=12, fontweight="bold",
        arrowprops=dict(facecolor="black", edgecolor="black", width=3, headwidth=10),
    )

def add_scale_bar(ax, delr, delc, length_km=100, loc="lower left"):
    """Add an anchored scale bar. delr/delc needed to set bar height proportional to cell size."""
    fontprops = fm.FontProperties(size=10)
    scalebar = AnchoredSizeBar(
        ax.transData,
        length_km * 1000.0,
        f"{length_km} km",
        loc=loc,
        pad=0.4,
        color="black",
        frameon=False,
        size_vertical=max(delc[0], delr[0]) * 2.0,
        fontproperties=fontprops,
    )
    ax.add_artist(scalebar)

def add_dtw_colorbar(fig, pcm, ax_or_axes, bounds):
    """Add a depth-to-water colorbar with class-midpoint tick labels."""
    cbar = fig.colorbar(
        pcm,
        ax=ax_or_axes,
        boundaries=bounds,
        ticks=bounds,
        spacing="proportional",
        extend="max",
        shrink=0.82,
    )
    tick_locs = [(bounds[i] + bounds[i + 1]) / 2 for i in range(len(bounds) - 1)]
    cbar.set_ticks(tick_locs)
    labels = [f"{bounds[i]}–{bounds[i+1]}" for i in range(len(bounds) - 2)]
    labels.append(f">{bounds[-2]}")
    cbar.set_ticklabels(labels)
    cbar.set_label("Depth to groundwater (m below ground level)")
    return cbar

