"""
Main entrypoint for running ERA5-Land Web GIS backend.
"""

import os
import socket
import sys

# Ensure HDF5 locking is disabled
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

# Add backend directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app import create_app

app = create_app()


def is_port_truly_free(port):
    """Check if port is actually available and not intercepted by OS services (e.g. macOS AirPlay on 5000)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return False
    except (ConnectionRefusedError, OSError):
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def get_free_port(preferred_port=5000):
    """Determine the best available port (detects port 5000 conflict with macOS ControlCenter)."""
    if "PORT" in os.environ:
        return int(os.environ["PORT"])
    for p in [preferred_port, 5001, 5050, 8080, 8000]:
        if is_port_truly_free(p):
            return p
    return 5001


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = get_free_port(5000)
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print("=" * 60, flush=True)
    print("  ERA5-Land Web GIS Server", flush=True)
    print(f"  Access UI at: http://{host}:{port}/", flush=True)
    print(f"  API Health:   http://{host}:{port}/api/health", flush=True)
    print("=" * 60, flush=True)

    app.run(host=host, port=port, debug=debug, threaded=True)
