"""
Time Series API endpoint.
Handles point time-series queries for clicked coordinates on the map.
Matches Sections 15, 16, 17 of Implementation Guide.
"""

from flask import Blueprint, jsonify, request
from app.config import BOUNDS, VARIABLES
from app.services.netcdf_service import get_timeseries_data

timeseries_bp = Blueprint("timeseries", __name__)


@timeseries_bp.route("/api/timeseries", methods=["GET"])
def get_timeseries():
    """
    Extract time series for specified lat/lon coordinate.
    """
    variable = request.args.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({
            "error": f"Invalid variable '{variable}'. Allowed: {list(VARIABLES.keys())}"
        }), 400

    lat_str = request.args.get("lat")
    lon_str = request.args.get("lon")
    if not lat_str or not lon_str:
        return jsonify({"error": "Query parameters 'lat' and 'lon' are required"}), 400

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        return jsonify({"error": "Latitude and longitude must be valid floating numbers"}), 400

    # Bounds check with relaxed margin
    if not (BOUNDS["lat_min"] - 0.5 <= lat <= BOUNDS["lat_max"] + 0.5 and
            BOUNDS["lon_min"] - 0.5 <= lon <= BOUNDS["lon_max"] + 0.5):
        return jsonify({
            "error": f"Coordinates ({lat}, {lon}) are outside dataset coverage: "
                     f"lat [{BOUNDS['lat_min']}, {BOUNDS['lat_max']}], "
                     f"lon [{BOUNDS['lon_min']}, {BOUNDS['lon_max']}]"
        }), 400

    from_time = request.args.get("from")
    to_time = request.args.get("to")
    aggregation = request.args.get("aggregation", "hourly").lower()
    if aggregation not in ("hourly", "daily", "monthly", "yearly"):
        aggregation = "hourly"

    try:
        data = get_timeseries_data(
            variable_id=variable,
            lat=lat,
            lon=lon,
            from_time=from_time,
            to_time=to_time,
            aggregation=aggregation,
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
