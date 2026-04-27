from pathlib import Path
from config import *

# ---------------------------------------------------------------------------
# DERIVED PATHS  (computed from config values — do not edit here)
# ---------------------------------------------------------------------------
bindir   = Path(MF6_EXE_DIR)
exe_path = str((bindir / "mf6.exe").resolve())

sim_ws = str(Path(MODEL_BASE_DIR) / nameModel)

GRID_DIR    = Path(GRID_DIR_PATH)
ALIGNED_DIR = Path(ALIGNED_DIR_PATH)
GRID_DIR.mkdir(parents=True, exist_ok=True)
ALIGNED_DIR.mkdir(parents=True, exist_ok=True)

nldas_root = Path(NLDAS_ROOT_PATH)

template_tif     = str(GRID_DIR    / f"template_{CELL}m_epsg{EPSG}.tif")
idomain_tif      = str(GRID_DIR    / f"idomain_{CELL}m_epsg{EPSG}.tif")

top_aligned        = str(ALIGNED_DIR / f"TOP_{CELL}m.tif")
botm_aligned       = str(ALIGNED_DIR / f"BOTM_{CELL}m.tif")
hk_aligned         = str(ALIGNED_DIR / f"HK_{CELL}m.tif")
mask_aligned       = str(ALIGNED_DIR / f"MASK_{CELL}m.tif")
strt_aligned       = str(ALIGNED_DIR / f"STRT_{CELL}m.tif")
Ibound_aligned     = str(ALIGNED_DIR / f"IBOUND_{CELL}m.tif")
drain_elev_aligned = str(ALIGNED_DIR / f"DRAIN_ELEV_{CELL}m.tif")
drain_frac_aligned = str(ALIGNED_DIR / f"DRAIN_FRAC_{CELL}m.tif")
