"""
Download API endpoint.
Exports point time-series or spatial subsets as CSV.
Matches Section 27 of Implementation Guide.
"""

import io
import csv
from flask import Blueprint, jsonify, request, Response
from app.config import VARIABLES
from app.services.netcdf_service import get_timeseries_data

download_bp = Blueprint("download", __name__)


@download_bp.route("/api/download", methods=["GET"])
def download_data():
    """
    Download time series as CSV.
    """
    variable = request.args.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({"error": f"Invalid variable '{variable}'"}), 400

    lat_str = request.args.get("lat")
    lon_str = request.args.get("lon")
    if not lat_str or not lon_str:
        return jsonify({"error": "Parameters 'lat' and 'lon' are required"}), 400

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        return jsonify({"error": "Latitude and longitude must be numbers"}), 400

    from_time = request.args.get("from")
    to_time = request.args.get("to")
    aggregation = request.args.get("aggregation", "hourly")

    try:
        ts_data = get_timeseries_data(
            variable_id=variable,
            lat=lat,
            lon=lon,
            from_time=from_time,
            to_time=to_time,
            aggregation=aggregation,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "# ERA5-Land Web GIS Data Export",
            f"Variable: {ts_data['name']} ({ts_data['variable']})",
            f"Unit: {ts_data['unit']}",
            f"Latitude: {ts_data['latitude']}",
            f"Longitude: {ts_data['longitude']}",
            f"Aggregation: {ts_data['aggregation']}"
        ])
        writer.writerow([])
        writer.writerow(["Timestamp", "Value", "Unit"])

        for row in ts_data.get("data", []):
            writer.writerow([row["time"], row["value"], ts_data["unit"]])

        filename = f"era5_{variable}_{lat}_{lon}_{aggregation}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
