##  Helper functions

# All reusable helper functions are grouped here so the rest of the notebook can stay short and readable.
# This includes:
# - grid/template helpers
# - raster read/write helpers
# - recharge helpers
# - GHB helpers
# - DRN helper builders
# - run configuration export
from pathlib import Path
import os, re, gc, shutil, calendar, time, tempfile

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio as rio
import fiona
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
from rasterio.crs import CRS
from rasterio.transform import from_origin, from_bounds
from affine import Affine
import xarray as xr
import flopy
from flopy.utils.gridintersect import GridIntersect
from scipy.ndimage import label
import matplotlib.pyplot as plt


def snap_bounds_to_cell(bounds, cell):
    xmin, ymin, xmax, ymax = bounds
    xmin = np.floor(xmin / cell) * cell
    ymin = np.floor(ymin / cell) * cell
    xmax = np.ceil(xmax / cell) * cell
    ymax = np.ceil(ymax / cell) * cell
    return float(xmin), float(ymin), float(xmax), float(ymax)

def build_model_months(start_date, nper):
    return pd.date_range(start=start_date, periods=nper, freq="MS")

def build_monthly_perioddata(start="2000-01-01", end="2025-12-01", nstp=1, tsmult=1.0):
    months = pd.date_range(start=start, end=end, freq="MS")
    pddata = []
    for d in months:
        ndays = calendar.monthrange(d.year, d.month)[1]
        pddata.append((float(ndays), int(nstp), float(tsmult)))
    return pddata, months

def make_template_from_boundary(boundary_shp, out_template_tif, cellsize):
    gdf = gpd.read_file(boundary_shp)

    if gdf.crs is None:
        raise ValueError(f"Boundary file has no CRS: {boundary_shp}")

    xmin, ymin, xmax, ymax = snap_bounds_to_cell(gdf.total_bounds, cellsize)

    width = int(round((xmax - xmin) / cellsize))
    height = int(round((ymax - ymin) / cellsize))

    from rasterio.transform import from_origin
    transform = from_origin(xmin, ymax, cellsize, cellsize)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "int16",
        "transform": transform,
        "nodata": 0,
        "compress": "deflate",
        "tiled": True,
        "BIGTIFF": "YES",
    }

    if os.path.exists(out_template_tif):
        try:
            os.remove(out_template_tif)
        except PermissionError:
            print("Could not delete locked file:", out_template_tif)

    with rio.open(out_template_tif, "w", **profile) as dst:
        import numpy as np
        dst.write(np.zeros((height, width), dtype=np.int16), 1)

    return out_template_tif


def rasterize_idomain(boundary_shp, template_tif, out_idomain_tif, burn_value=1, all_touched=False):
    """
    Rasterize boundary directly onto template grid.
    Assumes boundary_shp is already in the same CRS as the intended grid.
    """
    gdf = gpd.read_file(boundary_shp)

    if gdf.crs is None:
        raise ValueError(f"Boundary file has no CRS: {boundary_shp}")

    with rio.open(template_tif) as tmp:
        arr = rasterize(
            shapes=[(geom, burn_value) for geom in gdf.geometry if geom is not None and not geom.is_empty],
            out_shape=(tmp.height, tmp.width),
            transform=tmp.transform,
            fill=0,
            dtype="int32",
            all_touched=all_touched
        )

        profile = tmp.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="int32",
            count=1,
            nodata=0,
            compress="deflate",
            tiled=True,
            BIGTIFF="YES"
        )

        # optional: strip fields that sometimes cause trouble when copied through
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)

    if os.path.exists(out_idomain_tif):
        try:
            os.remove(out_idomain_tif)
        except PermissionError:
            print("Could not delete locked file:", out_idomain_tif)

    with rio.open(out_idomain_tif, "w", **profile) as dst:
        dst.write(arr, 1)

    return out_idomain_tif

def assert_match_template_no_crs(raster_tif, template_tif, name="Raster"):
    """
    Check shape and transform only. Skip CRS because Rasterio cannot
    reliably read CRS in the current environment.
    """
    with rio.open(raster_tif) as a, rio.open(template_tif) as b:
        if (a.height, a.width) != (b.height, b.width):
            raise AssertionError(
                f"{name} shape mismatch: {(a.height, a.width)} vs {(b.height, b.width)}"
            )
        if a.transform != b.transform:
            raise AssertionError(
                f"{name} transform mismatch:\n{a.transform}\nvs\n{b.transform}"
            )
    print(f"{name} matches template in shape and transform.")




def warp_raster_to_template(src_path, template_path, out_path, resampling, dst_nodata=-9999.0):
    with rio.open(template_path) as tmpl, rio.open(src_path) as src:
        dst_meta = src.meta.copy()
        dst_meta.update(
            driver="GTiff",
            crs=tmpl.crs,
            transform=tmpl.transform,
            width=tmpl.width,
            height=tmpl.height,
            nodata=dst_nodata,
            compress="deflate",
            tiled=True,
            BIGTIFF="YES",
            blockxsize=256,
            blockysize=256,
        )
        with rio.open(out_path, "w", **dst_meta) as dst:
            for b in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, b),
                    destination=rio.band(dst, b),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=tmpl.transform,
                    dst_crs=tmpl.crs,
                    dst_nodata=dst_nodata,
                    resampling=resampling,
                )
    return out_path

def assert_match_template(path, template_path, name):
    with rio.open(template_path) as t, rio.open(path) as s:
        assert (s.height, s.width) == (t.height, t.width), f"{name} shape mismatch"
        assert s.crs == t.crs, f"{name} CRS mismatch"
        assert s.transform == t.transform, f"{name} transform mismatch"

def read_band1(path, dtype="float32"):
    with rio.open(path) as src:
        return src.read(1).astype(dtype, copy=False), src.nodata

def read_all_bands(path, dtype="float32"):
    with rio.open(path) as src:
        return src.read().astype(dtype, copy=False), src.nodata

