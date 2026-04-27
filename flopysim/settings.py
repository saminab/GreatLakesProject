# --- Model identity ---
nameSim   = "Greatlakes"
nameModel = "Testing_6"  # MF6 model name; package files will be Testing.dis, Testing.rch, etc.

# --- Model grid ---
CELL = 1000    # cell size in metres (1 km grid)
EPSG = 3174    # Great Lakes Basin Albers projection
# pathInputDrn = r"D:\Users\abolmaal\modelling\Modflow\Prep\GreatLakes\model_Layers\NHD\streams_3174_clip_to_modelgrid.shp"
# fieldInputDrnWidth = "WIDTH_M"
USE_DRN = True
USE_WETLAND_DRN = False   # separate wetland DRN no longer needed
DRN_K_DIVISOR = 1.0       # use 1.0 if you want exactly Kcell
# DRN_K_DIVISOR = 10.0    # use this instead if you want Kcell/10 for vertical leakage

DRN_MIN_THICK = 0.1       # minimum cell thickness used in conductance
DRN_MIN_AREA_FRAC = 0.01  # skip tiny drain fractions
DRN_COND_MULT = 1.0
DRN_ELEV_EPS = 0.01       # keep drain elevation slightly inside the cell

# --- Time controls ---
START_DATE = "2020-01-01"
END_DATE   = "2023-12-01"

NPER_TEST =13          # set None for full run
USE_FIVE_LAYER_MODEL = False   # replaced by 8-layer geological structure below

# --- 8-layer geological structure ---
# Layer 1–3: Soil (fixed thicknesses)
# Layer 4–6: Quaternary (3 equal sub-layers, variable thickness)
# Layer 7:   Fractured bedrock (fixed)
# Layer 8:   Deep bedrock (variable, to MAX_DEPTH_M)
SOIL_THICKNESSES     = [0.25, 0.25, 0.50]  # m; cumulative = 1.0 m
FRAC_BEDROCK_THK_M   = 5.0                 # m; fixed fractured-bedrock layer
MAX_DEPTH_M          = 600.0               # m below land surface; base of deep bedrock
MIN_QUAT_SUBLAYER_M  = 2.0                 # m; minimum thickness per Quaternary sub-layer
# HK band index assigned to each of the 8 model layers (0-based, from hk_raw)
# bands: 0=surficial  1-3=Quaternary  4=bedrock
HK_LAYER_BAND_MAP    = [0, 0, 0, 1, 2, 3, 3, 4]
FORCE_CONSTANT_CHD = False
LAKE_STAGE = 100.0
USE_GHB = True
USE_DRN = True
## Starting heads controls
TOP_BUFFER = 0.5               # keep heads slightly below land surface
MIN_ABOVE_BOT = 2.0            # minimum head above cell bottom
MIN_SAT_FRAC = 0.30            # at least 30% of layer thickness above bottom


# conductance assumptions
GHB_BED_THICKNESS_M = 1.0
GHB_KV_DIVISOR = 10.0

# DRN assumptions
DRN_DEPTH_M = 0.5   # drain stage 0.5 m below land surface

# surface Seppage assumptions
# SURFACE SEEPAGE FACES (horizontal surface drains)
# Eq. 13: Csurf = K * Ac / Tsoil
TSOIL_M          = 50.0    # soil thickness (m) — calibration parameter
SURF_AREA_FRAC   = 0.001   # fraction of cell area for seepage paths
SURF_COND_CAP    = 1e6     # m²/day hard cap on conductance
SURF_ELEV_OFFSET = 5.0    # drain sits 5 m below land surface
SURF_DRN_LAY     = 0       # always top layer
# Minimum recharge threshold to qualify for a surface drain
# Cells below this have no recharge source and must not have a drain
# 1e-6 m/day = ~0.37 mm/yr — effectively zero

MIN_RECHARGE_MDAY = 0.0   # below this = weak drain zone
SURF_COND_WEAK    = 0.1   # m²/day — prevents artesian, won't drain aquifer

# --- CHD flag ---
USE_CHD = False

# --- Vertical anisotropy ---
KV_ANISOTROPY_RATIO = 10.0    # Kv = Kh / KV_ANISOTROPY_RATIO for all layers

# --- Drain cluster filter ---
MIN_CLUSTER_SIZE = 3          # remove isolated stream/wetland drain groups smaller than this

# --- Plot classes ---
N_CLASSES = 15                # number of quantile classes for HK colormap

# --- Output plot settings ---
SCALEBAR_KM = 100             # scale bar length in km for output maps
N_SHOW_MAX  = 6               # max number of stress-period maps to show in one figure

# --- Unit conversion ---
FT_TO_M = 0.3048              # feet to metres

# --- Well observation layer ---
WELL_LAYER = "GLB_all_wells_2025_mi_update"   # layer name inside the wells GDB