"""
Statistics API endpoints for spatial bbox and polygon analysis.
Matches Sections 28 and 29 of Implementation Guide.
"""

from flask import Blueprint, jsonify, request
from app.config import VARIABLES
from app.routes.map import parse_bbox
from app.services.statistics_service import (
    calculate_bbox_statistics,
    calculate_polygon_statistics,
)

statistics_bp = Blueprint("statistics", __name__)


@statistics_bp.route("/api/statistics", methods=["GET"])
def get_bbox_statistics():
    """
    Compute summary statistics across a bounding box or entire dataset.
    Matches Section 28 of Implementation Guide.
    """
    variable = request.args.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({"error": f"Invalid variable '{variable}'"}), 400

    bbox = parse_bbox(request.args.get("bbox"))
    time_str = request.args.get("time")
    from_time = request.args.get("from")
    to_time = request.args.get("to")

    try:
        stats = calculate_bbox_statistics(
            variable_id=variable,
            bbox=bbox,
            time_str=time_str,
            from_time=from_time,
            to_time=to_time,
        )
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@statistics_bp.route("/api/statistics/polygon", methods=["POST"])
def get_polygon_statistics():
    """
    Perform spatial statistics calculation over an arbitrary GeoJSON Polygon.
    Matches Section 29 of Implementation Guide.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    variable = data.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({"error": f"Invalid variable '{variable}'"}), 400

    geometry = data.get("geometry")
    if not geometry or not isinstance(geometry, dict):
        return jsonify({"error": "A valid GeoJSON geometry object is required in body"}), 400

    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return jsonify({"error": "Geometry type must be 'Polygon' or 'MultiPolygon'"}), 400

    time_str = data.get("time")
    from_time = data.get("from")
    to_time = data.get("to")

    try:
        stats = calculate_polygon_statistics(
            variable_id=variable,
            geometry=geometry,
            time_str=time_str,
            from_time=from_time,
            to_time=to_time,
        )
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