def clean_continuous(a, nodata, fill=0.0):
    a = a.astype("float32", copy=False)
    a = np.nan_to_num(a, nan=fill, posinf=fill, neginf=fill)
    if nodata is not None:
        a = np.where(a == nodata, fill, a)
    return a

def make_gridintersect(modelgrid):
    try:
        return GridIntersect(modelgrid, method="vertex")
    except TypeError:
        try:
            return GridIntersect(modelgrid, "vertex")
        except TypeError:
            return GridIntersect(modelgrid)

def update_ghb_k_from_idomain(ghb_cells_df, idomain):
    """
    Update GHB layer k so each boundary cell is assigned to the first active layer
    at its (i, j) location based on the final DIS idomain.
    """
    df = ghb_cells_df.copy()

    if {"i", "j"}.issubset(df.columns):
        i_col, j_col = "i", "j"
    elif {"row", "col"}.issubset(df.columns):
        i_col, j_col = "row", "col"
        if "i" not in df.columns:
            df["i"] = df["row"]
        if "j" not in df.columns:
            df["j"] = df["col"]
    else:
        raise ValueError("ghb_cells_df must contain either (i, j) or (row, col) columns.")

    if idomain.ndim == 2:
        active = idomain > 0
        keep_idx = []
        new_k = []
        for idx, r in enumerate(df.itertuples(index=False)):
            i = int(getattr(r, i_col))
            j = int(getattr(r, j_col))
            if 0 <= i < active.shape[0] and 0 <= j < active.shape[1] and active[i, j]:
                keep_idx.append(idx)
                new_k.append(0)
        df = df.iloc[keep_idx].copy()
        df["k"] = new_k
        return df.reset_index(drop=True)

    if idomain.ndim == 3:
        nlay, nrow, ncol = idomain.shape
        keep_idx = []
        new_k = []
        for idx, r in enumerate(df.itertuples(index=False)):
            i = int(getattr(r, i_col))
            j = int(getattr(r, j_col))
            if not (0 <= i < nrow and 0 <= j < ncol):
                continue
            active_layers = np.where(idomain[:, i, j] > 0)[0]
            if len(active_layers) == 0:
                continue
            keep_idx.append(idx)
            new_k.append(int(active_layers[0]))
        df = df.iloc[keep_idx].copy()
        df["k"] = new_k
        return df.reset_index(drop=True)

    raise ValueError(f"idomain must be 2D or 3D, got shape {idomain.shape}")

def assign_ghb_k_from_stage_floor(ghb_cells_df, idomain, botm3d, stage_floor_by_name, stage_margin=0.05):
    """
    Choose the shallowest active layer whose bottom is below the minimum
    stage for that lake/stage_name.

    Parameters
    ----------
    ghb_cells_df : DataFrame
        Must contain stage_name, i, j
    idomain : ndarray
        3D array (nlay, nrow, ncol)
    botm3d : ndarray
        3D bottom array (nlay, nrow, ncol)
    stage_floor_by_name : pandas Series or dict
        Minimum stage for each stage_name across the modeled period
    stage_margin : float
        Small safety margin so stage > bottom + margin
    """
    if idomain.ndim != 3:
        raise ValueError("assign_ghb_k_from_stage_floor expects 3D idomain")

    df = ghb_cells_df.copy()
    keep_rows = []
    new_k = []
    dropped = []

    nlay, nrow, ncol = idomain.shape

    for idx, r in enumerate(df.itertuples(index=False)):
        i = int(r.i)
        j = int(r.j)
        sname = str(r.stage_name)

        if sname not in stage_floor_by_name:
            dropped.append((idx, "missing_stage_name"))
            continue

        if not (0 <= i < nrow and 0 <= j < ncol):
            dropped.append((idx, "out_of_bounds"))
            continue

        stage_floor = float(stage_floor_by_name[sname])

        active_layers = np.where(idomain[:, i, j] > 0)[0]
        if len(active_layers) == 0:
            dropped.append((idx, "no_active_layers"))
            continue

        valid_layers = [
            int(k) for k in active_layers
            if float(botm3d[k, i, j]) < (stage_floor - stage_margin)
        ]

        if len(valid_layers) == 0:
            dropped.append((idx, "no_layer_below_stage"))
            continue

        keep_rows.append(idx)
        new_k.append(valid_layers[0])   # shallowest valid layer

    out = df.iloc[keep_rows].copy().reset_index(drop=True)
    out["k"] = new_k

    print("GHB cells kept after stage-aware layer assignment:", len(out))
    print("GHB cells dropped:", len(dropped))
    if len(dropped) > 0:
        print(pd.Series([d[1] for d in dropped]).value_counts())

    return out


