# All the Imports 
import os
import gc
import time
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"  # helps reading NetCDF/HDF5 from network drives on Windows
# remove conflicting PROJ environment variables
os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

print("PROJ_LIB =", os.environ.get("PROJ_LIB"))
print("PROJ_DATA =", os.environ.get("PROJ_DATA"))
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pyogrio")
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pathlib import Path
import re, glob, shutil, tempfile, calendar

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio as rio
from rasterio.transform import from_origin, from_bounds
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
import shapely.geos
from shapely.geometry import MultiLineString
import matplotlib.pyplot as plt
import matplotlib as mpl
from rasterio.crs import CRS
import flopy
from flopy.utils.gridintersect import GridIntersect
from affine import Affine
import xarray as xr
import geopandas as gpd
import rasterio as rio
import fiona
from scipy.ndimage import label

print(f"numpy version: {np.__version__}")
print(f"matplotlib version: {mpl.__version__}")
print(f"flopy version: {flopy.__version__}")
