import rasterio
import numpy as np
from rasterio.transform import xy

def calculate_slope(geo_data):
    try:
        # Example: Load a DEM raster (replace with your DEM file)
        dem_path = "path/to/your/dem.tif"
        with rasterio.open(dem_path) as dem:
            # Extract coordinates from GeoJSON
            features = geo_data.get("features", [])
            slopes = []
            for feature in features:
                if feature["geometry"]["type"] == "Polygon":
                    coords = feature["geometry"]["coordinates"][0]
                    # Compute slope for centroid of polygon
                    centroid_x = sum(p[0] for p in coords) / len(coords)
                    centroid_y = sum(p[1] for p in coords) / len(coords)
                    row, col = dem.index(centroid_x, centroid_y)
                    # Read elevation data around centroid
                    window = rasterio.windows.from_bounds(
                        centroid_x - 0.01, centroid_y - 0.01,
                        centroid_x + 0.01, centroid_y + 0.01,
                        dem.transform
                    )
                    elev = dem.read(1, window=window)
                    # Compute slope (simplified, use real algorithm)
                    dy, dx = np.gradient(elev)
                    slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
                    slopes.append(float(np.mean(slope)))
                else:
                    slopes.append(0.0)  # Default for non-polygon features
            return slopes
    except Exception as e:
        print(f"Error in calculate_slope: {e}")
        return [0.0] * len(geo_data.get("features", []))