# ---- NLDAS indexing ----
def index_blend_qsb_monthlies(root: Path):
    files = sorted(root.rglob("BLEND_Qsb_A*.nc"))
    rows = []
    for f in files:
        m = re.search(r"_A(\d{6})\.nc$", f.name)
        if not m:
            continue
        yyyymm = m.group(1)
        dt = pd.Timestamp(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
        rows.append((dt, str(f)))
    df = pd.DataFrame(rows, columns=["date", "path"]).sort_values("date").reset_index(drop=True)
    return df

def copy_to_local_cached(src_path: str) -> str:
    src = Path(src_path)
    cache_dir = Path(tempfile.gettempdir()) / "nldas_nc_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dst = cache_dir / src.name
    if (not dst.exists()) or (dst.stat().st_size != src.stat().st_size) or (dst.stat().st_mtime < src.stat().st_mtime):
        shutil.copy2(src, dst)
    return str(dst)

def read_qsb_lat_lon_attrs(nc_path: str, var="Qsb"):
    local_path = copy_to_local_cached(nc_path)

    last_err = None
    for engine in ("h5netcdf", "netcdf4"):
        try:
            ds = xr.open_dataset(local_path, engine=engine, decode_times=False)
            da = ds[var]
            if "time" in da.dims:
                da = da.isel(time=0)

            units = (da.attrs.get("units") or "").strip()
            cell_methods = (da.attrs.get("cell_methods") or "").strip()

            qsb = da.values.astype("float32")
            lat = da["lat"].values
            lon = da["lon"].values
            ds.close()
            return qsb, lat, lon, units, cell_methods
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Failed to read {nc_path}. Last error: {last_err}")

def parse_yyyymm_from_filename(fname: str):
    base = Path(fname).name
    m = re.search(r"\.A(\d{6})\.", base)
    if not m:
        m = re.search(r"_A(\d{6})\.nc$", base)
    if not m:
        raise ValueError(f"Cannot parse YYYYMM from {fname}")
    yyyymm = m.group(1)
    return int(yyyymm[:4]), int(yyyymm[4:6])

def qsb_month_to_rech_mday_on_template(
    nc_path,
    template_tif,
    var,
    id2d,
    dst_crs_wkt,
    clamp_negative_to_zero=True,
    src_crs="+proj=longlat +datum=WGS84 +no_defs +type=crs",
    resampling=Resampling.bilinear,
):
    ds = xr.open_dataset(nc_path)

    if var not in ds:
        raise KeyError(f"Variable '{var}' not found in {nc_path}")

    da = ds[var].squeeze()
    vals = np.array(da.values, dtype="float32")

    lat_name = None
    lon_name = None
    for nm in da.dims:
        low = nm.lower()
        if "lat" in low or low == "y":
            lat_name = nm
        if "lon" in low or low == "x":
            lon_name = nm

    if lat_name is None or lon_name is None:
        raise ValueError(f"Could not identify lat/lon dims in {da.dims}")

    lats = np.array(ds[lat_name].values, dtype=float)
    lons = np.array(ds[lon_name].values, dtype=float)

    # north-up raster convention
    if lats[0] < lats[-1]:
        vals = np.flipud(vals)
        lats = lats[::-1]

    dx = float(np.abs(lons[1] - lons[0]))
    dy = float(np.abs(lats[1] - lats[0]))
    x0 = float(lons.min() - dx / 2.0)
    y0 = float(lats.max() + dy / 2.0)

    src_transform = Affine(dx, 0.0, x0, 0.0, -dy, y0)

    # ---------------------------------------------------------
    # CORRECT UNIT CONVERSION
    # Qsb units = kg m-2 with cell_methods = time: sum
    # -> equivalent to mm/month
    # -> convert to m/day
    # ---------------------------------------------------------
    time_val = None
    if "time" in ds.coords and ds["time"].size > 0:
        time_val = pd.to_datetime(ds["time"].values[0])
    else:
        # fallback: infer from filename if needed
        time_val = pd.Timestamp(nc_path.split(".A")[1][:6] + "01")

    days_in_month = int(time_val.days_in_month)

    rech_src = np.array(vals, dtype="float32") / 1000.0 / days_in_month
    rech_src = np.nan_to_num(rech_src, nan=0.0, posinf=0.0, neginf=0.0)

    if clamp_negative_to_zero:
        rech_src[rech_src < 0] = 0.0

    with rio.open(template_tif) as tmp:
        dst = np.zeros((tmp.height, tmp.width), dtype="float32")

        reproject(
            source=rech_src,
            destination=dst,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=tmp.transform,
            dst_crs=dst_crs_wkt,
            resampling=resampling,
            dst_nodata=0.0,
        )

    dst = np.nan_to_num(dst, nan=0.0, posinf=0.0, neginf=0.0).astype("float32")
    dst[dst < 0] = 0.0
    dst[id2d <= 0] = 0.0

    return dst

def build_rch_spd_from_index(df_nc, months_run, template_tif, id2d, var, dst_crs_wkt):
    rch_spd = {}

    for per, dt in enumerate(months_run):
        hit = df_nc.loc[df_nc["date"] == dt]

        if hit.empty:
            with rio.open(template_tif) as tmp:
                rch_spd[per] = np.zeros((tmp.height, tmp.width), dtype="float32")
            continue

        nc_path = hit.iloc[0]["path"]

        rch_spd[per] = qsb_month_to_rech_mday_on_template(
            nc_path=nc_path,
            template_tif=template_tif,
            var=var,
            id2d=id2d,
            dst_crs_wkt=dst_crs_wkt,
        )

    return rch_spd

def intersect_grid_feature(ix, pathFeature, lay=0, addFields=None, grid_crs=None):
    addFields = addFields or []
    try:
        gdf = gpd.read_file(pathFeature, engine="fiona")
    except Exception:
        gdf = gpd.read_file(pathFeature)
        
    if gdf.empty:
        return pd.DataFrame()

    if grid_crs is not None and gdf.crs is not None and gdf.crs != grid_crs:
        gdf = gdf.to_crs(grid_crs)

    try:
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    except TypeError:
        gdf = gdf.explode().reset_index(drop=True)

    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()

    try:
        gdf["geometry"] = gdf.geometry.buffer(0)
    except Exception:
        pass

    parts = []
    for i in range(len(gdf)):
        geom = gdf.geometry.iloc[i]
        if geom is None or geom.is_empty:
            continue
        try:
            df = pd.DataFrame(ix.intersect(geom, geo_dataframe=False))
        except TypeError:
            df = pd.DataFrame(ix.intersect(geom))
        if df.empty:
            continue

        for f in addFields:
            if f in gdf.columns:
                df[f] = gdf[f].iloc[i]

        df["cellids"] = df["cellids"].apply(lambda rc: (lay, rc[0], rc[1]))
        df["row"] = df["cellids"].apply(lambda x: x[1])
        df["col"] = df["cellids"].apply(lambda x: x[2])
        parts.append(df)

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)

def compute_thickness(top2d, botm3d):
    thick = np.zeros_like(botm3d, dtype=float)
    thick[0] = top2d - botm3d[0]
    for k in range(1, botm3d.shape[0]):
        thick[k] = botm3d[k - 1] - botm3d[k]
    return thick

