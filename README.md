# Great Lakes Basin Groundwater Model

Regional transient MODFLOW 6 groundwater model for the extended Great Lakes Basin, built with [FloPy](https://github.com/modflowpy/flopy). The model simulates monthly groundwater dynamics from January 2000 to December 2025 at 1 km resolution, covering approximately 904,570 active cells across the full basin.

![Study domain](Figures/Studydomain.jpeg)

---

## Repository layout

```
GreatLakesProject/
├── flopysim/
│   ├── config.py                    ← single file to edit for all parameters
│   ├── settings.py                  ← re-exports config (kept for backwards compat)
│   ├── Imports.py                   ← all Python package imports
│   ├── Inputs.py                    ← input-processing helpers (grid, rasters, BCs)
│   ├── Helper.py                    ← core build helpers (recharge, drains, GHB, …)
│   ├── PlotHelper.py                ← plotting utilities
│   ├── Outputs.py                   ← output extraction helpers
│   ├── plot_conceptual_model.py     ← standalone conceptual model figure
│   ├── Modeflow6_SImulation.ipynb   ← main simulation notebook (build + run)
│   └── Modeflow6_OutputProcess.ipynb← post-processing and comparison notebook
└── Figures/
    └── Studydomain.jpeg
```

---

## Quickstart — changing parameters and running

**All calibration values, file paths, and switches live in one place:**

```
flopysim/config.py
```

Edit that file, then in the notebook run:

1. **`cfg-reload-01`** — reloads `config.py` into the active kernel session without a restart; prints key values so you can confirm they loaded correctly
2. **Drain-build cells** (reset → raster → seepage → cleanup) — rebuilds boundary-condition records with the new parameters
3. **Warm-up spin-up cell** — generates equilibrated starting heads
4. **Main model cell** — writes and runs the MODFLOW 6 simulation

> **Never edit `settings.py`, `Imports.py`, or `Inputs.py` directly.** They all import from `config.py`.

---

## Model overview

| Item | Value |
|------|-------|
| Simulator | MODFLOW 6 |
| Grid | 1 km × 1 km structured, EPSG 3174 (Great Lakes Basin Albers) |
| Domain | Extended Great Lakes Basin boundary |
| Active cells | ~904,570 (653,161 land + 251,409 GHB lake ring) |
| Layers | 5 (see geology below) |
| Stress periods | 312 monthly (Jan 2000 – Dec 2025) |
| Temporal unit | Days (all conductance, recharge in m²/day and m/day) |

---

## 5-layer geological structure

### Land cells
| Layer | Name | Top | Bottom |
|-------|------|-----|--------|
| 1 | Quaternary upper | DEM | (DEM + mid-Quat contact) / 2 |
| 2 | Quaternary middle | Contact 2 | Mid-Quat contact (Xu 2021) |
| 3 | Quaternary lower | Contact 3 | Bedrock surface (`modelbottom.tif`) |
| 4 | Fractured bedrock | Bedrock surface | Bedrock − 5 m (fixed) |
| 5 | Deep bedrock | Layer 4 bottom | −600 m ASL (fixed) |

### Lake cells (bathymetry override)
| Layer | Name | Top | Bottom |
|-------|------|-----|--------|
| 1 | Water column | Lake surface (DEM) | Lake floor (bathymetry) |
| 2–3 | Sub-lake Quaternary | Lake floor | Bedrock |
| 4–5 | Bedrock | Same as land | Same as land |

---

## Boundary conditions

### Recharge (RCHA)
- Source: **NLDAS-2 Noah-VIC monthly Qsb** (`BLEND_Qsb_A*.nc`)
- Variable: `Qsb` — total subsurface runoff (shallow interflow + deep drainage)
- Unit conversion: `Qsb [kg/m²/month] / 1000 / days_in_month → m/day`
- Applied fraction: `RCH_MULT = 0.65` (deep-drainage fraction that reaches the water table)
- Lake cells receive zero recharge

### General-Head Boundary — Great Lakes (GHB)
- Represents the five Great Lakes as time-varying head boundaries
- 251,409 cells in a ring inside each lake
- Monthly lake stages from observed gauge records
- Stage capped just below cell top to prevent unphysical inflow
- Conductance: `C = Kv × cell_area / GHB_BED_THICKNESS_M`, scaled by `GHB_COND_MULT = 0.5`

### Drain — stream network (DRN)
- Built from NHD stream raster (`drain_elevation.tif`) reprojected to model grid
- 605,018 cells covering all mapped stream/wetland reaches
- Drain elevation: land surface − `DRN_DEPTH_M` (0.5 m below surface)
- Conductance: `C = K × cell_area / DRN_K_DIVISOR`, capped at `DRN_COND_CAP = 1e5 m²/day`
- Isolated clusters smaller than `MIN_CLUSTER_SIZE = 3` cells are removed

### Drain — surface seepage (DRN)
- Represents saturation-excess runoff / seepage faces on all non-stream, non-lake land cells
- 47,904 cells (all active land cells not already covered by stream or GHB drains)
- Always placed in **Layer 1** (the phreatic/convertible layer) so the drain directly controls the water table
- Drain elevation: `DEM − SURF_ELEV_OFFSET` (2 m below surface), clamped within Layer 1 bounds
- Conductance: `C = K × cell_area / Layer1_thickness`, capped at `SURF_COND_CAP = 1e4 m²/day`
  - Physics basis: at peak spring recharge (~4,333 m³/day per 1 km² cell), equilibrium head = DEM − 1.57 m (DTW +1.6 m, never artesian)
- Cells with zero mean-annual recharge receive a weak drain (`SURF_COND_WEAK = 0.1 m²/day`)

---

## Hydraulic properties

| Property | Source | Notes |
|----------|--------|-------|
| Horizontal K (Kh) | `HK_5band_1000m.tif` | 5-band raster, one band per layer |
| Vertical K (Kv) | Derived | `Kv = Kh / KV_ANISOTROPY_RATIO` (ratio = 10, all layers) |
| Storage (Sy / Ss) | Default MF6 | Convertible cells (`icelltype = 1`) for Layer 1 |

---

## Solver settings

### Warm-up spin-up (24 monthly periods)
| Parameter | Value |
|-----------|-------|
| Complexity | SIMPLE |
| `outer_dvclose` | 5.0 m (loose — spin-up only needs approximate heads) |
| `outer_maximum` | 25 |
| `inner_maximum` | 30 |

### Main transient model
| Parameter | Value |
|-----------|-------|
| Complexity | MODERATE |
| `outer_dvclose` | 0.1 m |
| `inner_dvclose` | 0.01 m |
| `outer_maximum` | 200 |
| `inner_maximum` | 100 |
| Linear acceleration | BICGSTAB |
| Under-relaxation | DBD (θ = 0.9) |

---

## Simulation workflow

```
config.py
    │
    ├─▶ cfg-reload-01              # reload config into running kernel
    │
    ├─▶ Build grid & layers        # DEM, bathymetry, 5-layer geometry
    ├─▶ Build recharge (RCHA)      # NLDAS Qsb → m/day, RCH_MULT applied
    ├─▶ Build GHB                  # monthly lake stages, lakebed conductance
    ├─▶ Build stream DRN           # NHD raster, cluster filter
    ├─▶ Build surface seepage DRN  # Layer-1 forced, C = K·A/thick capped at 1e4
    ├─▶ Cleanup & sanity checks    # no duplicates, no DRN/GHB overlap, budget check
    │
    ├─▶ Warm-up spin-up (24 mo)   # SIMPLE IMS, produces ss_heads
    ├─▶ Clean ss_heads             # replace HDRY/HNOFLO, clip to cell bounds
    │
    └─▶ Main model (309 periods)   # MODERATE IMS, Jan 2000 – Dec 2025
            │
            └─▶ OutputProcess.ipynb
                    ├─▶ Depth-to-water-table maps (monthly / annual December)
                    ├─▶ Observed vs simulated head comparison
                    └─▶ Well hydrograph time series
```

---

## Key calibration parameters

All in `config.py` — change here, then re-run the reload cell and downstream cells:

| Parameter | Current value | What it controls |
|-----------|--------------|-----------------|
| `RCH_MULT` | 0.65 | Fraction of NLDAS Qsb applied as deep groundwater recharge |
| `GHB_COND_MULT` | 0.5 | Multiplier on GHB (lake) conductance |
| `DRN_COND_CAP` | 1e5 m²/day | Hard cap on stream drain conductance |
| `SURF_COND_CAP` | 1e4 m²/day | Hard cap on surface seepage drain conductance |
| `SURF_ELEV_OFFSET` | 2.0 m | Depth of surface seepage drain below land surface |
| `DRN_DEPTH_M` | 0.5 m | Depth of stream drain below land surface |
| `KV_ANISOTROPY_RATIO` | 10 | Kh/Kv ratio applied to all layers |

### Workflow for calibration runs
1. Edit parameter(s) in `config.py`
2. Bump `nameModel` (e.g., `Testing_14` → `Testing_15`) so outputs don't overwrite
3. Run `cfg-reload-01` in the notebook
4. Re-run drain-build cells and sanity check
5. Re-run warm-up spin-up
6. Re-run main model cell

---

## Inputs summary

| Input | Path | Description |
|-------|------|-------------|
| DEM | `model_Layers/DEM/DEM_extended20kmbdr_1000m.tif` | 1 km land surface elevation |
| Bedrock contact | `model_Layers/Bottom/modelbottom.tif` | Top of bedrock / base of Quaternary |
| Mid-Quat contact | `model_Layers/quaternary/mid_quat_contact_1000m.tif` | Middle Quaternary interface (Xu 2021) |
| Hydraulic conductivity | `model_Layers/HK/HK_5band_1000m.tif` | 5-band raster (one band per layer) |
| Lake bathymetry | `model_Layers/GreatLakes_bathymetry/…contours.tif` | Lake floor elevations |
| Starting heads | `model_Layers/Wells/starting_heads_clamped_1000m.tif` | Spin-up initial condition |
| Stream drain elevation | `model_Layers/Drains/drain_elevation.tif` | Pre-built drain raster from NHD |
| Domain mask | `model_Layers/Ibound/Idomain_mask_30m.tif` | Active cell mask |
| Recharge | `Data/Downloaded/Climatedata/Gridded/NLDAS_NOAHVIC_M.2.0/` | Monthly NetCDF files |
| Lake stages | `model_Layers/GHBs/GreatLakes_stage_monthly_for_model.csv` | Monthly observed stages |
| Observation wells | `GLB_water_wells.gdb` | GLB well water-level database |

---

## Outputs

All outputs are written to `MODEL_BASE_DIR / nameModel /`:

| Output | Description |
|--------|-------------|
| `Testing_14.hds` | Binary heads file (all layers, all periods) |
| `Testing_14.cbb` | Cell-by-cell budget file |
| `Observation_Comparison/` | Simulated vs observed head tables |
| `Figs/Testing_14/depthtowater_*.png` | Depth-to-water-table maps |
| `Figs/Testing_14/observed_vs_simulated_*.png` | Calibration scatter plots and hydrographs |

---

## Environment

```
Python       ≥ 3.10
flopy        ≥ 3.7
numpy
pandas
geopandas
rasterio
matplotlib
netCDF4 / xarray   (for NLDAS reading)
MODFLOW 6    (exe in MF6_EXE_DIR)
```

Install dependencies:
```bash
conda create -n glb_gw python=3.11
conda activate glb_gw
conda install -c conda-forge flopy geopandas rasterio netcdf4 xarray jupyter
```
