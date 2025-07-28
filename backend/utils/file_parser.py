import json
import logging
import os
import shapely.geometry
from lxml import etree
from shapely.geometry import shape, Polygon, Point, LineString, GeometryCollection, mapping
import aiofiles
import asyncio
import rasterio
from rasterio.merge import merge
import glob
import pyproj
import shapefile
from shapely.ops import transform

# Configure logging to match main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
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

async def parse_geojson(file_path):
    """Parse a GeoJSON file asynchronously."""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())
        if data.get('type') != 'FeatureCollection':
            log_error("Invalid GeoJSON", {"file_path": file_path})
            raise ValueError("GeoJSON must be a FeatureCollection")
        log_info("Parsed GeoJSON", {"file_path": file_path, "features": len(data.get("features", []))})
        return data
    except Exception as e:
        log_error("Error parsing GeoJSON", {"file_path": file_path, "error": str(e)})
        raise

def parse_geojson_sync(file_path):
    """Synchronous wrapper for parse_geojson."""
    return asyncio.run(parse_geojson(file_path))

async def parse_kml(path):
    """Parse a KML file asynchronously and convert to GeoJSON."""
    try:
        # Normalize path for Windows compatibility
        path = os.path.normpath(path)
        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            content = await f.read()
        if '<kml' not in content:
            log_error("Invalid KML file", {"file_path": path})
            raise ValueError("Invalid KML file: Missing <kml> tag")

        # Parse XML with lxml
        try:
            root = etree.fromstring(content.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            log_error("Invalid KML XML", {"file_path": path, "error": str(e)})
            raise ValueError(f"Invalid KML XML: {str(e)}")

        # Define KML namespace
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        geojson_features = []
        placemark_count = 0

        for placemark in root.findall('.//kml:Placemark', namespaces=ns):
            placemark_count += 1
            properties = {"name": placemark.findtext('kml:name', default="Unnamed", namespaces=ns)}

            # Handle ExtendedData
            extended_data = placemark.find('kml:ExtendedData', namespaces=ns)
            if extended_data is not None:
                for data in extended_data.findall('kml:Data', namespaces=ns):
                    name = data.get('name')
                    value = data.findtext('kml:value', namespaces=ns)
                    if name and value:
                        properties[name] = value
                for simple_data in extended_data.findall('kml:SimpleData', namespaces=ns):
                    name = simple_data.get('name')
                    if name:
                        properties[name] = simple_data.text

            # Handle geometry
            try:
                if placemark.find('kml:Polygon', namespaces=ns) is not None:
                    geom = placemark.find('kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', namespaces=ns)
                    if geom is None:
                        log_error("Missing coordinates in Polygon", {"placemark": properties.get("name")})
                        continue
                    coords = []
                    for coord in geom.text.strip().split('\n'):
                        try:
                            lon, lat, *_ = map(float, coord.strip().split(','))
                            coords.append([lon, lat])
                        except ValueError:
                            log_error("Invalid coordinate format in Polygon", {"placemark": properties.get("name")})
                            continue
                    if len(coords) < 3:
                        log_error("Invalid Polygon: Too few coordinates", {"placemark": properties.get("name")})
                        continue
                    geom_type = "Polygon"
                    geom_coords = [coords]
                elif placemark.find('kml:Point', namespaces=ns) is not None:
                    geom = placemark.find('kml:Point/kml:coordinates', namespaces=ns)
                    if geom is None:
                        log_error("Missing coordinates in Point", {"placemark": properties.get("name")})
                        continue
                    try:
                        lon, lat, *_ = map(float, geom.text.strip().split(','))
                        geom_type = "Point"
                        geom_coords = [lon, lat]
                    except ValueError:
                        log_error("Invalid coordinate format in Point", {"placemark": properties.get("name")})
                        continue
                elif placemark.find('kml:LineString', namespaces=ns) is not None:
                    geom = placemark.find('kml:LineString/kml:coordinates', namespaces=ns)
                    if geom is None:
                        log_error("Missing coordinates in LineString", {"placemark": properties.get("name")})
                        continue
                    coords = []
                    for coord in geom.text.strip().split('\n'):
                        try:
                            lon, lat, *_ = map(float, coord.strip().split(','))
                            coords.append([lon, lat])
                        except ValueError:
                            log_error("Invalid coordinate format in LineString", {"placemark": properties.get("name")})
                            continue
                    if len(coords) < 2:
                        log_error("Invalid LineString: Too few coordinates", {"placemark": properties.get("name")})
                        continue
                    geom_type = "LineString"
                    geom_coords = coords
                elif placemark.find('kml:MultiGeometry', namespaces=ns) is not None:
                    geom_type = "GeometryCollection"
                    geom_coords = []
                    multi_geom = placemark.find('kml:MultiGeometry', namespaces=ns)
                    for geom in multi_geom:
                        if geom.tag.endswith('Polygon'):
                            coords = []
                            coord_elem = geom.find('kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', namespaces=ns)
                            if coord_elem is None:
                                log_error("Missing coordinates in MultiGeometry Polygon", {"placemark": properties.get("name")})
                                continue
                            for coord in coord_elem.text.strip().split('\n'):
                                try:
                                    lon, lat, *_ = map(float, coord.strip().split(','))
                                    coords.append([lon, lat])
                                except ValueError:
                                    log_error("Invalid coordinate in MultiGeometry Polygon", {"placemark": properties.get("name")})
                                    continue
                            if len(coords) >= 3:
                                geom_coords.append({"type": "Polygon", "coordinates": [coords]})
                        elif geom.tag.endswith('Point'):
                            coord_elem = geom.find('kml:coordinates', namespaces=ns)
                            if coord_elem is None:
                                log_error("Missing coordinates in MultiGeometry Point", {"placemark": properties.get("name")})
                                continue
                            try:
                                lon, lat, *_ = map(float, coord_elem.text.strip().split(','))
                                geom_coords.append({"type": "Point", "coordinates": [lon, lat]})
                            except ValueError:
                                log_error("Invalid coordinate in MultiGeometry Point", {"placemark": properties.get("name")})
                                continue
                        elif geom.tag.endswith('LineString'):
                            coords = []
                            coord_elem = geom.find('kml:coordinates', namespaces=ns)
                            if coord_elem is None:
                                log_error("Missing coordinates in MultiGeometry LineString", {"placemark": properties.get("name")})
                                continue
                            for coord in coord_elem.text.strip().split('\n'):
                                try:
                                    lon, lat, *_ = map(float, coord.strip().split(','))
                                    coords.append([lon, lat])
                                except ValueError:
                                    log_error("Invalid coordinate in MultiGeometry LineString", {"placemark": properties.get("name")})
                                    continue
                            if len(coords) >= 2:
                                geom_coords.append({"type": "LineString", "coordinates": coords})
                        else:
                            log_error("Unsupported geometry in MultiGeometry", {"placemark": properties.get("name"), "geometry": geom.tag})
                            continue
                else:
                    log_error("Unsupported geometry", {"placemark": properties.get("name")})
                    continue

                # Validate geometry with Shapely
                try:
                    if geom_type == "Polygon":
                        shape(Polygon(geom_coords[0]))
                    elif geom_type == "Point":
                        shape(Point(geom_coords))
                    elif geom_type == "LineString":
                        shape(LineString(geom_coords))
                    elif geom_type == "GeometryCollection":
                        shape(GeometryCollection([shape({"type": g["type"], "coordinates": g["coordinates"]}) for g in geom_coords]))
                except Exception as e:
                    log_error("Invalid geometry", {"placemark": properties.get("name"), "error": str(e)})
                    continue

                geojson_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": geom_type,
                        "coordinates": geom_coords
                    },
                    "properties": properties
                })

            except Exception as e:
                log_error("Error processing placemark", {"placemark": properties.get("name"), "error": str(e)})
                continue

        result = {
            "type": "FeatureCollection",
            "features": geojson_features
        }
        log_info("Parsed KML", {"file_path": path, "placemarks": placemark_count, "features": len(geojson_features)})
        return result

    except Exception as e:
        log_error("Error parsing KML", {"file_path": path, "error": str(e)})
        raise

