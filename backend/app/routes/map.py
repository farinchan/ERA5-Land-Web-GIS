"""
Map and Visualization API endpoints.
Provides endpoints for times, raster overlays, wind vectors, and regional boundaries.
"""

import io
from flask import Blueprint, jsonify, request, Response, send_file
from app.config import BOUNDS, MAX_BBOX_SPAN, VARIABLES
from app.services.netcdf_service import (
    get_available_times,
    get_wind_vectors,
)
from app.services.raster_service import render_raster_png

map_bp = Blueprint("map", __name__)


def parse_bbox(bbox_str: str):
    """Parse comma-separated bbox string 'west,south,east,north'."""
    if not bbox_str:
        return None
    try:
        parts = [float(p.strip()) for p in bbox_str.split(",")]
        if len(parts) != 4:
            return None
        west, south, east, north = parts
        # Validation
        if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0):
            return None
        if not (-90.0 <= south <= 90.0 and -90.0 <= north <= 90.0):
            return None
        if west >= east or south >= north:
            return None
        if (east - west) > MAX_BBOX_SPAN or (north - south) > MAX_BBOX_SPAN:
            return None
        return [west, south, east, north]
    except Exception:
        return None


@map_bp.route("/api/times", methods=["GET"])
def get_times():
    """
    Get available time steps.
    Matches Section 10 of Implementation Guide.
    """
    from_time = request.args.get("from")
    to_time = request.args.get("to")
    step = int(request.args.get("step", 1))

    try:
        times = get_available_times(from_time=from_time, to_time=to_time, step=step)
        return jsonify({
            "count": len(times),
            "times": times
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@map_bp.route("/api/map", methods=["GET"])
def get_map_metadata():
    """
    Get map metadata and generated raster overlay URL for the given parameters.
    Matches Section 11 of Implementation Guide.
    """
    variable = request.args.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({
            "error": f"Invalid variable '{variable}'. Allowed: {list(VARIABLES.keys())}"
        }), 400

    time_str = request.args.get("time")
    date_str = request.args.get("date")
    aggregation = request.args.get("aggregation", "hourly")
    bbox_str = request.args.get("bbox")
    bbox = parse_bbox(bbox_str)

    custom_min = request.args.get("min", type=float)
    custom_max = request.args.get("max", type=float)
    smooth = request.args.get("smooth", "true").lower() in ("true", "1", "yes")

    try:
        # Pre-render to obtain accurate bounds and legend
        _, bounds, meta = render_raster_png(
            variable_id=variable,
            time_str=time_str,
            bbox=bbox,
            aggregation=aggregation,
            date_str=date_str,
            custom_min=custom_min,
            custom_max=custom_max,
            smooth=smooth,
        )

        # Build direct image URL
        query_params = [f"variable={variable}"]
        if time_str:
            query_params.append(f"time={time_str}")
        if date_str:
            query_params.append(f"date={date_str}")
        if aggregation != "hourly":
            query_params.append(f"aggregation={aggregation}")
        if bbox_str:
            query_params.append(f"bbox={bbox_str}")
        if custom_min is not None:
            query_params.append(f"min={custom_min}")
        if custom_max is not None:
            query_params.append(f"max={custom_max}")
        query_params.append(f"smooth={'true' if smooth else 'false'}")

        image_url = f"/api/map/raster?{'&'.join(query_params)}"

        return jsonify({
            "variable": variable,
            "name": meta.get("name"),
            "unit": meta.get("unit"),
            "time": meta.get("time"),
            "aggregation": meta.get("aggregation"),
            "bounds": bounds,
            "image_url": image_url,
            "legend": meta.get("legend"),
            "data_min": meta.get("data_min"),
            "data_max": meta.get("data_max"),
            "scale_min": meta.get("scale_min"),
            "scale_max": meta.get("scale_max"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@map_bp.route("/api/map/raster", methods=["GET"])
def get_map_raster():
    """
    Renders and streams transparent RGBA PNG for Leaflet ImageOverlay.
    """
    variable = request.args.get("variable", "t2m")
    if variable not in VARIABLES:
        return jsonify({"error": f"Invalid variable '{variable}'"}), 400

    time_str = request.args.get("time")
    date_str = request.args.get("date")
    aggregation = request.args.get("aggregation", "hourly")
    bbox = parse_bbox(request.args.get("bbox"))
    custom_min = request.args.get("min", type=float)
    custom_max = request.args.get("max", type=float)
    width = int(request.args.get("width", 600))
    height = int(request.args.get("height", 600))
    smooth = request.args.get("smooth", "true").lower() in ("true", "1", "yes")

    try:
        png_bytes, bounds, meta = render_raster_png(
            variable_id=variable,
            time_str=time_str,
            bbox=bbox,
            aggregation=aggregation,
            date_str=date_str,
            custom_min=custom_min,
            custom_max=custom_max,
            target_width=min(max(width, 128), 2048),
            target_height=min(max(height, 128), 2048),
            smooth=smooth,
        )

        response = Response(png_bytes, mimetype="image/png")
        response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["X-Raster-Bounds"] = str(bounds)
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@map_bp.route("/api/wind", methods=["GET"])
def get_wind():
    """
    Get wind vector components for overlay rendering.
    Matches Section 18 of Implementation Guide.
    """
    time_str = request.args.get("time")
    bbox = parse_bbox(request.args.get("bbox"))
    stride = max(1, int(request.args.get("stride", 3)))

    try:
        vectors = get_wind_vectors(time_str=time_str, bbox=bbox, stride=stride)
        return jsonify({
            "count": len(vectors),
            "stride": stride,
            "vectors": vectors
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@map_bp.route("/api/regions", methods=["GET"])
def get_regions():
    """
    Returns administrative boundaries GeoJSON for Sumatra region.
    """
    import os
    from flask import current_app
    
    # Path to GeoJSON in static/data
    static_folder = current_app.static_folder
    geojson_path = os.path.join(static_folder, "data", "sumatra_boundaries.geojson")
    
    if os.path.exists(geojson_path):
        return send_file(geojson_path, mimetype="application/geo+json")
    
    # Fallback to minimal GeoJSON boundary box for West Sumatra
    return jsonify({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Cakupan ERA5-Land Sumatera",
                    "region": "Sumatera"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [93.7, -2.7],
                            [102.3, -2.7],
                            [102.3, 6.2],
                            [93.7, 6.2],
                            [93.7, -2.7]
                        ]
                    ]
                }
            }
        ]
    })
