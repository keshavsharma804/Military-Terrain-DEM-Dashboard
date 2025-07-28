import json
import os
import logging
import sqlite3
import csv
import glob
import time  # Added import for time
from io import StringIO  # Added import for StringIO
import rasterio
import hashlib
from functools import wraps, lru_cache
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flasgger import Swagger
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from utils.file_parser import parse_shapefile, parse_kml, parse_geojson
from utils.merge_and_plot_dem import merge_and_save_dem, generate_static_preview, export_to_folium
from utils.analysis import extract_elevation_stats, generate_slope_map
from analysis.risk_model import evaluate_risk
from analysis.terrain import calculate_slope
from utils.folium_helper import add_legend_and_stats

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5000", "http://localhost:5173"]}})
app.config['UPLOAD_FOLDER'] = 'Uploads/input'
app.config['ALLOWED_EXTENSIONS'] = {'tif', 'tiff', 'kml', 'geojson', 'shp', 'shx', 'dbf'}
Swagger(app)

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY not set in .env file")

# Config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'Uploads')
MAX_FILE_SIZE = 10 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
)

def log_error(message, extra=None):
    logging.error(json.dumps({"error": message, **(extra or {})}))

def log_info(message, extra=None):
    logging.info(json.dumps({"message": message, **(extra or {})}))

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-API-Key') != API_KEY:
            log_error("Invalid or missing API key", {"endpoint": request.endpoint})
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS parsed_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  data TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def hash_files(folder_path):
    """Generate a hash of all .tif files in the folder for caching."""
    tif_files = sorted([f for f in glob.glob(os.path.join(folder_path, "*.tif")) if not f.endswith("merged_dem.tif")])
    if not tif_files:
        return None
    hasher = hashlib.sha256()
    for file_path in tif_files:
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
    return hasher.hexdigest()