def sync_parse_kml(path):
    """Synchronous wrapper for parse_kml for compatibility with synchronous code."""
    return asyncio.run(parse_kml(path))

def merge_and_save_dem(folder_path):
    search_path = os.path.join(folder_path, "*.tif")
    tif_files = glob.glob(search_path)

    if not tif_files:
        raise FileNotFoundError("No .tif files found in the specified folder.")

    src_files = [rasterio.open(fp) for fp in tif_files]
    merged_array, transform = merge(src_files)
    crs = src_files[0].crs  # use CRS from first file

    for src in src_files:
        src.close()

    temp_tif_path = os.path.join(folder_path, "merged_output.tif")
    with rasterio.open(
        temp_tif_path,
        'w',
        driver='GTiff',
        height=merged_array.shape[1],
        width=merged_array.shape[2],
        count=1,
        dtype=merged_array.dtype,
        crs=crs,
        transform=transform
    ) as dst:
        dst.write(merged_array[0], 1)

    return temp_tif_path


def parse_shapefile(upload_folder):
    try:
        shp_path = os.path.join(upload_folder, 'uploaded.shp')
        shx_path = os.path.join(upload_folder, 'uploaded.shx')
        dbf_path = os.path.join(upload_folder, 'uploaded.dbf')

        if not (os.path.exists(shp_path) and os.path.exists(shx_path) and os.path.exists(dbf_path)):
            raise FileNotFoundError("Missing one or more required shapefile components (.shp, .shx, .dbf)")

        reader = shapefile.Reader(shp_path)
        fields = reader.fields[1:]
        field_names = [field[0] for field in fields]
        features = []

        for sr in reader.shapeRecords():
            atr = dict(zip(field_names, sr.record))
            geom = sr.shape.__geo_interface__
            features.append({
                'type': 'Feature',
                'geometry': geom,
                'properties': atr
            })

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        return geojson

    except Exception as e:
        raise RuntimeError(f"Error parsing shapefile: {str(e)}")