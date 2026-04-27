from pathlib import Path
from settings import *

# --- MF6 executable ---
bindir = Path(r"D:\Users\abolmaal\modelling\Modflow\helper")
exe_path = str((bindir / "mf6.exe").resolve())

# --- Simulation workspace (will be RECREATED) ---
dirModelFilesBase = r"D:\Users\abolmaal\modelling\Modflow"
sim_ws = str(Path(dirModelFilesBase) / nameModel)

# --- Boundary polygon (truth) ---
boundary_shp = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Ibound\extended_Bdry_final_GLB_Albers_exported.shp"

IBOUND = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Ibound\Idomain_mask_30m.tif"
# --- Raw rasters (any CRS/resolution; we will warp to template) ---
nameInputTop       = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\DEM\DEM_extended20kmbdr_1000m.tif"

nameInputLayBot    = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Bottom\modelbottom.tif"

nameInputHorizCond = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\HK\HK_5band_1000m.tif"


# this is the actual starting head raster
nameInputStrt     = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Wells\starting_heads_clamped_1000m.tif"

#this is your lake/land mask, NOT starting heads
#nameInputMask   = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Costantheads\domain_water_mask_30m_buff2000m.tif"

# --- CHD / DRN vector inputs ---
pathInputConstHead      = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Costantheads\CHD_cells_points_dem.shp"
fieldInputConstHeadElev = "head"

# -- GHB ---
OUT_GHB_TABLE = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes_GHB_cells.csv"
OUT_STAGE_TABLE = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes_stage_monthly_for_model.csv"

#LAKES_SHP = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes.shp"
pathLakePoly = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes.shp"

# --- NLDAS monthly Noah (NetCDF) ---
nldas_root = Path(r"D:\Users\abolmaal\Data\Downloaded\Climatedata\Gridded\NLDAS_NOAHVIC_M.2.0")
NLDAS_VAR  = "Qsb"

# --- Outputs (template + warped rasters) ---
GRID_DIR    = Path(r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\GRID_3174")
ALIGNED_DIR = Path(r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\ALIGNED_3174")
GRID_DIR.mkdir(parents=True, exist_ok=True)
ALIGNED_DIR.mkdir(parents=True, exist_ok=True)

template_tif = str(GRID_DIR / f"template_{CELL}m_epsg{EPSG}.tif")
idomain_tif  = str(GRID_DIR / f"idomain_{CELL}m_epsg{EPSG}.tif")

top_aligned   = str(ALIGNED_DIR / f"TOP_{CELL}m.tif")
botm_aligned  = str(ALIGNED_DIR / f"BOTM_{CELL}m.tif")
hk_aligned    = str(ALIGNED_DIR / f"HK_{CELL}m.tif")
mask_aligned  = str(ALIGNED_DIR / f"MASK_{CELL}m.tif")
strt_aligned  = str(ALIGNED_DIR / f"STRT_{CELL}m.tif")
Ibound_aligned = str(ALIGNED_DIR / f"IBOUND_{CELL}m.tif")

# --- Streams source for DRN build ---
gdb_path = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\NHD\streams_tmp.gdb"
pathInputGHBFeature = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes_buffer10km.shp"

layer_name = "streams_3174"   # change if your FileGDB layer name differs
# Figure_dir
fig_dir = r"D:\Users\abolmaal\modelling\Figs\testing6"

# --- Water-wells geodatabase (observation comparison) ---
wells_gdb_path = r"S:\Data\GIS_Data\Derived\Great_Lakes_Basin\Watersheds\Water_Wells\GLB_water_wells.gdb"