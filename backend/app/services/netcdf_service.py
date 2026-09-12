"""
NetCDF Data Service.
Handles opening the ERA5-Land NetCDF dataset with xarray/dask lazy loading,
spatial slicing with descending/ascending latitude detection,
temporal subsetting, resampling/aggregations, and point extraction.
"""

import os
# Must be set before importing xarray/netCDF4 to avoid locking issues on networked/OneDrive storage
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import xarray as xr

from app.config import (
    CHUNKS,
    DATA_PATH,
    VARIABLES,
)
from app.utils.units import convert_units

# Singleton dataset holder
_DATASET: Optional[xr.Dataset] = None
_TIMESTAMPS_CACHE: Optional[List[str]] = None
_DATASET_INFO_CACHE: Optional[Dict[str, Any]] = None


def get_dataset() -> xr.Dataset:
    """
    Open the ERA5-Land dataset lazily with dask chunking.
    Reuses cached dataset handle if already opened.
    """
    global _DATASET
    if _DATASET is not None:
        return _DATASET

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"ERA5-Land dataset not found at: {DATA_PATH}")

    # Open with chunks for lazy evaluation
    ds = xr.open_dataset(
        DATA_PATH,
        chunks=CHUNKS,
    )
    _DATASET = ds
    return _DATASET


def get_dataset_info() -> Dict[str, Any]:
    """Retrieve metadata information about the loaded dataset (cached)."""
    global _DATASET_INFO_CACHE
    if _DATASET_INFO_CACHE is not None:
        return _DATASET_INFO_CACHE

    ds = get_dataset()
    times = pd.to_datetime(ds.valid_time.values)
    lats = ds.latitude.values
    lons = ds.longitude.values

    _DATASET_INFO_CACHE = {
        "time_start": str(times.min().isoformat()),
        "time_end": str(times.max().isoformat()),
        "time_count": len(times),
        "lat_min": float(lats.min()),
        "lat_max": float(lats.max()),
        "lon_min": float(lons.min()),
        "lon_max": float(lons.max()),
        "lat_step": float(abs(lats[1] - lats[0])) if len(lats) > 1 else 0.1,
        "lon_step": float(abs(lons[1] - lons[0])) if len(lons) > 1 else 0.1,
        "variables": list(VARIABLES.keys()),
    }
    return _DATASET_INFO_CACHE


def get_available_times(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    step: int = 1
) -> List[str]:
    """
    Retrieve formatted ISO string timestamps available in the dataset.
    Supports filtering by from_time and to_time.
    """
    global _TIMESTAMPS_CACHE
    ds = get_dataset()
    
    if _TIMESTAMPS_CACHE is None:
        raw_times = pd.to_datetime(ds.valid_time.values)
        _TIMESTAMPS_CACHE = [t.strftime("%Y-%m-%dT%H:%M:%S") for t in raw_times]

    times = _TIMESTAMPS_CACHE

    if from_time:
        times = [t for t in times if t >= from_time]
    if to_time:
        times = [t for t in times if t <= to_time]

    if step > 1:
        times = times[::step]

    return times


def get_variable_array(
    ds: xr.Dataset,
    variable_id: str
) -> xr.DataArray:
    """
    Extract variable DataArray from dataset, computing derived variables if needed.
    """
    if variable_id == "wind_speed":
        u = ds["u10"]
        v = ds["v10"]
        return np.sqrt(u ** 2 + v ** 2)

    if variable_id == "wind_direction":
        u = ds["u10"]
        v = ds["v10"]
        # Meteorological direction: degrees from which the wind blows (0=North, 90=East)
        direction = (np.degrees(np.arctan2(-u, -v))) % 360.0
        return direction

    if variable_id not in ds.data_vars:
        raise ValueError(f"Variable '{variable_id}' not found in dataset. Available: {list(ds.data_vars)}")

    return ds[variable_id]


