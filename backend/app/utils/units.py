"""
Unit conversion utilities for ERA5-Land variables.
Converts raw NetCDF storage units to user-friendly display units.
"""

from typing import Any, Union
import numpy as np
import xarray as xr


def convert_units(
    data: Union[float, np.ndarray, xr.DataArray],
    variable_id: str
) -> Union[float, np.ndarray, xr.DataArray]:
    """
    Convert raw variable data to display units.
    - Temperature (t2m, d2m): Kelvin (K) -> Celsius (°C)
    - Precipitation & Hydrology (tp, pev, ro): meters (m) -> millimeters (mm)
    - Surface Pressure (sp): Pascals (Pa) -> Hectopascals (hPa)
    - Soil Moisture (swvl1-swvl4): m³/m³ (no conversion)
    - Wind components (u10, v10, wind_speed): m/s (no conversion)
    """
    if variable_id in ("t2m", "d2m"):
        return data - 273.15

    if variable_id in ("tp", "pev", "ro"):
        # Note: pev in ERA5 is often negative (indicating water loss from surface)
        # or positive depending on sign convention. In ERA5-Land, pev is typically negative.
        # Converting m to mm multiplies by 1000.
        return data * 1000.0

    if variable_id == "sp":
        return data / 100.0

    # swvl1, swvl2, swvl3, swvl4, u10, v10, wind_speed, wind_direction
    return data


def format_value_with_unit(value: float, unit: str, precision: int = 2) -> str:
    """Format numeric value with its unit string."""
    if value is None or np.isnan(value):
        return "N/A"
    return f"{value:.{precision}f} {unit}"
