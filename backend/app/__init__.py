"""
Flask Application Factory for ERA5-Land Web GIS.
"""

import os
# Ensure file locking is disabled on network/cloud drives before anything loads
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

from flask import Flask, render_template
from flask_cors import CORS

from app.config import (
    BOUNDS,
    STATIC_DIR,
    TEMPLATE_DIR,
    VARIABLES,
)
from app.routes.download import download_bp
from app.routes.map import map_bp
from app.routes.statistics import statistics_bp
from app.routes.timeseries import timeseries_bp
from app.routes.variables import variables_bp
from app.services.netcdf_service import get_dataset_info


def create_app(config_override=None):
    """Create and configure Flask application instance."""
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )

    # Enable CORS for all API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    if config_override:
        app.config.update(config_override)

    # Register blueprints
    app.register_blueprint(variables_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(timeseries_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(download_bp)

    # Web View Route: Render Jinja2 dashboard
    @app.route("/")
    def index():
        dataset_info = {}
        try:
            dataset_info = get_dataset_info()
        except Exception as e:
            app.logger.warning(f"Could not load dataset info on startup: {e}")

        # Group variables by category for the template
        categories = {}
        for var_id, var_meta in VARIABLES.items():
            cat = var_meta.get("category", "meteorology").capitalize()
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(var_meta)

        return render_template(
            "index.html",
            variables=VARIABLES,
            categories=categories,
            dataset_info=dataset_info,
            bounds=BOUNDS,
            default_variable="t2m",
        )

    return app
