"""
Statistics Service.
Calculates spatial and temporal statistics for bounding boxes and arbitrary polygons,
supporting interactive point and polygon analysis.
"""

from typing import Any, Dict, List, Optional
import matplotlib.path as mpath
import numpy as np
import pandas as pd
from shapely.geometry import shape

from app.config import VARIABLES
from app.services.netcdf_service import (
    get_dataset,
    get_variable_array,
    slice_spatial,
)
from app.utils.units import convert_units


def calculate_bbox_statistics(
    variable_id: str,
    bbox: Optional[List[float]] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    time_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate spatial and temporal statistics across a bounding box.
    """
    ds = get_dataset()
    da = get_variable_array(ds, variable_id)
    da = slice_spatial(da, bbox)
    var_meta = VARIABLES.get(variable_id, {})
    unit = var_meta.get("unit", "")
    agg_type = var_meta.get("aggregation", "mean")

    if time_str:
        target_dt = pd.to_datetime(time_str)
        da = da.sel(valid_time=target_dt, method="nearest")
    elif from_time or to_time:
        start = from_time if from_time else str(da.valid_time.values.min())
        end = to_time if to_time else str(da.valid_time.values.max())
        da = da.sel(valid_time=slice(start, end))

    # Compute lazy array
    raw_vals = da.values
    vals = convert_units(raw_vals, variable_id)
    valid_vals = vals[~np.isnan(vals)]

    if len(valid_vals) == 0:
        return {
            "variable": variable_id,
            "unit": unit,
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
        }

    stats = {
        "variable": variable_id,
        "name": var_meta.get("name", variable_id),
        "unit": unit,
        "count": int(len(valid_vals)),
        "min": round(float(np.min(valid_vals)), 3),
        "max": round(float(np.max(valid_vals)), 3),
        "mean": round(float(np.mean(valid_vals)), 3),
        "std": round(float(np.std(valid_vals)), 3),
    }

    if agg_type == "sum" or variable_id in ("tp", "pev", "ro"):
        stats["total"] = round(float(np.sum(valid_vals)), 3)

    return stats


def calculate_polygon_statistics(
    variable_id: str,
    geometry: Dict[str, Any],
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    time_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute spatial statistics and temporal breakdown within an arbitrary GeoJSON polygon.
    """
    geom_shape = shape(geometry)
    min_lon, min_lat, max_lon, max_lat = geom_shape.bounds

    ds = get_dataset()
    da = get_variable_array(ds, variable_id)
    # Slice spatially to polygon bounding box first for maximum performance
    da_sub = slice_spatial(da, bbox=[min_lon, min_lat, max_lon, max_lat])

    lats = da_sub.latitude.values
    lons = da_sub.longitude.values

    # Build 2D grid coordinates
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])

    # Build shapely / matplotlib path mask
    # Support polygon exterior coordinates
    if geometry.get("type") == "Polygon":
        poly_coords = geometry["coordinates"][0]
        path = mpath.Path(poly_coords)
        mask_flat = path.contains_points(points)
    else:
        # MultiPolygon fallback
        mask_flat = np.array([geom_shape.contains(shape({"type": "Point", "coordinates": pt})) for pt in points])

    mask_2d = mask_flat.reshape(lat_grid.shape)

    # Time filtering
    if time_str:
        target_dt = pd.to_datetime(time_str)
        da_sub = da_sub.sel(valid_time=target_dt, method="nearest")
        # Array shape: (lat, lon)
        raw_vals = da_sub.values
        vals = convert_units(raw_vals, variable_id)
        # Apply polygon mask
        poly_vals = vals[mask_2d & ~np.isnan(vals)]
        temporal_series = []
    else:
        if from_time or to_time:
            start = from_time if from_time else str(da_sub.valid_time.values.min())
            end = to_time if to_time else str(da_sub.valid_time.values.max())
            da_sub = da_sub.sel(valid_time=slice(start, end))

        raw_vals = da_sub.values  # shape: (valid_time, lat, lon)
        vals = convert_units(raw_vals, variable_id)

        # Calculate time series mean within polygon for each timestamp
        times = pd.to_datetime(da_sub.valid_time.values)
        temporal_series = []
        all_poly_vals = []

        for t_idx, t in enumerate(times):
            frame_vals = vals[t_idx]
            frame_poly_vals = frame_vals[mask_2d & ~np.isnan(frame_vals)]
            if len(frame_poly_vals) > 0:
                mean_t = float(np.mean(frame_poly_vals))
                all_poly_vals.extend(frame_poly_vals)
                temporal_series.append({
                    "time": t.strftime("%Y-%m-%d %H:%M"),
                    "value": round(mean_t, 3)
                })

        poly_vals = np.array(all_poly_vals)

    var_meta = VARIABLES.get(variable_id, {})
    unit = var_meta.get("unit", "")
    agg_type = var_meta.get("aggregation", "mean")

    if len(poly_vals) == 0:
        return {
            "variable": variable_id,
            "unit": unit,
            "cell_count": int(np.sum(mask_2d)),
            "valid_data_points": 0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "timeseries": temporal_series,
        }

    stats = {
        "variable": variable_id,
        "name": var_meta.get("name", variable_id),
        "unit": unit,
        "cell_count": int(np.sum(mask_2d)),
        "valid_data_points": int(len(poly_vals)),
        "min": round(float(np.min(poly_vals)), 3),
        "max": round(float(np.max(poly_vals)), 3),
        "mean": round(float(np.mean(poly_vals)), 3),
        "std": round(float(np.std(poly_vals)), 3),
        "timeseries": temporal_series,
    }

    if agg_type == "sum" or variable_id in ("tp", "pev", "ro"):
        stats["total"] = round(float(np.sum(poly_vals)), 3)

    return stats
