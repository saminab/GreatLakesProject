# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
# This is the single file to edit when changing model parameters, paths, or
# calibration values.  All other Python files (settings.py, Inputs.py) import
# from here — you never need to touch them directly.
# =============================================================================
import os


# ---------------------------------------------------------------------------
# MODEL IDENTITY
# ---------------------------------------------------------------------------
nameSim   = "Greatlakes"
nameModel    = "Testing_13"       # used for MF6 package names and the sim folder
nameModel_SS = "Testing_13_SS"   # steady-state spin-up model (heads become STRT for transient)

# ---------------------------------------------------------------------------
# MODEL GRID
# ---------------------------------------------------------------------------
CELL = 1000                    # cell size in metres
EPSG = 3174                    # Great Lakes Basin Albers projection


# ---------------------------------------------------------------------------
# SIMULATION TIME
# ---------------------------------------------------------------------------
START_DATE = "2000-01-01"      # first stress period (monthly)
END_DATE   = "2025-12-01"      # last stress period (inclusive)
NPER_TEST  = 36              # number of periods for a short test run; set None for full run


# ---------------------------------------------------------------------------
# FILE PATHS — EXECUTABLES AND WORKSPACE
# ---------------------------------------------------------------------------
MF6_EXE_DIR      = r"D:\Users\abolmaal\modelling\Modflow\helper"
MODEL_BASE_DIR    = r"D:\Users\abolmaal\modelling\Modflow"     # sim_ws = MODEL_BASE_DIR / nameModel
FIGS_BASE_DIR     = r"D:\Users\abolmaal\modelling\Figs"        # fig_dir = FIGS_BASE_DIR / nameModel


# ---------------------------------------------------------------------------
# FILE PATHS — GRID AND DOMAIN
# ---------------------------------------------------------------------------
GRID_DIR_PATH    = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\GRID_3174"
ALIGNED_DIR_PATH = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\ALIGNED_3174"

boundary_shp     = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Ibound\extended_Bdry_final_GLB_Albers_exported.shp"
IBOUND           = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Ibound\Idomain_mask_30m.tif"


# ---------------------------------------------------------------------------
# FILE PATHS — INPUT RASTERS
# ---------------------------------------------------------------------------
nameInputTop        = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\DEM\DEM_extended20kmbdr_1000m.tif"
nameInputLayBot     = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Bottom\modelbottom.tif"
nameInputMidQuat    = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\quaternary\mid_quat_contact_1000m.tif"
nameInputHorizCond  = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\HK\HK_5band_1000m.tif"
nameInputStrt       = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Wells\starting_heads_clamped_1000m.tif"
nameInputDrainElev  = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Drains\drain_elevation.tif"
nameInputBathy      = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\GreatLakes_bathymetry\GreatLakes_bathymetry_contours.tif"


# ---------------------------------------------------------------------------
# FILE PATHS — VECTOR INPUTS
# ---------------------------------------------------------------------------
pathLakePoly        = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes.shp"
pathInputGHBFeature = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Lakes\GreatLakes_GHB_fullLake.shp"
pathInputConstHead  = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Costantheads\CHD_cells_points_dem.shp"
fieldInputConstHeadElev = "head"
gdb_path            = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\NHD\streams_tmp.gdb"
layer_name          = "streams_3174"
lake_name_field     = "lake_name"


# ---------------------------------------------------------------------------
# FILE PATHS — GHB TABLES
# ---------------------------------------------------------------------------
OUT_GHB_TABLE   = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\GHBs\GreatLakes_GHB_cells.csv"
OUT_STAGE_TABLE = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\GHBs\GreatLakes_stage_monthly_for_model.csv"


# ---------------------------------------------------------------------------
# FILE PATHS — CLIMATE (NLDAS)
# ---------------------------------------------------------------------------
NLDAS_ROOT_PATH  = r"D:\Users\abolmaal\Data\Downloaded\Climatedata\Gridded\NLDAS_NOAHVIC_M.2.0"
NLDAS_VAR        = "Qsb"
# Fraction of NLDAS Qsb applied as groundwater recharge.
# Qsb = total subsurface runoff (shallow interflow + deep drainage combined).
# Only the deep-drainage fraction reaches the water table; the rest becomes
# baseflow at shallow depth.  Typical values: 0.3–0.6.
RCH_MULT         = 0.65                   # calibration multiplier on recharge


# ---------------------------------------------------------------------------
# FILE PATHS — OBSERVATION WELLS
# ---------------------------------------------------------------------------
wells_gdb_path  = r"S:\Data\GIS_Data\Derived\Great_Lakes_Basin\Watersheds\Water_Wells\GLB_water_wells.gdb"
WELL_LAYER      = "GLB_all_wells_2025_mi_update"


# ---------------------------------------------------------------------------
# FILE PATHS — FIGURES  (derived from nameModel; folder created automatically)
# ---------------------------------------------------------------------------
fig_dir          = os.path.join(FIGS_BASE_DIR, nameModel)
out_fig_ts       = os.path.join(fig_dir, "depthtowatertable.png")
out_fig_maps     = os.path.join(fig_dir, "depthtowater_maps_blue_classes.png")
out_fig_final    = os.path.join(fig_dir, "depthtowater_final_blue_classes.png")


