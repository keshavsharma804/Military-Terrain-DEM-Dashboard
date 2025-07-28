import os
from glob import glob
import numpy as np
import numpy.ma as ma
import rasterio

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from rasterio.merge import merge
from rasterio.enums import Resampling
from rasterio.plot import show
from rasterio.plot import reshape_as_image
from rasterio.plot import show_hist
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import folium
import branca.colormap as cm
from matplotlib.colors import LightSource
from utils.logging import log_error, log_info



def merge_and_save_dem(folder_path):
    # Remove redundant "input" from path
    base_path = folder_path if folder_path.endswith('input') else os.path.join(folder_path, 'input')
    tif_files = [f for f in glob(os.path.join(base_path, "*.tif")) if not f.endswith("merged_dem.tif")]
    log_info("Found TIFF files", {"files": tif_files, "folder_path": base_path})
    if not tif_files:
        log_error("No .tif files found in the specified folder.", {"folder_path": base_path})
        raise FileNotFoundError("No .tif files found in the specified folder.")
    

    downsampled_paths = []
    for fp in tif_files:
        with rasterio.open(fp) as src:
            scale_factor = 8
            data = src.read(
                out_shape=(src.count, src.height // scale_factor, src.width // scale_factor),
                resampling=Resampling.bilinear
            )
            if np.all(data == src.nodata) or np.isnan(data).all():
                log_error("Invalid input DEM: contains only nodata or NaN", {"file": fp})
                continue
            if data.shape[1] < 2 or data.shape[2] < 2:
                log_error("Input DEM too small for processing", {"file": fp, "shape": data.shape})
                continue
            transform = src.transform * src.transform.scale(
                (src.width / data.shape[2]),
                (src.height / data.shape[1])
            )
            temp_fp = fp.replace(".tif", "_small.tif")
            out_meta = src.meta.copy()
            out_meta.update({
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": transform,
                "compress": "lzw",
                "nodata": src.nodata if src.nodata is not None else -9999
            })
            with rasterio.open(temp_fp, "w", **out_meta) as dest:
                dest.write(data)
            downsampled_paths.append(temp_fp)

    if not downsampled_paths:
        log_error("No valid DEM files after processing", {"folder_path": folder_path})
        raise ValueError("No valid DEM files after processing")

    src_files_to_mosaic = [rasterio.open(fp) for fp in downsampled_paths]
    mosaic, out_transform = merge(src_files_to_mosaic)

    if np.all(mosaic == src_files_to_mosaic[0].nodata) or np.isnan(mosaic).all():
        for src in src_files_to_mosaic:
            src.close()
        log_error("Merged DEM contains only nodata or NaN values", {"folder_path": folder_path})
        raise ValueError("Merged DEM contains only nodata or NaN values")

    out_fp = os.path.join(folder_path, "merged_dem.tif")
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "count": 1,
        "dtype": mosaic.dtype,
        "nodata": src_files_to_mosaic[0].nodata if src_files_to_mosaic[0].nodata is not None else -9999
    })

    for src in src_files_to_mosaic:
        src.close()
    if os.path.exists(out_fp):
        os.remove(out_fp)
    with rasterio.open(out_fp, "w", **out_meta) as dest:
        dest.write(mosaic[0], 1)

    # Only clean up temporary files on success
    for temp_fp in downsampled_paths:
        try:
            os.remove(temp_fp)
        except OSError as e:
            log_error("Failed to remove temporary file", {"file": temp_fp, "error": str(e)})

    return out_fp

def generate_hillshade(input, out_path='Uploads/hillshade.png'):
    if isinstance(input, str):
        with rasterio.open(input) as src:
            elevation = src.read(1)
            res_x, res_y = src.res
    else:
        elevation = input
        res_x = res_y = 1  # Default resolution

    azimuth = 315
    angle_altitude = 45
    x, y = np.gradient(elevation, res_x, res_y)
    slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
    aspect = np.arctan2(-x, y)
    shaded = np.sin(np.radians(angle_altitude)) * np.sin(slope) + \
             np.cos(np.radians(angle_altitude)) * np.cos(slope) * np.cos(np.radians(azimuth) - aspect)
    shaded = (255 * (shaded - shaded.min()) / (shaded.max() - shaded.min())).astype(np.uint8)

    # Save the hillshade image to file
    plt.imsave(out_path, shaded, cmap='gray')
    # Return the shaded array instead of the file path
    return shaded

