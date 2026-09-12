"""
Variables and Health Check API endpoints.
"""

from flask import Blueprint, jsonify
from app.config import VARIABLES
from app.services.netcdf_service import get_dataset_info

variables_bp = Blueprint("variables", __name__)


@variables_bp.route("/api/health", methods=["GET"])
def health_check():
    """Health check and dataset status endpoint."""
    try:
        info = get_dataset_info()
        return jsonify({
            "status": "ok",
            "message": "ERA5-Land Web GIS API is running smoothly",
            "dataset": info
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@variables_bp.route("/api/variables", methods=["GET"])
def get_variables():
    """
    Get list of available ERA5-Land variables with metadata.
    Matches Section 9 of Implementation Guide.
    """
    vars_list = [
        {
            "id": var["id"],
            "name": var["name"],
            "unit": var["unit"],
            "category": var.get("category", "meteorology"),
            "description": var.get("description", ""),
            "aggregation": var.get("aggregation", "mean"),
            "default_min": var.get("default_min"),
            "default_max": var.get("default_max"),
            "colormap": var.get("colormap", "viridis"),
        }
        for var in VARIABLES.values()
    ]

    return jsonify({"variables": vars_list})