# ---------------------------------------------------------------------------
# FILE PATHS — OUTPUT TABLES  (derived from nameModel; folder created automatically)
# ---------------------------------------------------------------------------
obs_out_dir     = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\Observations"
compare_out_dir = os.path.join(MODEL_BASE_DIR, nameModel, "Observation_Comparison")
out_obs_csv     = os.path.join(obs_out_dir, "GLB_well_observations_for_MODFLOW.csv")
out_compare_csv = os.path.join(fig_dir, "well_observed_vs_simulated_heads.csv")
out_compare_fig = os.path.join(fig_dir, "observed_vs_simulated_heads.png")
out_dtw_fig     = os.path.join(fig_dir, "observed_vs_simulated_dtw.png")

# Create model-specific output directories when config is imported
os.makedirs(os.path.join(MODEL_BASE_DIR, nameModel), exist_ok=True)
os.makedirs(os.path.join(MODEL_BASE_DIR, nameModel_SS), exist_ok=True)
os.makedirs(fig_dir, exist_ok=True)
os.makedirs(compare_out_dir, exist_ok=True)
os.makedirs(obs_out_dir, exist_ok=True)


# ---------------------------------------------------------------------------
# 5-LAYER GEOLOGICAL STRUCTURE  (no soil layers)
# ---------------------------------------------------------------------------
# Land cells:
#   Layer 1: Quaternary 1     top=DEM,       bottom=Contact2=(DEM+mid_quat)/2
#   Layer 2: Quaternary 2     top=Contact2,  bottom=Contact3=mid_quat contact (Xu 2021)
#   Layer 3: Quaternary 3     top=Contact3,  bottom=Contact4=bedrock (modelbottom.tif)
#   Layer 4: Fractured bedrock top=Contact4, bottom=Contact4 - 5 m    (fixed)
#   Layer 5: Deep bedrock      top=Layer4 bot, bottom=Contact6=-600 m ASL (fixed)
#
# Lake cells (bathymetry override):
#   Layer 1: Lake water column top=DEM,       bottom=lake floor
#   Layer 2: Quaternary 1     top=lake floor, bottom=(floor+bedrock)/2
#   Layer 3: Quaternary 2     top=above,      bottom=bedrock
#   Layer 4: Fractured bedrock (same as land)
#   Layer 5: Deep bedrock      (same as land)
#
# modelbottom.tif  = bedrock contact (top of bedrock / bottom of Quaternary)
# nameInputMidQuat = bottom of middle Quaternary contact (Xu 2021)
FRAC_BEDROCK_THK_M  = 5.0                  # m; fixed fractured-bedrock thickness
MAX_DEPTH_M         = 600.0                # base of deep bedrock = -MAX_DEPTH_M m ASL (fixed absolute elevation)
MIN_QUAT_SUBLAYER_M = 1.0                  # m; minimum thickness per Quaternary sub-layer