def generate_static_preview(tif_path):
    with rasterio.open(tif_path) as src:
        dem = src.read(1)
        dem = np.ma.masked_equal(dem, src.nodata)
        hillshade = generate_hillshade(tif_path)  # Now returns the shaded array

        fig, ax = plt.subplots(figsize=(12, 10))
        ax.imshow(hillshade, cmap='gray', alpha=1)  # Use the shaded array
        terrain = ax.imshow(dem, cmap='terrain', alpha=0.6)
        plt.colorbar(terrain, ax=ax, label="Elevation (m)")
        ax.set_title("Hillshaded DEM with Elevation Overlay")
        ax.grid(True, color='white', linestyle='--', linewidth=0.3)
        ax.set_xlabel("X (Columns)")
        ax.set_ylabel("Y (Rows)")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        plt.tight_layout()
        output_path = os.path.join('Uploads', 'merged_dem_with_hillshade.png')
        plt.savefig(output_path, dpi=300)
        plt.close()
    return output_path

def reproject_to_wgs84(input_path, output_path):
    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': 'EPSG:4326',
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.nearest)

    return output_path


def export_to_folium(input_path, output_path='Uploads/interactive_map.html'):
    try:
        with rasterio.open(input_path) as src:
            bounds = src.bounds
            elevation = src.read(1)
            nodata = src.nodata if src.nodata is not None else -9999
            res_x, res_y = src.res

        # Mask invalid values
        elevation = np.ma.masked_where((elevation == nodata) | np.isnan(elevation) | np.isinf(elevation), elevation)
        if elevation.count() < 2:
            log_error("Invalid elevation data for Folium map", {"file": input_path, "count": elevation.count()})
            raise ValueError("Invalid elevation data for Folium map")

        # Generate hillshade
        hillshade_path = input_path.replace('.tif', '_hillshade.png')
        hillshade = generate_hillshade(input_path, hillshade_path)
        if hillshade is None or np.all(hillshade == 0):
            log_error("Failed to generate valid hillshade", {"file": hillshade_path})
            raise ValueError("Failed to generate valid hillshade")

        # Initialize Folium map
        m = folium.Map(
            location=[(bounds.top + bounds.bottom) / 2, (bounds.left + bounds.right) / 2],
            zoom_start=10,
            tiles='OpenStreetMap'
        )

        # Add hillshade as ImageOverlay
        folium.raster_layers.ImageOverlay(
            image=hillshade_path,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            opacity=0.6,
            interactive=True,
            cross_origin=True
        ).add_to(m)

        # Add elevation colormap with safe min/max
        valid_elevation = elevation.compressed()
        vmin = float(np.percentile(valid_elevation, 2)) if valid_elevation.size > 0 else 0
        vmax = float(np.percentile(valid_elevation, 98)) if valid_elevation.size > 0 else 1000
        colormap = cm.LinearColormap(
            colors=['blue', 'green', 'yellow', 'red'],
            vmin=vmin,
            vmax=vmax
        )
        colormap.add_to(m)

        # Add elevation stats
        stats = {
            "min": float(vmin),
            "max": float(vmax),
            "mean": float(np.mean(valid_elevation)) if valid_elevation.size > 0 else 0
        }
        folium.Popup(f"Elevation Stats: {stats}").add_to(m)

        m.save(output_path)
        log_info("Interactive map generated", {"output_path": output_path})
        return output_path
    except Exception as e:
        log_error("Failed to generate Folium map", {"error": str(e), "file": input_path})
        raise


def extract_elevation_stats(tif_path):
    import rasterio
    import numpy as np

    with rasterio.open(tif_path) as src:
        band = src.read(1)
        band = band[band != src.nodata]

    stats = {
        "min_elevation": float(np.min(band)),
        "max_elevation": float(np.max(band)),
        "mean_elevation": float(np.mean(band)),
        "std_deviation": float(np.std(band))
    }
    return stats

def add_legend_and_stats(m, stats):
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 240px;
        height: 120px;
        background-color: white;
        z-index: 9999;
        padding: 10px;
        border: 1px solid black;
        font-size: 14px;
    ">
        <strong>Elevation Stats:</strong><br>
        Min: {stats['min_elevation']}<br>
        Max: {stats['max_elevation']}<br>
        Mean: {stats['mean_elevation']}<br>
        Std Dev: {stats['std_deviation']}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
