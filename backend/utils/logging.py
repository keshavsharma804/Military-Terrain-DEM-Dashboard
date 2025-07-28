# utils/logging.py
import json
import logging
import shapely
from shapely.geometry import mapping

# Configure logging to match main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
)

def log_error(message, extra=None):
    def serialize_value(v):
        if isinstance(v, (shapely.geometry.base.BaseGeometry)):
            return mapping(v)  # Convert geometry to dict
        try:
            json.dumps(v)
            return v
        except TypeError:
            return str(v)

    safe_extra = {k: serialize_value(v) for k, v in (extra or {}).items()}
    logging.error(json.dumps({"error": message, **safe_extra}))

def log_info(message, extra=None):
    logging.info(json.dumps({"message": message, **(extra or {})}))