# HK raster band number (1-based, matching the raster file) for each model layer
# hk_raw bands: 1=Quat-1  2=Quat-2  3=Quat-3  4=fractured bedrock  5=deep bedrock
HK_LAYER_BAND_MAP   = [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# BOUNDARY CONDITION SWITCHES
# ---------------------------------------------------------------------------
USE_GHB           = True
USE_DRN           = True
USE_WETLAND_DRN   = False
USE_CHD           = False
FORCE_CONSTANT_CHD = False
LAKE_STAGE        = 100.0                  # fallback lake stage (m) if table missing


# ---------------------------------------------------------------------------
# GHB (General-Head Boundary — Great Lakes)
# ---------------------------------------------------------------------------
GHB_BED_THICKNESS_M = 1.0                 # lakebed sediment thickness (m)
GHB_KV_DIVISOR      = 10.0               # Kv = Kh / GHB_KV_DIVISOR for lakebed
GHB_COND_MULT       = 0.5                 # calibration multiplier on GHB conductance
STAGE_CAP_OFFSET    = 0.10               # m; stage is capped this far below cell top


# ---------------------------------------------------------------------------
# DRN (Drain — streams and surface seepage)
# ---------------------------------------------------------------------------
DRN_K_DIVISOR    = 1.0                    # drain conductance = K_cell / DRN_K_DIVISOR
DRN_MIN_THICK    = 0.1                    # m; minimum cell thickness for conductance
DRN_MIN_AREA_FRAC = 0.01                  # skip drain cells below this area fraction
DRN_COND_MULT    = 1.0                    # calibration multiplier on drain conductance
DRN_ELEV_EPS     = 0.01                   # m; drain elevation offset below cell top
DRN_DEPTH_M      = 0.5                    # m; stream drain stage below land surface
DRN_COND_CAP     = 1e5                    # m²/day; hard cap on stream drain conductance
#   Rationale: K × (1 km²) / DRN_K_DIVISOR can reach 1e8 for high-K cells,
#   which causes ILU overflow in the IMS solver.  A 1 km cell with 10 m/day K
#   and ~100 m of stream length has C ≈ K × stream_area / bed_thickness
#   ≈ 10 × 1e4 / 0.5 ≈ 2e5 m²/day, so 1e5 is physically conservative.

# Surface seepage drains (horizontal seepage faces)
# Conductance: C = K * cell_area / Layer1_thickness   (Darcy through near-surface soil)
#   K            = horizontal K of Layer 1 at each cell  [m/day]
#   cell_area    = delr * delc = 1e6 m² at 1 km resolution
#   Layer1_thick = top2d - botm3d[0]  (varies spatially)
# SURF_AREA_FRAC and TSOIL_M are retained below for reference but are no
# longer used in the conductance calculation (superseded by layer thickness).
TSOIL_M           = 50.0                  # m; kept for reference — not used in conductance
SURF_AREA_FRAC    = 0.01                  # kept for reference — not used in conductance
SURF_COND_CAP     = 1e3                   # m²/day; hard cap on surface drain conductance
# Note: C = K * 1km² / thick easily reaches 1e6-1e8 m²/day.
# The cap is the effective conductance for most cells and controls
# solver stiffness — 1e3 m²/day gives head above drain ~ 0.4-1 m,
# keeping water table ~4-5 m below surface without solver oscillation.
SURF_ELEV_OFFSET  = 2.0                   # m; seepage drain sits this far below surface
SURF_DRN_LAY      = 0                     # model layer index for surface drains (0 = top)
MIN_RECHARGE_MDAY = 0.0                   # m/day; cells below this get weak drain only
SURF_COND_WEAK    = 0.1                   # m²/day; weak drain for low-recharge cells

MIN_CLUSTER_SIZE  = 3                     # remove isolated drain clusters smaller than this


# ---------------------------------------------------------------------------
# STARTING HEADS
# ---------------------------------------------------------------------------
TOP_BUFFER   = 0.5                        # m; head kept this far below land surface
MIN_ABOVE_BOT = 2.0                       # m; minimum head above cell bottom
MIN_SAT_FRAC  = 0.30                      # fraction of layer thickness that must be saturated


# ---------------------------------------------------------------------------
# HYDRAULIC PROPERTIES
# ---------------------------------------------------------------------------
KV_ANISOTROPY_RATIO = 10.0               # Kv = Kh / KV_ANISOTROPY_RATIO (all layers)


# ---------------------------------------------------------------------------
# PLOT AND OUTPUT SETTINGS
# ---------------------------------------------------------------------------
N_CLASSES    = 15                         # quantile classes for HK colormap
SCALEBAR_KM  = 100                        # scale bar length in km
N_SHOW_MAX   = 6                          # max stress-period maps per figure


# ---------------------------------------------------------------------------
# UNIT CONVERSION
# ---------------------------------------------------------------------------
FT_TO_M = 0.3048                          # feet to metres


# ---------------------------------------------------------------------------
# DIRECT EXECUTION
# ---------------------------------------------------------------------------
# Run the full MODFLOW 6 simulation without opening Jupyter:
#
#   python config.py
#
# The simulation notebook (Modeflow6_SImulation.ipynb) is executed in a
# fresh kernel.  Its Cell 0 imports from this file, so every change you
# make here is picked up automatically — no notebook edits needed.
#
# An executed copy of the notebook is saved alongside the original so you
# keep a record of the run with all cell outputs.
# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     import subprocess, sys, os, datetime

#     here     = os.path.dirname(os.path.abspath(__file__))
#     notebook = os.path.join(here, "Modeflow6_SImulation.ipynb")

#     if not os.path.exists(notebook):
#         print(f"ERROR: notebook not found: {notebook}")
#         sys.exit(1)

#     # timestamped output copy so each run is preserved
#     stamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#     out_nb   = os.path.join(here, f"Modeflow6_SImulation_run_{stamp}.ipynb")

#     print("=" * 60)
#     print("  Running MODFLOW 6 simulation")
#     print(f"  nameModel  : {nameModel}")
#     print(f"  START_DATE : {START_DATE}")
#     print(f"  END_DATE   : {END_DATE}")
#     print(f"  NPER_TEST  : {NPER_TEST}")
#     print(f"  notebook   : {notebook}")
#     print(f"  output nb  : {out_nb}")
#     print("=" * 60)

#     result = subprocess.run(
#         [
#             sys.executable, "-m", "jupyter", "nbconvert",
#             "--to", "notebook",
#             "--execute",
#             "--ExecutePreprocessor.timeout=86400",   # 24-hour ceiling
#             "--ExecutePreprocessor.kernel_name=python3",
#             "--output", out_nb,
#             notebook,
#         ]
#     )

#     if result.returncode == 0:
#         print(f"\nSimulation complete.  Executed notebook saved to:\n  {out_nb}")
#     else:
#         print(f"\nSimulation FAILED (exit code {result.returncode}).")
#         sys.exit(result.returncode)