def ensure_3d(arr, nlay, nrow, ncol):
    arr = np.asarray(arr)
    if arr.ndim == 0:
        return np.full((nlay, nrow, ncol), float(arr))
    elif arr.ndim == 2:
        return np.repeat(arr[np.newaxis, :, :], nlay, axis=0)
    elif arr.ndim == 3:
        return arr
    else:
        raise ValueError(f"Unexpected array ndim: {arr.ndim}")

def get_extent(xorigin, yorigin, delr, delc, nrow, ncol):
    # handles both scalar (uniform) and array (variable) cell sizes
    width  = ncol * float(delr) if np.ndim(delr) == 0 else float(np.sum(delr))
    height = nrow * float(delc) if np.ndim(delc) == 0 else float(np.sum(delc))
    return [xorigin, xorigin + width, yorigin, yorigin + height]

def mask_model_array(arr, idomain_layer=None, huge=1e20):
    """Mask MODFLOW placeholder values (|val| >= huge) and optionally inactive cells."""
    a = np.array(arr, dtype=float)
    a[np.abs(a) >= huge] = np.nan
    if idomain_layer is not None:
        a = np.where(np.asarray(idomain_layer) > 0, a, np.nan)
    return a

def get_date_labels(nper, months=None):
    """Return YYYY-MM strings for plot axes, falling back to 'SP N' labels."""
    if months is not None and len(months) >= nper:
        return [pd.to_datetime(m).strftime("%Y-%m") for m in months[:nper]]
    return [f"SP {i + 1}" for i in range(nper)]

def get_water_table(head_t, idomain, huge=1e29):
    """Water table = first valid head downward; masks MF6 dry-cell placeholder (1e30)."""
    nlay, nrow, ncol = head_t.shape
    wt = np.full((nrow, ncol), np.nan, dtype=float)
    for k in range(nlay):
        hk = np.array(head_t[k], dtype=float)
        hk[np.abs(hk) >= huge] = np.nan
        hk[idomain[k] <= 0]    = np.nan
        hk[hk >  10000]        = np.nan   # above realistic surface elevation
        hk[hk < -1000]         = np.nan   # below realistic head
        take = np.isnan(wt) & np.isfinite(hk)
        wt[take] = hk[take]
    return wt

def get_depth_to_water(head_t, idomain, top, clip_negative=True):
    """Depth to water table (top - water_table). Optionally clip negative (artesian) values."""
    wt  = get_water_table(head_t, idomain)
    dtw = np.array(top, dtype=float) - wt
    dtw[~np.isfinite(wt)] = np.nan
    if clip_negative:
        dtw = np.where(np.isfinite(dtw), np.maximum(dtw, 0.0), np.nan)
    return dtw

def robust_limits(arr, qlow=2, qhigh=98, symmetric=False):
    """Return (vmin, vmax) as percentile-based color limits, ignoring non-finite values."""
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return 0.0, 1.0
    vmin = float(np.nanpercentile(a, qlow))
    vmax = float(np.nanpercentile(a, qhigh))
    if symmetric:
        vmax_abs = max(abs(vmin), abs(vmax))
        return -vmax_abs, vmax_abs
    return vmin, vmax

def extract_head_series(hdobj, kstpkper_list, layer, row, col, idomain3d, huge=1e20):
    """Extract a head time series at a single model cell, replacing dry/inactive with NaN."""
    vals = []
    for kp in kstpkper_list:
        h = hdobj.get_data(kstpkper=kp)
        v = float(h[layer, row, col])
        if abs(v) >= huge or idomain3d[layer, row, col] <= 0:
            vals.append(np.nan)
        else:
            vals.append(v)
    return np.array(vals, dtype=float)

def plot_bc_masks(chd_rec, drn_rec, xorigin, yorigin, delr, delc, nrow, ncol, idomain=None):
    extent = get_extent(xorigin, yorigin, delr, delc, nrow, ncol)

    if idomain is not None:
        bg = np.where(idomain[0] > 0, 1.0, np.nan)
    else:
        bg = np.ones((nrow, ncol), dtype=float)

    chd_mask = np.full((nrow, ncol), np.nan, dtype=float)
    drn_mask = np.full((nrow, ncol), np.nan, dtype=float)

    for (k, r, c), _ in chd_rec:
        if int(k) == 0:
            chd_mask[int(r), int(c)] = 1.0

    for rec in drn_rec:
        (k, r, c), elev, cond = rec
        if int(k) == 0:
            drn_mask[int(r), int(c)] = 1.0

    plt.figure(figsize=(10, 8))
    plt.imshow(bg, origin="upper", extent=extent, alpha=0.15, cmap="Greys")
    plt.imshow(chd_mask, origin="upper", extent=extent, alpha=0.9, cmap="Blues")
    plt.imshow(drn_mask, origin="upper", extent=extent, alpha=0.8, cmap="Reds")
    plt.title("Boundary-condition cells (CHD=blue, DRN=red)")
    plt.xlabel("Easting (m)")
    plt.ylabel("Northing (m)")
    plt.tight_layout()
    plt.show()

def safe_rmtree(folder, tries=10, wait=1.0):
    folder = Path(folder)
    if not folder.exists():
        return
    gc.collect()
    time.sleep(0.2)
    last_err = None
    for _ in range(tries):
        try:
            shutil.rmtree(folder)
            return
        except Exception as e:
            last_err = e
            gc.collect()
            time.sleep(wait)
    raise last_err

def extract_kij(rec_list):
    """
    Extract (k, i, j) from MODFLOW-style boundary record lists.

    Supports records like:
      ((k, i, j), head, cond, ...)
      ((k, i, j), elev, cond, ...)
    """
    if rec_list is None or len(rec_list) == 0:
        return np.empty((0, 3), dtype=int)

    out = []
    for rec in rec_list:
        try:
            cellid = rec[0]
            k, i, j = cellid
            out.append((int(k), int(i), int(j)))
        except Exception:
            # skip malformed records
            continue

    if len(out) == 0:
        return np.empty((0, 3), dtype=int)

    return np.array(out, dtype=int)


