"""
Configuration module for ERA5-Land Web GIS.
Defines variables metadata, unit conventions, color palettes, and server settings.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Data path: check backend/data/ERA5-Land.nc or root ERA5-Land.nc
DEFAULT_DATA_PATH = BASE_DIR / "data" / "ERA5-Land.nc"
if not DEFAULT_DATA_PATH.exists():
    FALLBACK_PATH = PROJECT_ROOT / "ERA5-Land.nc"
    if FALLBACK_PATH.exists():
        DEFAULT_DATA_PATH = FALLBACK_PATH

DATA_PATH = os.environ.get("ERA5_DATA_PATH", str(DEFAULT_DATA_PATH))

# Template and static paths
TEMPLATE_DIR = os.environ.get("TEMPLATE_DIR", str(PROJECT_ROOT / "app" / "templates"))
STATIC_DIR = os.environ.get("STATIC_DIR", str(PROJECT_ROOT / "app" / "static"))

# Chunking settings for lazy loading (auto adapts to dataset dimensions)
CHUNKS = "auto"

# Variable metadata
VARIABLES = {
    "t2m": {
        "id": "t2m",
        "name": "Temperature 2 metre",
        "unit": "°C",
        "source_unit": "K",
        "category": "temperature",
        "description": "Temperature of air at 2m above the surface of land, sea or in-land waters.",
        "aggregation": "mean",
        "colormap": "RdYlBu_r",
        "default_min": 15.0,
        "default_max": 35.0,
    },
    "d2m": {
        "id": "d2m",
        "name": "Dewpoint temperature",
        "unit": "°C",
        "source_unit": "K",
        "category": "temperature",
        "description": "Temperature to which the air, at 2 metres above the surface, must be cooled to become saturated with water vapour.",
        "aggregation": "mean",
        "colormap": "YlGnBu",
        "default_min": 15.0,
        "default_max": 28.0,
    },
    "tp": {
        "id": "tp",
        "name": "Total precipitation",
        "unit": "mm",
        "source_unit": "m",
        "category": "precipitation",
        "description": "Accumulated liquid and frozen water comprising rain and snow that falls to Earth's surface.",
        "aggregation": "sum",
        "colormap": "Blues",
        "default_min": 0.0,
        "default_max": 30.0,
    },
    "pev": {
        "id": "pev",
        "name": "Potential evaporation",
        "unit": "mm",
        "source_unit": "m",
        "category": "hydrology",
        "description": "Evaporation that would take place if there were an unlimited supply of water.",
        "aggregation": "sum",
        "colormap": "YlOrRd",
        "default_min": -30.0,
        "default_max": 0.0,
    },
    "ro": {
        "id": "ro",
        "name": "Runoff",
        "unit": "mm",
        "source_unit": "m",
        "category": "hydrology",
        "description": "Volume of water that runs off into rivers and streams.",
        "aggregation": "sum",
        "colormap": "PuBu",
        "default_min": 0.0,
        "default_max": 15.0,
    },
    "sp": {
        "id": "sp",
        "name": "Surface pressure",
        "unit": "hPa",
        "source_unit": "Pa",
        "category": "pressure",
        "description": "Pressure (force per unit area) of the atmosphere on the surface of land.",
        "aggregation": "mean",
        "colormap": "coolwarm",
        "default_min": 850.0,
        "default_max": 1015.0,
    },
    "swvl1": {
        "id": "swvl1",
        "name": "Soil moisture layer 1 (0-7 cm)",
        "unit": "m³/m³",
        "source_unit": "m³/m³",
        "category": "soil",
        "description": "Volume of water in soil layer 1 (0-7 cm depth).",
        "aggregation": "mean",
        "colormap": "YlGn",
        "default_min": 0.15,
        "default_max": 0.55,
    },
    "swvl2": {
        "id": "swvl2",
        "name": "Soil moisture layer 2 (7-28 cm)",
        "unit": "m³/m³",
        "source_unit": "m³/m³",
        "category": "soil",
        "description": "Volume of water in soil layer 2 (7-28 cm depth).",
        "aggregation": "mean",
        "colormap": "YlGn",
        "default_min": 0.15,
        "default_max": 0.55,
    },
    "swvl3": {
        "id": "swvl3",
        "name": "Soil moisture layer 3 (28-100 cm)",
        "unit": "m³/m³",
        "source_unit": "m³/m³",
        "category": "soil",
        "description": "Volume of water in soil layer 3 (28-100 cm depth).",
        "aggregation": "mean",
        "colormap": "YlGn",
        "default_min": 0.15,
        "default_max": 0.55,
    },
    "swvl4": {
        "id": "swvl4",
        "name": "Soil moisture layer 4 (100-289 cm)",
        "unit": "m³/m³",
        "source_unit": "m³/m³",
        "category": "soil",
        "description": "Volume of water in soil layer 4 (100-289 cm depth).",
        "aggregation": "mean",
        "colormap": "YlGn",
        "default_min": 0.20,
        "default_max": 0.55,
    },
    "u10": {
        "id": "u10",
        "name": "10 metre U wind component",
        "unit": "m/s",
        "source_unit": "m/s",
        "category": "wind",
        "description": "Eastward component of the 10-metre wind speed.",
        "aggregation": "mean",
        "colormap": "coolwarm",
        "default_min": -5.0,
        "default_max": 5.0,
    },
    "v10": {
        "id": "v10",
        "name": "10 metre V wind component",
        "unit": "m/s",
        "source_unit": "m/s",
        "category": "wind",
        "description": "Northward component of the 10-metre wind speed.",
        "aggregation": "mean",
        "colormap": "coolwarm",
        "default_min": -5.0,
        "default_max": 5.0,
    },
    "wind_speed": {
        "id": "wind_speed",
        "name": "10 metre Wind Speed",
        "unit": "m/s",
        "source_unit": "m/s",
        "category": "wind",
        "description": "Horizontal wind speed magnitude calculated from U and V components.",
        "aggregation": "mean",
        "colormap": "viridis",
        "default_min": 0.0,
        "default_max": 10.0,
    },
}

# Color Scales definition
COLOR_SCALES = {
    var_id: {
        "min": var_info["default_min"],
        "max": var_info["default_max"],
        "colormap": var_info["colormap"],
        "unit": var_info["unit"],
    }
    for var_id, var_info in VARIABLES.items()
}

# Bounding box constraints for validation
BOUNDS = {
    "lat_min": -2.7,
    "lat_max": 6.2,
    "lon_min": 93.7,
    "lon_max": 102.3,
}

# Maximum allowed bbox extent (degrees) for security
MAX_BBOX_SPAN = 20.0