@app.route('/upload-tif', methods=['POST'])
@require_api_key
def upload_tif():
    try:
        if 'file' not in request.files:
            log_error("No file part in request", {})
            return jsonify({"status": "error", "message": "No file part in request"}), 400
        file = request.files['file']
        if file.filename == '':
            log_error("No selected file", {})
            return jsonify({"status": "error", "message": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            try:
                with rasterio.open(file_path) as src:
                    if src.count < 1 or src.dtypes[0] not in ('int16', 'float32', 'float64'):
                        os.remove(file_path)
                        log_error("Invalid GeoTIFF file", {"filename": filename})
                        return jsonify({"status": "error", "message": "Invalid GeoTIFF: Must contain valid elevation data"}), 400
            except rasterio.errors.RasterioIOError as e:
                os.remove(file_path)
                log_error("Failed to validate GeoTIFF", {"filename": filename, "error": str(e)})
                return jsonify({"status": "error", "message": f"Invalid GeoTIFF: {str(e)}"}), 400
            log_info("File uploaded successfully", {"filename": filename, "path": file_path})
            return jsonify({"status": "success", "filename": filename}), 200
        else:
            log_error("Invalid file extension", {"filename": file.filename})
            return jsonify({"status": "error", "message": "Invalid file extension: Only .tif or .tiff allowed"}), 400
    except Exception as e:
        log_error("Failed to upload file", {"error": str(e)})
        return jsonify({"status": "error", "message": f"Upload failed: {str(e)}"}), 500

@lru_cache(maxsize=32)
def cached_merge_dem(folder_hash, folder_path):
    """Cached DEM processing based on folder hash."""
    try:
        log_info("Starting DEM merge", {"folder_path": folder_path})
        merged_tif_path = merge_and_save_dem(folder_path)
        log_info("Generating static preview", {"merged_tif_path": merged_tif_path})
        preview_img = generate_static_preview(merged_tif_path)
        log_info("Generating folium map", {"merged_tif_path": merged_tif_path})
        interactive_map = export_to_folium(merged_tif_path)
        log_info("Extracting elevation stats", {"merged_tif_path": merged_tif_path})
        stats = extract_elevation_stats(merged_tif_path)
        log_info("Generating slope map", {"merged_tif_path": merged_tif_path})
        slope_map = generate_slope_map(merged_tif_path)
        return {
            'status': 'success',
            'merged_dem': merged_tif_path.replace("\\", "/"),
            'preview': f"/Uploads/{os.path.basename(preview_img)}",
            'interactive': f"/Uploads/{os.path.basename(interactive_map)}",
            'slope_map': f"/Uploads/{os.path.basename(slope_map)}",
            'elevation_stats': stats
        }
    except FileNotFoundError as e:
        log_error("No .tif files found", {"folder_path": folder_path, "error": str(e)})
        return {"status": "error", "message": "No valid .tif files found in the specified folder"}
    except rasterio.errors.RasterioIOError as e:
        log_error("Invalid GeoTIFF data", {"folder_path": folder_path, "error": str(e)})
        return {"status": "error", "message": f"Invalid GeoTIFF data: {str(e)}"}
    except Exception as e:
        log_error("Error merging DEM", {"folder_path": folder_path, "error": str(e)})
        return {"status": "error", "message": f"DEM processing failed: {str(e)}"}

@app.route('/merge-dem', methods=['POST'])
@require_api_key
def merge_dem():
    try:
        data = request.get_json()
        folder_path = data.get('folder_path', 'Uploads/input')
        log_info("Received merge-dem request", {"folder_path": folder_path})
        
        # Validate folder
        if not os.path.exists(folder_path):
            log_error("Folder does not exist", {"folder_path": folder_path})
            return jsonify({"status": "error", "message": f"Folder {folder_path} does not exist"}), 400
        
        # Check for at least one .tif file
        tif_files = [f for f in glob.glob(os.path.join(folder_path, "*.tif")) if not f.endswith("merged_dem.tif")]
        if len(tif_files) < 1:
            log_error("Insufficient .tif files", {"folder_path": folder_path, "file_count": len(tif_files)})
            return jsonify({"status": "error", "message": "At least one .tif file is required"}), 400
        
        # Generate cache key
        folder_hash = hash_files(folder_path)
        if not folder_hash:
            log_error("No .tif files for hashing", {"folder_path": folder_path})
            return jsonify({"status": "error", "message": "No .tif files found for processing"}), 400
        
        # Process DEM with caching
        result = cached_merge_dem(folder_hash, folder_path)
        return jsonify(result), 200 if result['status'] == 'success' else 500
    except Exception as e:
        log_error("Unexpected error in merge-dem", {"error": str(e)})
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500

@app.after_request
def cleanup(response):
    for file in glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*_small.tif')):
        if os.path.isfile(file) and time.time() - os.path.getmtime(file) > 3600:
            try:
                os.remove(file)
            except OSError as e:
                log_error("Failed to remove file during cleanup", {"file": file, "error": str(e)})
    return response

@app.route('/view-dem')
@require_api_key
def view_dem():
    try:
        folder = "Uploads/input"
        merged_tif = merge_and_save_dem(folder)
        static_image_path = generate_static_preview(merged_tif)
        interactive_map_path = export_to_folium(merged_tif)
        return jsonify({
            "static_image_url": f"/Uploads/{os.path.basename(static_image_path)}",
            "interactive_map_url": f"/Uploads/{os.path.basename(interactive_map_path)}"
        })
    except Exception as e:
        log_error("Failed to process DEM", {"error": str(e)})
        return jsonify({'error': str(e)}), 500

@app.route('/api/sample', methods=['GET'])
@require_api_key
def get_sample_kml():
    try:
        data_path = os.path.join('data', 'sample_zones.kml')
        features = parse_kml(data_path)
        log_info("Sample KML retrieved", {"path": data_path, "features": len(features.get("features", []))})
        return jsonify(features)
    except Exception as e:
        log_error("Error reading sample KML", {"path": data_path, "error": str(e)})
        return jsonify({'error': 'Failed to read sample KML'}), 500

@app.route('/api/terrain', methods=['POST'])
@require_api_key
def analyze_terrain():
    try:
        geo_data = request.get_json()
        if not geo_data or 'features' not in geo_data:
            log_error("Invalid GeoJSON data", {"endpoint": "terrain"})
            return jsonify({'error': 'Invalid GeoJSON data'}), 400
        slopes = calculate_slope(geo_data)
        for i, feature in enumerate(geo_data.get("features", [])):
            feature["properties"]["slope"] = slopes[i]
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("INSERT INTO parsed_data (data) VALUES (?)", (json.dumps(geo_data),))
        conn.commit()
        conn.close()
        log_info("Terrain analysis completed", {"features": len(geo_data.get("features", [])), "slopes": slopes})
        return jsonify({"slopes": slopes, "geojson": geo_data})
    except Exception as e:
        log_error("Error in terrain analysis", {"error": str(e)})
        return jsonify({'error': 'Failed to analyze terrain'}), 500

@app.route('/api/analyze', methods=['GET'])
@require_api_key
def analyze_risk():
    try:
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT data FROM parsed_data ORDER BY timestamp DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        data = json.loads(row[0]) if row else {"features": []}
        scores = evaluate_risk(data)
        log_info("Risk analysis completed", {"features": len(data.get("features", [])), "scores": scores})
        return jsonify({"scores": scores})
    except Exception as e:
        log_error("Error in risk analysis", {"error": str(e)})
        return jsonify({'error': 'Failed to analyze risk'}), 500

@app.route('/api/layers', methods=['GET'])
@require_api_key
def get_uploaded_layer():
    try:
        data_path = os.path.join('data', 'restricted_area.geojson')
        data = parse_geojson(data_path)
        log_info("Retrieved restricted area", {"path": data_path})
        return jsonify({"geojson": data})
    except Exception as e:
        log_error("Error retrieving restricted area", {"path": data_path, "error": str(e)})
        return jsonify({'error': 'Failed to retrieve restricted area'}), 500

@app.route('/api/restricted', methods=['GET'])
@require_api_key
def get_restricted_area():
    return get_uploaded_layer()

@app.route('/api/zones', methods=['GET'])
@require_api_key
def get_zones():
    try:
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT data FROM parsed_data ORDER BY timestamp DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        data = json.loads(row[0]) if row else {"type": "FeatureCollection", "features": []}
        log_info("Retrieved zones", {"features": len(data.get("features", []))})
        return jsonify(data)
    except Exception as e:
        log_error("Error retrieving zones", {"error": str(e)})
        return jsonify({'error': 'Failed to retrieve zones'}), 500

@app.route('/api/parse', methods=['POST'])
@require_api_key
def parse_file():
    try:
        if 'file' not in request.files:
            log_error("No file part in the request")
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        if not file or file.filename == '':
            log_error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            log_error("Invalid file extension", {"filename": filename})
            return jsonify({'error': 'Invalid file type'}), 400
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            log_error("File too large", {"filename": filename, "size": file_size})
            return jsonify({'error': 'File too large. Max 10MB allowed'}), 400
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        log_info("File uploaded", {"filename": filename, "size": file_size})
        data = None
        if filename.endswith('.kml'):
            data = parse_kml(file_path)
        elif filename.endswith('.geojson'):
            data = parse_geojson(file_path)
        elif filename.endswith('.shp'):
            data = parse_shapefile(file_path)
        if data and isinstance(data, dict):
            features = data.get("features", [])
            total_features = len(features)
            geometry_types = {}
            for f in features:
                geom_type = f.get("geometry", {}).get("type", "Unknown")
                geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
            data["metadata"] = {
                "total_features": total_features,
                "geometry_types": geometry_types
            }
        if request.args.get('store', 'false').lower() == 'true' and data:
            try:
                conn = sqlite3.connect('data.db')
                c = conn.cursor()
                c.execute("INSERT INTO parsed_data (data) VALUES (?)", (json.dumps(data),))
                conn.commit()
                conn.close()
                log_info("Data stored in DB", {"filename": filename})
            except Exception as db_err:
                log_error("Database insert failed", {"error": str(db_err)})
        return jsonify(data), 200
    except Exception as e:
        log_error("Unhandled exception in file parsing", {"error": str(e)})
        return jsonify({'error': 'Failed to parse the file. Ensure valid format and structure.'}), 500
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
            log_info("Temporary file removed", {"file_path": file_path})

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    File Upload Endpoint
    ---
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Upload a KML or GeoJSON file
    responses:
      200:
        description: Parsed data
      400:
        description: Upload or parsing error
    """
    return parse_file()

@app.route('/api/export', methods=['GET'])
@require_api_key
def export_data():
    format = request.args.get('format', 'json')
    try:
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT data FROM parsed_data ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'No parsed data found'}), 404
        parsed_data = json.loads(row[0])
        if format == 'csv':
            if not parsed_data.get('features') or not parsed_data['features'][0].get('properties'):
                return jsonify({'error': 'No valid feature properties found for CSV export'}), 400
            output = StringIO()
            fields = list(parsed_data['features'][0]['properties'].keys())
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for feature in parsed_data['features']:
                writer.writerow(feature.get('properties', {}))
            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers.set('Content-Disposition', 'attachment', filename='parsed_data.csv')
            return response
        return Response(json.dumps(parsed_data), mimetype='application/json',
                       headers={"Content-Disposition": "attachment;filename=parsed_data.json"})
    except Exception as e:
        return jsonify({'error': 'Export failed', 'details': str(e)}), 500

@app.route('/api/metadata', methods=['POST'])
@require_api_key
def extract_metadata():
    try:
        if not request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        filenames = {}
        for ext in ('shp', 'shx', 'dbf'):
            if f'{ext}' in request.files:
                uploaded_file = request.files[ext]
                new_name = f"uploaded.{ext}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)
                uploaded_file.save(path)
                filenames[ext] = path
        if 'file' in request.files:
            file = request.files['file']
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                return jsonify({'error': 'Invalid file type'}), 400
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            ext = filename.split('.')[-1].lower()
            if ext == 'kml':
                data = parse_kml(file_path)
            elif ext == 'geojson':
                data = parse_geojson(file_path)
            elif ext == 'shp':
                data = parse_shapefile(filenames.get('shp', 'uploaded.shp'))
            else:
                return jsonify({'error': 'Unsupported file type'}), 400
        elif 'shp' in filenames:
            data = parse_shapefile(filenames['shp'])
        else:
            return jsonify({'error': 'No valid GIS file provided'}), 400
        metadata = {}
        geometries = []
        if data and isinstance(data, dict):
            features = data.get("features", [])
            total_features = len(features)
            geometry_types = {}
            for f in features:
                geom = f.get("geometry")
                if geom:
                    try:
                        shp = shape(geom)
                        geometries.append(shp)
                        geom_type = geom.get("type", "Unknown")
                        geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
                    except Exception:
                        pass
            combined = unary_union(geometries) if geometries else None
            bbox = combined.bounds if combined else None
            centroid = list(combined.centroid.coords)[0] if combined else None
            metadata = {
                "total_features": total_features,
                "geometry_types": geometry_types,
                "bounding_box": bbox,
                "centroid": centroid
            }
        return jsonify({"metadata": metadata}), 200
    except Exception as e:
        return jsonify({'error': f'Metadata extraction failed: {str(e)}'}), 500
    finally:
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            if f.startswith("uploaded.") or f == filename:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
                except:
                    pass

@app.route('/api/metadata/csv', methods=['POST'])
@require_api_key
def export_metadata_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            return jsonify({'error': 'Invalid file type'}), 400
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if filename.endswith('.kml'):
            data = parse_kml(file_path)
        elif filename.endswith('.geojson'):
            data = parse_geojson(file_path)
        elif filename.endswith('.shp'):
            data = parse_shapefile(file_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        if not data or not isinstance(data, dict) or not data.get('features'):
            return jsonify({'error': 'Invalid or empty GeoJSON data'}), 400
        geometries = []
        rows = []
        for idx, f in enumerate(data.get("features", []), 1):
            geom = f.get("geometry")
            if geom:
                try:
                    shp = shape(geom)
                    geometries.append(shp)
                    rows.append({
                        "feature_id": idx,
                        "geometry_type": geom.get("type", "Unknown"),
                        "centroid": list(shp.centroid.coords)[0] if shp.centroid.coords else None,
                        "bbox": shp.bounds if shp.bounds else None
                    })
                except Exception as e:
                    log_error("Failed to process geometry", {"feature_id": idx, "error": str(e)})
        if not rows:
            return jsonify({'error': 'No valid geometries found for CSV export'}), 400
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["feature_id", "geometry_type", "centroid", "bbox"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='metadata.csv')
    except Exception as e:
        return jsonify({'error': f'CSV metadata export failed: {str(e)}'}), 500
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

@app.route('/api/preview/image', methods=['POST'])
@require_api_key
def generate_map_preview():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            return jsonify({'error': 'Invalid file type'}), 400
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if filename.endswith('.kml'):
            data = parse_kml(file_path)
        elif filename.endswith('.geojson'):
            data = parse_geojson(file_path)
        elif filename.endswith('.shp'):
            data = parse_shapefile(file_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        geometries = []
        if data and isinstance(data, dict):
            for f in data.get("features", []):
                geom = f.get("geometry")
                if geom:
                    try:
                        shp = shape(geom)
                        geometries.append(shp)
                    except:
                        continue
        fig, ax = plt.subplots(figsize=(6, 6))
        for geom in geometries:
            x, y = geom.exterior.xy if hasattr(geom, "exterior") else geom.xy
            ax.plot(x, y, linewidth=1)
        ax.set_title("Geospatial Feature Preview")
        ax.axis("equal")
        ax.axis("off")
        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], 'preview.png')
        fig.savefig(preview_path, bbox_inches='tight')
        plt.close(fig)
        return send_file(preview_path, mimetype='image/png', as_attachment=True, download_name='preview.png')
    except Exception as e:
        return jsonify({'error': f'Preview image generation failed: {str(e)}'}), 500
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], 'preview.png')
        if os.path.exists(preview_path):
            os.remove(preview_path)

@app.route('/api/visual-preview', methods=['POST'])
@require_api_key
def visual_preview():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        ext = filename.split('.')[-1].lower()
        if not allowed_file(filename):
            return jsonify({'error': 'Invalid file type'}), 400
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        if ext == 'kml':
            data = parse_kml(path)
        elif ext == 'geojson':
            data = parse_geojson(path)
        elif ext == 'shp':
            data = parse_shapefile(path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        preview_features = []
        for f in data.get("features", []):
            geom = f.get("geometry")
            if not geom:
                continue
            try:
                shp = shape(geom).simplify(0.0001)
                preview_features.append({
                    "type": "Feature",
                    "geometry": mapping(shp),
                    "properties": {}
                })
            except:
                continue
        return jsonify({
            "type": "FeatureCollection",
            "features": preview_features
        })
    except Exception as e:
        return jsonify({'error': f'Preview generation failed: {str(e)}'}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.route('/')
def serve_react_app():
    return send_from_directory('dist', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('dist', path)

@app.route('/Uploads/<path:filename>')
def serve_uploaded_file(filename):
    try:
        return send_from_directory('Uploads', filename)
    except Exception as e:
        log_error("Failed to serve file", {"filename": filename, "error": str(e)})
        return jsonify({"status": "error", "message": f"File not found: {filename}"}), 404
    
if __name__ == '__main__':
    load_dotenv()
    init_db()
    app.run(debug=True)