def build_lake_mask(LAKES_SHP, grid_crs, xorigin, yorigin, delr, delc, nrow, ncol):
    lakes = gpd.read_file(LAKES_SHP)

    if lakes.crs is not None:
        try:
            lakes = lakes.to_crs(grid_crs)
        except Exception:
            lakes = lakes.to_crs(str(grid_crs))

    ymax = yorigin + np.sum(delc)
    transform = from_origin(xorigin, ymax, float(delr[0]), float(delc[0]))

    lake_mask = rasterize(
        [(geom, 1) for geom in lakes.geometry if geom is not None and not geom.is_empty],
        out_shape=(nrow, ncol),
        transform=transform,
        fill=0,
        default_value=1,
        dtype="uint8",
    ).astype(bool)

    return lake_mask

def save_or_show(fig_dir, filename):
    if save_figs:
        outpath = os.path.join(fig_dir, filename)
        fig.savefig(outpath, dpi=300, bbox_inches="tight")
        print("Saved figure:", outpath)
    plt.show()
    
    
    
# function for wetlands 
def build_wetland_drn(
    pathWetlands,
    ix,
    grid_crs,
    idomain,
    top2d,
    botm3d,
    hk3d,
    delr,
    delc,
    WETLAND_TSED_M=1.0,
    WETLAND_KV_DIVISOR=10.0,
    WETLAND_DEPTH_BELOW_LAND_M=0.1,
    MIN_KV=1e-8,
):
    """
    Build wetland drain cells from wetland polygons intersected with model grid.

    Conductance:
        C = K * Af / Tsed
    where
        K   = proxy vertical K from top layer = hk3d[0] / WETLAND_KV_DIVISOR
        Af  = wetland overlap area in the cell
        Tsed= assumed wetland-bottom sediment thickness

    Drain elevation:
        top2d - WETLAND_DEPTH_BELOW_LAND_M,
        but never below cell bottom + 0.1 m
    """
    import numpy as np
    import pandas as pd

    wet = intersect_grid_feature(
        ix=ix,
        pathFeature=pathWetlands,
        lay=0,
        addFields=[],
        grid_crs=grid_crs,
    )

    if wet.empty:
        raise ValueError("Wetland-grid intersection returned no cells.")

    # overlap area
    if "areas" in wet.columns:
        wet["Af"] = pd.to_numeric(wet["areas"], errors="coerce")
    elif "area" in wet.columns:
        wet["Af"] = pd.to_numeric(wet["area"], errors="coerce")
    else:
        raise ValueError("Could not find overlap area column ('areas' or 'area').")

    wet = wet[wet["Af"].notna() & (wet["Af"] > 0)].copy()

    # current grid indices
    wet["i"] = wet["row"].astype(int)
    wet["j"] = wet["col"].astype(int)
    wet["k"] = 0

    # keep active top-layer cells only
    rr = wet["i"].to_numpy(dtype=int)
    cc = wet["j"].to_numpy(dtype=int)
    keep = (
        (rr >= 0) & (rr < idomain.shape[1]) &
        (cc >= 0) & (cc < idomain.shape[2]) &
        (idomain[0, rr, cc] > 0)
    )
    wet = wet.loc[keep].copy()

    if wet.empty:
        raise ValueError("All wetland intersections were removed by top-layer idomain.")

    rr = wet["i"].to_numpy(dtype=int)
    cc = wet["j"].to_numpy(dtype=int)

    # K proxy
    kv = hk3d[0, rr, cc].astype(float) / float(WETLAND_KV_DIVISOR)
    kv = np.maximum(kv, MIN_KV)

    # drain elevation
    elev = top2d[rr, cc].astype(float) - float(WETLAND_DEPTH_BELOW_LAND_M)
    elev = np.maximum(elev, botm3d[0, rr, cc].astype(float) + 0.1)

    # conductance
    cond = kv * wet["Af"].to_numpy(dtype=float) / float(WETLAND_TSED_M)

    wet["elev"] = elev
    wet["kv"] = kv
    wet["cond"] = cond

    # collapse duplicates by cell
    dfWetDrn = (
        wet.groupby(["k", "i", "j"], as_index=False)
        .agg(
            Af=("Af", "sum"),
            elev=("elev", "min"),
            kv=("kv", "first"),
            cond=("cond", "sum"),
        )
    )

    dfWetDrn = dfWetDrn[dfWetDrn["cond"] > 0].copy()

    wet_drn_rec = [
        ((int(r.k), int(r.i), int(r.j)), float(r.elev), float(r.cond))
        for r in dfWetDrn.itertuples(index=False)
    ]

    return dfWetDrn, wet_drn_rec


def build_cellid_set_from_df(df):
    if df is None or len(df) == 0:
        return set()
    d = df.copy()
    if "cellids" not in d.columns:
        d["cellids"] = list(zip(d["lay"].astype(int), d["row"].astype(int), d["col"].astype(int)))
    return set(d["cellids"])

def build_cellid_set_from_rec(rec):
    out = set()
    if rec is None:
        return out
    for r in rec:
        cellid = r[0]
        if isinstance(cellid, tuple) and len(cellid) == 3:
            out.add((int(cellid[0]), int(cellid[1]), int(cellid[2])))
    return out

def get_template_info(template_tif):
    with rio.open(template_tif) as src:
        b = src.bounds
        transform = src.transform
        dx = abs(transform.a)
        dy = abs(transform.e)
    return (b.left, b.bottom, b.right, b.top), dx, dy

