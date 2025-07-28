import json
import os
import logging
import numpy as np
from shapely.geometry import shape

# Configure logging to match main.py and file_parser.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

def log_error(message, extra=None):
    logging.error(json.dumps({"error": message, **(extra or {})}))

def log_info(message, extra=None):
    logging.info(json.dumps({"message": message, **(extra or {})}))

def evaluate_risk(data, restricted_path="data/restricted_area.geojson"):
    """
    Evaluate risk for each feature in the input GeoJSON data based on proximity
    to restricted areas and terrain slope.
    
    Args:
        data (dict): GeoJSON FeatureCollection
        restricted_path (str): Path to restricted area GeoJSON file
    
    Returns:
        list: Risk scores for each feature (0-100)
    """
    try:
        # Validate input data
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            log_error("Invalid input data", {"type": type(data).__name__})
            raise ValueError("Input must be a GeoJSON FeatureCollection")

        # Load restricted areas
        if not os.path.exists(restricted_path):
            log_error("Restricted area file not found", {"path": restricted_path})
            raise FileNotFoundError(f"Restricted area file not found: {restricted_path}")
        
        with open(restricted_path, 'r', encoding='utf-8') as f:
            restricted = json.load(f)
        if restricted.get("type") != "FeatureCollection":
            log_error("Invalid restricted area GeoJSON", {"path": restricted_path})
            raise ValueError("Restricted area must be a GeoJSON FeatureCollection")
        
        restricted_shapes = []
        for feature in restricted.get("features", []):
            try:
                restricted_shapes.append(shape(feature["geometry"]))
            except Exception as e:
                log_error("Invalid geometry in restricted area", {"path": restricted_path, "error": str(e)})
                continue
        
        if not restricted_shapes:
            log_error("No valid geometries in restricted area", {"path": restricted_path})
            raise ValueError("No valid geometries found in restricted area")

        scores = []
        for feature in data.get("features", []):
            try:
                geom = shape(feature["geometry"])
                # Calculate minimum distance to restricted areas
                min_distance = min(geom.distance(r) for r in restricted_shapes) if restricted_shapes else float('inf')
                # Risk based on proximity (higher risk if closer)
                distance_risk = 100 * np.exp(-min_distance / 0.01) if min_distance != float('inf') else 0.0
                # Incorporate slope (default to 0.0 if missing)
                slope = feature.get("properties", {}).get("slope", 0.0)
                if not isinstance(slope, (int, float)):
                    log_error("Invalid slope value", {"feature_name": feature.get("properties", {}).get("name", "Unnamed"), "slope": slope})
                    slope = 0.0
                slope_risk = 10 * slope  # Adjust weight as needed
                # Combine risks and cap at 100
                risk = min(round(distance_risk + slope_risk, 2), 100.0)
                scores.append(risk)
                log_info("Calculated risk", {
                    "feature_name": feature.get("properties", {}).get("name", "Unnamed"),
                    "distance": round(min_distance, 4),
                    "slope": slope,
                    "risk": risk
                })
            except Exception as e:
                log_error("Error processing feature", {
                    "feature_name": feature.get("properties", {}).get("name", "Unnamed"),
                    "error": str(e)
                })
                scores.append(0.0)
        
        if not scores:
            log_info("No valid features processed", {"feature_count": len(data.get("features", []))})
        return scores

    except Exception as e:
        log_error("Error in evaluate_risk", {"error": str(e)})
        return [0.0] * len(data.get("features", []))