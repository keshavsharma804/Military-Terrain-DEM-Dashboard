# Geospatial Intelligence Dashboard

A full-stack Flask and React application for processing and visualizing geospatial data, including KML, GeoJSON, and DEM (.tif) files, built to demonstrate advanced Python, JavaScript, and GIS skills.

## Project Overview
This project processes geospatial data for terrain analysis, generating hillshade maps, slope maps, and interactive visualizations. It features a responsive React frontend with file uploads and a Flask backend for data processing, optimized with caching and robust error handling.

## Key Features
- **Data Retrieval and Processing**: Processes `.tif` files using `rasterio` and `numpy` for DEM merging, hillshade generation, and elevation statistics extraction.
- **Geospatial Analysis**: Computes slope maps and risk scores using `numpy` and custom algorithms, validated with QGIS.
- **Frontend Development**: Built a responsive React frontend with Tailwind CSS, `react-leaflet` for interactive maps, and animations for enhanced UX.
- **GIS Integration**: Outputs compatible with QGIS for professional geospatial analysis and visualization.
- **Error Handling and Optimization**: Implemented caching with `lru_cache`, fixed path case sensitivity, and resolved `404` errors for file serving.
- **File Parsing**: Supports KML, GeoJSON, and shapefiles with asynchronous parsing using `shapely` and `lxml`.

## Technical Stack
- **Backend**: Python, Flask, `rasterio`, `numpy`, `folium`, `werkzeug`, `shapely`, `lxml`
- **Frontend**: JavaScript, React, `react-leaflet`, Tailwind CSS, `react-toastify`, `animate.css`
- **GIS Tools**: QGIS for validation and visualization
- **Database**: SQLite for storing parsed geospatial data
- **Other**: Asynchronous file parsing with `aiofiles`, logging, and API key authentication

## Key Contributions
- Developed a robust backend to process large `.tif` files, reducing processing time with downsampling and caching.
- Fixed critical bugs, including `glob` module errors and case-sensitive path issues, ensuring seamless file access.
- Designed a user-friendly React interface with dark mode, animations, and real-time map updates.
- Integrated QGIS-compatible outputs for professional geospatial workflows.
- Implemented comprehensive error handling for invalid GeoTIFFs, missing files, and database operations.


## Setup
1. Clone: `git clone <repo_url>`
2. Backend: `cd backend && pip install -r requirements.txt`
3. Frontend: `cd frontend && npm install && npm run build && mv dist ../backend/`
4. Create `backend/.env`: `API_KEY=v3WHvReXYg/FWoIfvLgXHmY/SC28JKUsSOGK+oM8X5Q=`
5. Run: `cd backend && python main.py`
6. Access: `http://localhost:5000` (React) or `http://localhost:5000/simple` (HTML fallback)

## Screenshots
![1](https://github.com/user-attachments/assets/ed431e72-5c03-4192-abf6-d7918f37f52d)
![2](https://github.com/user-attachments/assets/5c1ae08a-a490-431c-bc8d-7c351bdb7aaa)
![3](https://github.com/user-attachments/assets/e7f84e36-aa1c-4b0e-9224-3aa4143a90f6)
![4](https://github.com/user-attachments/assets/d638b291-032b-4be4-89a5-71f64d148fb2)
![5](https://github.com/user-attachments/assets/b1ef1a1a-3a36-430a-a699-111c982c4896)


## Upcoming Features To Enhance it

- Real-Time Terrain Analysis: Add live slope and aspect calculations with dynamic visualizations using WebGL or Plotly for enhanced interactivity.
- 3D Terrain Visualization: Integrate Three.js to render 3D terrain models from DEM data in the browser.
- Multi-Format Export: Support exporting processed data as CSV, GeoJSON, or KMZ for broader compatibility.
- Batch Processing: Enable simultaneous processing of multiple geospatial file types (e.g., KML, GeoJSON, shapefiles) in a single request.
- Terrain Risk Scoring: Implement advanced risk assessment models based on elevation, slope, and user-defined parameters.
- Cloud Integration: Add support for uploading and processing files from cloud storage (e.g., AWS S3, Google Drive).
- User Authentication: Introduce user accounts with JWT-based authentication for secure access and data persistence.
- Interactive Layer Controls: Allow users to toggle map layers (e.g., hillshade, slope, elevation) dynamically in the React frontend.
- Geospatial Querying: Enable spatial queries (e.g., points within polygons) using PostGIS or shapely.