def build_drn_from_streams_glb(
    ix,
    gdb_path,
    layer_name,
    template_tif,
    id2d,
    top2d,
    botm3d,
    hk3d=None,
    lay=0,

    width_field="WIDTH_M",
    fcode_field="FCODE",
    permanency_field="PERMANENCY",
    flowclass_field="FLOW_CLASS",

    default_width=10.0,

    min_width=None,               # e.g. 25.0 or 10.0
    keep_permanency=None,         # e.g. ["Perennial"] after checking actual values
    keep_flowclass=None,          # e.g. ["StreamRiver"] after checking actual values
    keep_fcodes=None,
    drop_fcodes=None,

    simplify_tol=100.0,
    min_len=None,
    min_len_frac=0.30,

    elev_offset=0.5,
    bed_thick=1.0,
    bed_k=0.1,
    cond_mult=1.0,
    cond_cap=5e4,

    dfChd=None,
    chd_rec=None,
    report_every=1000,
):
    bbox_tuple, dx, dy = get_template_info(template_tif)
    cellsize = float(min(dx, dy))

    if min_len is None:
        min_len = float(min_len_frac) * cellsize

    print("Template cell size:", cellsize)
    print("Using min_len:", min_len)

    print("Available layers in GDB (first 30):")
    print(fiona.listlayers(gdb_path)[:30])

    gdf = gpd.read_file(
        gdb_path,
        layer=layer_name,
        bbox=bbox_tuple,
        engine="fiona",
    )

    if gdf.empty:
        raise RuntimeError("No stream features read in model bbox.")

    print("Loaded features:", len(gdf))
    print("Columns:", gdf.columns.tolist())

    gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()
    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()

    if gdf.empty:
        raise RuntimeError("No valid LineString/MultiLineString features remain.")

    if simplify_tol is not None and simplify_tol > 0:
        gdf["geometry"] = gdf.geometry.simplify(simplify_tol, preserve_topology=False)
        gdf = gdf[gdf.geometry.notna() & (~gdf.geometry.is_empty)].copy()

    # width
    if width_field in gdf.columns:
        gdf["width_m"] = pd.to_numeric(gdf[width_field], errors="coerce")
    else:
        gdf["width_m"] = np.nan

    gdf["width_m"] = gdf["width_m"].fillna(default_width)
    gdf.loc[~np.isfinite(gdf["width_m"]), "width_m"] = float(default_width)
    gdf.loc[gdf["width_m"] <= 0, "width_m"] = float(default_width)

    print("Width unique:", np.unique(gdf["width_m"])[:20])

    if min_width is not None:
        before = len(gdf)
        gdf = gdf[gdf["width_m"] >= float(min_width)].copy()
        print(f"Filter width >= {min_width}: {before} -> {len(gdf)}")

    # permanency
    if keep_permanency is not None and permanency_field in gdf.columns:
        before = len(gdf)
        gdf = gdf[gdf[permanency_field].isin(keep_permanency)].copy()
        print(f"Filter PERMANENCY in {keep_permanency}: {before} -> {len(gdf)}")

    # flow class
    if keep_flowclass is not None and flowclass_field in gdf.columns:
        before = len(gdf)
        gdf = gdf[gdf[flowclass_field].isin(keep_flowclass)].copy()
        print(f"Filter FLOW_CLASS in {keep_flowclass}: {before} -> {len(gdf)}")

    # fcode
    if fcode_field in gdf.columns:
        if keep_fcodes is not None:
            before = len(gdf)
            gdf = gdf[gdf[fcode_field].isin(list(keep_fcodes))].copy()
            print(f"Keep FCodes {keep_fcodes}: {before} -> {len(gdf)}")

        if drop_fcodes is not None:
            before = len(gdf)
            gdf = gdf[~gdf[fcode_field].isin(list(drop_fcodes))].copy()
            print(f"Drop FCodes {drop_fcodes}: {before} -> {len(gdf)}")

    if gdf.empty:
        raise RuntimeError("All stream features were removed by filtering.")

    # intersect feature-by-feature
    acc = {}
    geoms = gdf.geometry.values
    widths = gdf["width_m"].to_numpy(dtype=float)

    print("Intersecting filtered stream features with grid...")
    for n, (geom, width_m) in enumerate(zip(geoms, widths), start=1):
        if geom is None or geom.is_empty:
            continue

        try:
            out = ix.intersect(geom, geo_dataframe=False)
        except TypeError:
            out = ix.intersect(geom)

        df = pd.DataFrame(out)
        if df.empty:
            continue

        if "lengths" in df.columns:
            length_col = "lengths"
        elif "length" in df.columns:
            length_col = "length"
        else:
            raise RuntimeError(f"No line length column returned. Got: {df.columns.tolist()}")

        if "cellids" in df.columns:
            cellid_col = "cellids"
        elif "cellid" in df.columns:
            cellid_col = "cellid"
        else:
            raise RuntimeError(f"No cellid column returned. Got: {df.columns.tolist()}")

        lens = pd.to_numeric(df[length_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        cellids = df[cellid_col].tolist()

        for cellid, L in zip(cellids, lens):
            if L <= 0:
                continue

            if isinstance(cellid, tuple):
                if len(cellid) == 2:
                    row, col = int(cellid[0]), int(cellid[1])
                elif len(cellid) == 3:
                    row, col = int(cellid[-2]), int(cellid[-1])
                else:
                    continue
            else:
                continue

            key = (int(lay), row, col)
            if key not in acc:
                acc[key] = {"lengths": 0.0, "wlen": 0.0}

            acc[key]["lengths"] += float(L)
            acc[key]["wlen"] += float(width_m) * float(L)

        if n % report_every == 0:
            print(f"  intersected {n}/{len(gdf)} features...")

    if len(acc) == 0:
        raise RuntimeError("No DRN intersections found after filtering.")

    rows_out = []
    for (lay_i, row_i, col_i), vals in acc.items():
        total_len = vals["lengths"]
        avg_width = vals["wlen"] / total_len if total_len > 0 else default_width
        rows_out.append((lay_i, row_i, col_i, total_len, avg_width))

    dfDrn = pd.DataFrame(rows_out, columns=["lay", "row", "col", "lengths", "width_m"])

    before = len(dfDrn)
    dfDrn = dfDrn[dfDrn["lengths"] >= float(min_len)].copy()
    print(f"Drop cells with stream length < {min_len} m: {before} -> {len(dfDrn)}")

    if dfDrn.empty:
        raise RuntimeError("All DRN cells removed by min_len.")

    rr = dfDrn["row"].to_numpy(dtype=int)
    cc = dfDrn["col"].to_numpy(dtype=int)

    before = len(dfDrn)
    dfDrn = dfDrn[np.asarray(id2d)[rr, cc] == 1].copy()
    print(f"Keep only active cells: {before} -> {len(dfDrn)}")

    if dfDrn.empty:
        raise RuntimeError("No active DRN cells remain.")

    chd_set = set()
    chd_set |= build_cellid_set_from_df(dfChd)
    chd_set |= build_cellid_set_from_rec(chd_rec)

    dfDrn["cellids"] = list(zip(dfDrn["lay"].astype(int), dfDrn["row"].astype(int), dfDrn["col"].astype(int)))

    if len(chd_set) > 0:
        before = len(dfDrn)
        dfDrn = dfDrn[~dfDrn["cellids"].isin(chd_set)].copy()
        print(f"Remove DRN cells overlapping CHD: {before} -> {len(dfDrn)}")

    rr = dfDrn["row"].to_numpy(dtype=int)
    cc = dfDrn["col"].to_numpy(dtype=int)

    TOP = np.asarray(top2d, dtype=float)[rr, cc]
    BOT = np.asarray(botm3d, dtype=float)[lay, rr, cc]
    W = dfDrn["width_m"].to_numpy(dtype=float)
    L = dfDrn["lengths"].to_numpy(dtype=float)

    elev = np.maximum(BOT + 0.1, TOP - float(elev_offset))
    Kbed = np.full(len(dfDrn), float(bed_k), dtype=float)

    cond = Kbed * (W * L) / float(bed_thick)
    cond = cond * float(cond_mult)

    if cond_cap is not None:
        cond = np.minimum(cond, float(cond_cap))

    dfDrn["elev"] = np.nan_to_num(elev, nan=0.0, posinf=0.0, neginf=0.0)
    dfDrn["cond"] = np.nan_to_num(cond, nan=0.0, posinf=0.0, neginf=0.0)

    dfDrn = dfDrn[dfDrn["cond"] > 0].copy()

    drn_rec = [
        ((int(r.lay), int(r.row), int(r.col)), float(r.elev), float(r.cond))
        for r in dfDrn.itertuples(index=False)
    ]

    print("Final DRN records:", len(drn_rec))
    print("cond min/max:", float(dfDrn["cond"].min()), float(dfDrn["cond"].max()))

    return dfDrn, drn_rec


def build_drn_from_raster(
    drain_elev2d,
    drain_frac2d,
    idomain,
    top2d,
    botm3d,
    hk3d,
    delr,
    delc,
    k_divisor=1.0,
    cond_mult=1.0,
    min_thick=0.1,
    min_area_frac=0.01,
    elev_eps=0.01,
):
    recs = []
    rows = []

    nlay, nrow, ncol = idomain.shape

    ii, jj = np.where(np.isfinite(drain_elev2d) & (drain_frac2d >= min_area_frac))

    for i, j in zip(ii, jj):
        active_k = np.where(idomain[:, i, j] > 0)[0]
        if len(active_k) == 0:
            continue
        k = int(active_k[0])

        cell_top = float(top2d[i, j] if k == 0 else botm3d[k - 1, i, j])
        cell_bot = float(botm3d[k, i, j])
        cell_thick = max(cell_top - cell_bot, min_thick)

        elev = float(drain_elev2d[i, j])

        # keep drain elevation inside the cell
        if elev >= cell_top:
            elev = cell_top - elev_eps
        if elev <= cell_bot:
            continue
        # calculate the conductance based on the fraction of the cell area covered by the drain and the cell's hydraulic conductivity 
        area = float(delr[j] * delc[i] * drain_frac2d[i, j])
        if area <= 0:
            continue

        kcell = float(hk3d[k, i, j]) / k_divisor
        cond = float(kcell * area / cell_thick * cond_mult)

        if not np.isfinite(cond) or cond <= 0:
            continue

        rec = ((k, int(i), int(j)), elev, cond)
        recs.append(rec)

        rows.append({
            "lay": k,
            "row": int(i),
            "col": int(j),
            "elev": elev,
            "cond": cond,
            "area_m2": area,
            "area_frac": float(drain_frac2d[i, j]),
            "kcell": kcell,
            "cell_thick": cell_thick,
        })

    df = pd.DataFrame(rows)
    return df, recs


# build Lake mask function 
def build_full_lake_mask(path_lake_poly, template_tif):
    gdf = gpd.read_file(path_lake_poly)

    with rio.open(template_tif) as tmp:
        lake_mask = rasterize(
            [(geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty],
            out_shape=(tmp.height, tmp.width),
            transform=tmp.transform,
            fill=0,
            dtype="uint8",
            all_touched=False
        ).astype(bool)

    return lake_mask



def rec_list_to_bool_mask(rec_list, nrow, ncol):
    mask = np.zeros((nrow, ncol), dtype=bool)
    if rec_list is None:
        return mask
    for rec in rec_list:
        try:
            k, i, j = rec[0]
            mask[int(i), int(j)] = True
        except Exception:
            continue
    return mask

def ghb_df_to_bool_mask(df, nrow, ncol):
    mask = np.zeros((nrow, ncol), dtype=bool)
    if df is None or len(df) == 0:
        return mask
    for r in df.itertuples(index=False):
        mask[int(r.i), int(r.j)] = True
    return mask

# function for surface seepage cell 
#This function iterates over a MODFLOW “stress-period record list” and extracts all unique (i, j) index pairs from it. It returns these pairs as a set of 2-tuples of integers.
def rec_to_ij_set(rec_list):
    """Return a set of (i, j) pairs from a MODFLOW stress-period record list."""
    s = set()
    for rec in rec_list:
        try:
            k, i, j = rec[0]
            s.add((int(i), int(j)))
        except Exception:
            continue
    return s

def ghb_to_ij_set(df):
    """Return a set of (i, j) pairs from a GHB DataFrame with columns i and j."""
    s = set()
    for r in df.itertuples(index=False):
        s.add((int(r.i), int(r.j)))
    return s


# =============================================================================
# RUN CONFIGURATION EXPORT
# =============================================================================

def save_run_config(sim_ws, config_path=None):
    """
    Save a snapshot of config.py and a plain-text run summary into sim_ws.

    Two files are written:
      config_snapshot.py  -- verbatim copy of config.py (re-runnable)
      run_summary.txt     -- human-readable key-parameter table with timestamp

    Parameters
    ----------
    sim_ws      : str  path to the simulation workspace directory
    config_path : str  path to config.py; auto-detected from Helper.py location if None
    """
    import importlib.util, subprocess, datetime

    os.makedirs(sim_ws, exist_ok=True)

    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')

    if not os.path.exists(config_path):
        print(f'WARNING: config.py not found at {config_path} -- skipping snapshot.')
        return

    # 1. verbatim copy of config.py
    snapshot_py = os.path.join(sim_ws, 'config_snapshot.py')
    shutil.copy2(config_path, snapshot_py)

    # 2. load config values for the summary
    spec = importlib.util.spec_from_file_location('_cfg_snap', config_path)
    cfg  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)

    def g(attr):
        return getattr(cfg, attr, 'not set')

    # 3. git hash (best-effort)
    git_hash = 'unavailable'
    try:
        r = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True,
            cwd=os.path.dirname(config_path)
        )
        if r.returncode == 0:
            git_hash = r.stdout.strip()
    except Exception:
        pass

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sep = '=' * 60

    rows = [
        sep,
        '  MODFLOW 6 RUN CONFIGURATION SNAPSHOT',
        sep,
        f'  Timestamp       : {now}',
        f'  Git hash        : {git_hash}',
        f'  config.py       : {config_path}',
        '',
        '--- Model Identity ---',
        f'  nameSim         : {g("nameSim")}',
        f'  nameModel       : {g("nameModel")}',
        '',
        '--- Grid ---',
        f'  CELL            : {g("CELL")} m',
        f'  EPSG            : {g("EPSG")}',
        '',
        '--- Time ---',
        f'  START_DATE      : {g("START_DATE")}',
        f'  END_DATE        : {g("END_DATE")}',
        f'  NPER_TEST       : {g("NPER_TEST")}',
        '',
        '--- Layer Structure ---',
        f'  SOIL_THICKNESSES    : {g("SOIL_THICKNESSES")}',
        f'  FRAC_BEDROCK_THK_M  : {g("FRAC_BEDROCK_THK_M")} m',
        f'  MAX_DEPTH_M         : {g("MAX_DEPTH_M")} m',
        f'  MIN_QUAT_SUBLAYER_M : {g("MIN_QUAT_SUBLAYER_M")} m',
        f'  HK_LAYER_BAND_MAP   : {g("HK_LAYER_BAND_MAP")}',
        '',
        '--- Boundary Conditions ---',
        f'  USE_GHB         : {g("USE_GHB")}',
        f'  USE_DRN         : {g("USE_DRN")}',
        f'  USE_CHD         : {g("USE_CHD")}',
        f'  USE_WETLAND_DRN : {g("USE_WETLAND_DRN")}',
        '',
        '--- GHB Parameters ---',
        f'  GHB_BED_THICKNESS_M : {g("GHB_BED_THICKNESS_M")} m',
        f'  GHB_KV_DIVISOR      : {g("GHB_KV_DIVISOR")}',
        f'  GHB_COND_MULT       : {g("GHB_COND_MULT")}',
        f'  STAGE_CAP_OFFSET    : {g("STAGE_CAP_OFFSET")} m',
        '',
        '--- DRN / Seepage Parameters ---',
        f'  DRN_K_DIVISOR    : {g("DRN_K_DIVISOR")}',
        f'  DRN_COND_MULT    : {g("DRN_COND_MULT")}',
        f'  DRN_DEPTH_M      : {g("DRN_DEPTH_M")} m',
        f'  TSOIL_M          : {g("TSOIL_M")} m',
        f'  SURF_AREA_FRAC   : {g("SURF_AREA_FRAC")}',
        f'  SURF_ELEV_OFFSET : {g("SURF_ELEV_OFFSET")} m',
        '',
        '--- Hydraulic Properties ---',
        f'  KV_ANISOTROPY_RATIO : {g("KV_ANISOTROPY_RATIO")}',
        '',
        '--- Starting Heads ---',
        f'  TOP_BUFFER    : {g("TOP_BUFFER")} m',
        f'  MIN_ABOVE_BOT : {g("MIN_ABOVE_BOT")} m',
        f'  MIN_SAT_FRAC  : {g("MIN_SAT_FRAC")}',
        '',
        '--- Key Input Files ---',
        f'  nameInputTop       : {g("nameInputTop")}',
        f'  nameInputLayBot    : {g("nameInputLayBot")}',
        f'  nameInputHorizCond : {g("nameInputHorizCond")}',
        f'  nameInputStrt      : {g("nameInputStrt")}',
        f'  nameInputDrainElev : {g("nameInputDrainElev")}',
        f'  NLDAS_ROOT_PATH    : {g("NLDAS_ROOT_PATH")}',
        sep,
    ]

    summary_path = os.path.join(sim_ws, 'run_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows) + '\n')

    print(f'Config snapshot : {snapshot_py}')
    print(f'Run summary     : {summary_path}')
