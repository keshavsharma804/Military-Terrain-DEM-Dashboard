import rasterio
import os
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def generate_slope_map(dem_path, out_path='uploads/slope_map_colored.png'):
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype('float64')
        if np.all(elevation == src.nodata) or np.isnan(elevation).all():
            raise ValueError("Input DEM contains only nodata or NaN values")
        x, y = np.gradient(elevation, src.res[0], src.res[1])
        slope = np.sqrt(x**2 + y**2)
        slope = np.arctan(slope) * (180 / np.pi)

        norm = mcolors.Normalize(vmin=0, vmax=np.percentile(slope, 98))
        cmap = plt.get_cmap('viridis')
        colored_slope = cmap(norm(slope))

        plt.imsave(out_path, colored_slope)
        if not os.path.exists(out_path):
            raise FileNotFoundError(f"Failed to save slope map at {out_path}")
    return out_path

def extract_elevation_stats(dem_path):
    with rasterio.open(dem_path) as src:
        elevation = src.read(1)
        stats = {
            'min': float(np.min(elevation)),
            'max': float(np.max(elevation)),
            'mean': float(np.mean(elevation)),
            'std': float(np.std(elevation))
        }
    return stats