def slice_spatial(
    da: Union[xr.DataArray, xr.Dataset],
    bbox: Optional[List[float]] = None
) -> Union[xr.DataArray, xr.Dataset]:
    """
    Slice DataArray or Dataset spatially with bbox [west, south, east, north].
    Handles descending latitude coordinates automatically.
    """
    if not bbox:
        return da

    west, south, east, north = bbox
    lats = da.latitude.values
    lat_is_ascending = lats[0] < lats[-1]

    if lat_is_ascending:
        lat_slice = slice(south, north)
    else:
        # Descending: start from northern higher value down to southern lower value
        lat_slice = slice(north, south)

    lon_slice = slice(west, east)
    return da.sel(latitude=lat_slice, longitude=lon_slice)


def get_raster_slice(
    variable_id: str,
    time_str: Optional[str] = None,
    bbox: Optional[List[float]] = None,
    aggregation: str = "hourly",
    date_str: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Extract a 2D spatial slice for raster visualization.
    Returns:
      (values_2d, latitudes_1d, longitudes_1d, metadata)
    """
    ds = get_dataset()
    da = get_variable_array(ds, variable_id)
    da = slice_spatial(da, bbox)

    var_meta = VARIABLES.get(variable_id, {})
    agg_type = var_meta.get("aggregation", "mean")

    # Time selection or temporal aggregation
    if aggregation in ("daily", "monthly", "yearly") and (date_str or time_str):
        # Temporal aggregation for a given day/month/year
        ref_time = date_str or time_str
        target_dt = pd.to_datetime(ref_time)
        
        if aggregation == "daily":
            # Slice for that entire day
            day_str = target_dt.strftime("%Y-%m-%d")
            time_subset = da.sel(valid_time=slice(f"{day_str} 00:00:00", f"{day_str} 23:59:59"))
        elif aggregation == "monthly":
            month_start = target_dt.strftime("%Y-%m-01")
            # Next month start or month end
            time_subset = da.sel(valid_time=slice(month_start, f"{target_dt.year}-{target_dt.month:02d}-31"))
        else: # yearly
            time_subset = da.sel(valid_time=slice(f"{target_dt.year}-01-01", f"{target_dt.year}-12-31"))

        if time_subset.sizes.get("valid_time", 0) == 0:
            # Fallback to nearest
            da_time = da.sel(valid_time=target_dt, method="nearest")
        else:
            if agg_type == "sum":
                da_time = time_subset.sum(dim="valid_time")
            else:
                da_time = time_subset.mean(dim="valid_time")
    else:
        # Single timestep
        if time_str:
            target_dt = pd.to_datetime(time_str)
            da_time = da.sel(valid_time=target_dt, method="nearest")
        else:
            # Default to first available timestamp
            da_time = da.isel(valid_time=0)

    # Compute lazy dask array to numpy
    raw_vals = da_time.values
    # Convert units to display units
    vals = convert_units(raw_vals, variable_id)

    lats = da_time.latitude.values
    lons = da_time.longitude.values

    # Determine actual timestamp if single timestep
    selected_time = ""
    if "valid_time" in da_time.coords:
        selected_time = pd.to_datetime(da_time.valid_time.values).isoformat()
    elif time_str:
        selected_time = time_str

    meta = {
        "variable": variable_id,
        "name": var_meta.get("name", variable_id),
        "unit": var_meta.get("unit", ""),
        "time": selected_time,
        "aggregation": aggregation,
        "lat_min": float(lats.min()),
        "lat_max": float(lats.max()),
        "lon_min": float(lons.min()),
        "lon_max": float(lons.max()),
        "shape": list(vals.shape),
    }

    return vals, lats, lons, meta


def get_timeseries_data(
    variable_id: str,
    lat: float,
    lon: float,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    aggregation: str = "hourly"
) -> Dict[str, Any]:
    """
    Extract time series for a clicked point (lat, lon) with optional aggregation.
    """
    ds = get_dataset()
    da = get_variable_array(ds, variable_id)
    var_meta = VARIABLES.get(variable_id, {})
    agg_type = var_meta.get("aggregation", "mean")

    # Select nearest spatial grid cell
    point_da = da.sel(latitude=lat, longitude=lon, method="nearest")
    nearest_lat = float(point_da.latitude.values)
    nearest_lon = float(point_da.longitude.values)

    # Temporal subset
    if from_time or to_time:
        start = from_time if from_time else str(point_da.valid_time.values.min())
        end = to_time if to_time else str(point_da.valid_time.values.max())
        point_da = point_da.sel(valid_time=slice(start, end))

    # Apply aggregation resampling if requested
    if aggregation == "daily":
        resampler = point_da.resample(valid_time="1D")
        point_da = resampler.sum() if agg_type == "sum" else resampler.mean()
    elif aggregation == "monthly":
        resampler = point_da.resample(valid_time="1MS")
        point_da = resampler.sum() if agg_type == "sum" else resampler.mean()
    elif aggregation == "yearly":
        resampler = point_da.resample(valid_time="1YS")
        point_da = resampler.sum() if agg_type == "sum" else resampler.mean()

    # Compute values and convert units
    raw_vals = point_da.values
    vals = convert_units(raw_vals, variable_id)
    times = pd.to_datetime(point_da.valid_time.values)

    records = []
    for t, v in zip(times, vals):
        val_float = None if np.isnan(v) else round(float(v), 3)
        records.append({
            "time": t.strftime("%Y-%m-%d %H:%M"),
            "iso": t.isoformat(),
            "value": val_float
        })

    valid_floats = [r["value"] for r in records if r["value"] is not None]
    
    stats = {}
    if valid_floats:
        stats["min"] = round(float(np.min(valid_floats)), 3)
        stats["max"] = round(float(np.max(valid_floats)), 3)
        stats["mean"] = round(float(np.mean(valid_floats)), 3)
        if agg_type == "sum" or variable_id in ("tp", "pev", "ro"):
            stats["total"] = round(float(np.sum(valid_floats)), 3)
    else:
        stats = {"min": None, "max": None, "mean": None}

    return {
        "query_lat": lat,
        "query_lon": lon,
        "latitude": nearest_lat,
        "longitude": nearest_lon,
        "variable": variable_id,
        "name": var_meta.get("name", variable_id),
        "unit": var_meta.get("unit", ""),
        "aggregation": aggregation,
        "stats": stats,
        "data": records
    }


def get_wind_vectors(
    time_str: Optional[str] = None,
    bbox: Optional[List[float]] = None,
    stride: int = 2
) -> List[Dict[str, Any]]:
    """
    Extract wind U/V components downsampled by stride for vector arrows display.
    """
    ds = get_dataset()
    if time_str:
        target_dt = pd.to_datetime(time_str)
        u_slice = ds["u10"].sel(valid_time=target_dt, method="nearest")
        v_slice = ds["v10"].sel(valid_time=target_dt, method="nearest")
    else:
        u_slice = ds["u10"].isel(valid_time=0)
        v_slice = ds["v10"].isel(valid_time=0)

    u_slice = slice_spatial(u_slice, bbox)
    v_slice = slice_spatial(v_slice, bbox)

    u_vals = u_slice.values[::stride, ::stride]
    v_vals = v_slice.values[::stride, ::stride]
    lats = u_slice.latitude.values[::stride]
    lons = u_slice.longitude.values[::stride]

    vectors = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            u = float(u_vals[i, j])
            v = float(v_vals[i, j])
            if np.isnan(u) or np.isnan(v):
                continue
            speed = float(np.sqrt(u**2 + v**2))
            direction = float((np.degrees(np.arctan2(-u, -v))) % 360.0)
            vectors.append({
                "lat": round(float(lat), 4),
                "lon": round(float(lon), 4),
                "u": round(u, 2),
                "v": round(v, 2),
                "speed": round(speed, 2),
                "direction": round(direction, 1),
            })

    return vectors
