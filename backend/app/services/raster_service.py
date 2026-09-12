"""
Raster Service.
Renders ERA5-Land spatial grids into transparent georeferenced RGBA PNG overlays,
provides color scales, legend gradient hex stops, and bounds for Leaflet ImageOverlay.
"""

import io
from typing import Any, Dict, List, Optional, Tuple
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
from PIL import Image

from app.config import COLOR_SCALES, VARIABLES
from app.services.netcdf_service import get_raster_slice

# In-memory image cache: {cache_key: (png_bytes, bounds, meta)}
_IMAGE_CACHE: Dict[str, Tuple[bytes, List[List[float]], Dict[str, Any]]] = {}
_MAX_CACHE_ENTRIES = 128


import matplotlib as mpl


def get_colormap(colormap_name: str):
    """Retrieve matplotlib colormap safely with fallback."""
    try:
        return mpl.colormaps[colormap_name]
    except Exception:
        return mpl.colormaps["viridis"]


def generate_legend_info(variable_id: str, vmin: float, vmax: float, steps: int = 5) -> Dict[str, Any]:
    """
    Generate gradient color stops and legend tick marks for the frontend legend.
    """
    scale_cfg = COLOR_SCALES.get(variable_id, {})
    cmap_name = scale_cfg.get("colormap", "viridis")
    cmap = get_colormap(cmap_name)

    # 10 color sample stops for the CSS linear-gradient
    gradient_stops = []
    for frac in np.linspace(0, 1, 11):
        rgba = cmap(frac)
        hex_color = mcolors.to_hex(rgba)
        gradient_stops.append({"position": round(frac * 100, 1), "color": hex_color})

    # Numeric tick marks
    ticks = []
    tick_values = np.linspace(vmin, vmax, steps)
    for val in tick_values:
        ticks.append(round(float(val), 2))

    return {
        "variable": variable_id,
        "name": VARIABLES.get(variable_id, {}).get("name", variable_id),
        "unit": VARIABLES.get(variable_id, {}).get("unit", ""),
        "min": round(float(vmin), 2),
        "max": round(float(vmax), 2),
        "gradient": gradient_stops,
        "ticks": ticks,
        "colormap": cmap_name,
    }


def render_raster_png(
    variable_id: str,
    time_str: Optional[str] = None,
    bbox: Optional[List[float]] = None,
    aggregation: str = "hourly",
    date_str: Optional[str] = None,
    custom_min: Optional[float] = None,
    custom_max: Optional[float] = None,
    target_width: int = 512,
    target_height: int = 512,
    smooth: bool = True,
) -> Tuple[bytes, List[List[float]], Dict[str, Any]]:
    """
    Renders the ERA5-Land grid slice as a transparent PNG image.
    Returns:
      (png_bytes, leaflet_bounds [[south, west], [north, east]], metadata)
    """
    # Check cache
    cache_key = f"{variable_id}:{time_str}:{date_str}:{bbox}:{aggregation}:{custom_min}:{custom_max}:{target_width}:{target_height}:{smooth}"
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    vals, lats, lons, slice_meta = get_raster_slice(
        variable_id=variable_id,
        time_str=time_str,
        bbox=bbox,
        aggregation=aggregation,
        date_str=date_str,
    )

    scale_cfg = COLOR_SCALES.get(variable_id, {})
    cmap_name = scale_cfg.get("colormap", "viridis")
    cmap = get_colormap(cmap_name)

    # Determine min/max range
    valid_mask = ~np.isnan(vals)
    if np.any(valid_mask):
        data_min = float(np.nanmin(vals))
        data_max = float(np.nanmax(vals))
    else:
        data_min = 0.0
        data_max = 1.0

    vmin = custom_min if custom_min is not None else scale_cfg.get("min", data_min)
    vmax = custom_max if custom_max is not None else scale_cfg.get("max", data_max)

    if vmin >= vmax:
        vmax = vmin + 1.0

    # Ensure latitude is top-to-bottom for the image array (north to south)
    if lats[0] < lats[-1]:
        # Latitude is ascending (south to north), flip vertically so top of image is north
        vals_img = np.flipud(vals)
        valid_img = np.flipud(valid_mask)
    else:
        vals_img = vals
        valid_img = valid_mask

    # Normalize values to 0.0 - 1.0
    norm_vals = np.clip((vals_img - vmin) / (vmax - vmin), 0.0, 1.0)

    # Map normalized values to RGBA uint8
    rgba_floats = cmap(norm_vals)  # shape: (H, W, 4) in [0.0, 1.0]
    rgba_uint8 = (rgba_floats * 255).astype(np.uint8)

    # Set NaN pixels to fully transparent (alpha = 0)
    rgba_uint8[~valid_img, 3] = 0

    # Convert to PIL Image
    img = Image.fromarray(rgba_uint8, mode="RGBA")

    # Upsample with bilinear smoothing or nearest neighbor for crisp grid cells
    resample_mode = Image.Resampling.BILINEAR if smooth else Image.Resampling.NEAREST
    img_resized = img.resize((target_width, target_height), resample=resample_mode)

    # Save to PNG buffer
    buf = io.BytesIO()
    img_resized.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()

    # Calculate Leaflet Bounds: [[south, west], [north, east]]
    south = float(np.min(lats))
    north = float(np.max(lats))
    west = float(np.min(lons))
    east = float(np.max(lons))

    # Expand half-pixel outer border for grid cell centering
    lat_half = (abs(lats[1] - lats[0]) / 2.0) if len(lats) > 1 else 0.05
    lon_half = (abs(lons[1] - lons[0]) / 2.0) if len(lons) > 1 else 0.05

    bounds = [
        [round(south - lat_half, 5), round(west - lon_half, 5)],
        [round(north + lat_half, 5), round(east + lon_half, 5)]
    ]

    legend = generate_legend_info(variable_id, vmin, vmax)

    meta = {
        **slice_meta,
        "data_min": round(data_min, 3),
        "data_max": round(data_max, 3),
        "scale_min": round(vmin, 3),
        "scale_max": round(vmax, 3),
        "bounds": bounds,
        "legend": legend,
    }

    # Store in memory cache
    if len(_IMAGE_CACHE) >= _MAX_CACHE_ENTRIES:
        # Evict oldest entry
        _IMAGE_CACHE.pop(next(iter(_IMAGE_CACHE)))
    _IMAGE_CACHE[cache_key] = (png_bytes, bounds, meta)

    return png_bytes, bounds, meta
