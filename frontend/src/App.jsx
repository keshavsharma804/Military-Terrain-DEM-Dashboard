import React, { useState } from 'react';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import FileUploader from './components/FileUploader';
import MapViewer from './components/MapViewer';
import RiskChart from './components/RiskChart';
import MetadataTable from './components/MetadataTable';
import ExportButton from './components/ExportButton';
import VisualPreview from './components/VisualPreview';
import 'animate.css';

function App() {
  const [geoData, setGeoData] = useState(null);
  const [previewImage, setPreviewImage] = useState(null);
  const [slopeMap, setSlopeMap] = useState(null);
  const [interactiveMapUrl, setInteractiveMapUrl] = useState(null);
  const [downloadDem, setDownloadDem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  const handleFileData = (parsedData) => {
    setGeoData(parsedData);
    toast.success('File uploaded successfully!');
  };

  const handleTifUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    setLoading(true);
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/upload-tif`,
        formData,
        {
          headers: {
            'x-api-key': process.env.REACT_APP_API_KEY,
          },
        }
      );
      if (response.data.status === 'success') {
        toast.success(`TIFF uploaded: ${response.data.filename}`);
      } else {
        toast.error(`Upload failed: ${response.data.message}`);
      }
    } catch (err) {
      toast.error(`Upload failed: ${err.response?.data?.message || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateDEM = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/merge-dem`,
        { folder_path: 'Uploads/input' },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': process.env.REACT_APP_API_KEY,
          },
        }
      );
      if (response.data.status === 'success') {
        setPreviewImage(`${process.env.REACT_APP_BACKEND_URL}${response.data.preview}`);
        setSlopeMap(`${process.env.REACT_APP_BACKEND_URL}${response.data.slope_map}`);
        setInteractiveMapUrl(`${process.env.REACT_APP_BACKEND_URL}${response.data.interactive}`);
        setDownloadDem(`${process.env.REACT_APP_BACKEND_URL}${response.data.merged_dem}`);
        toast.success('DEM generated successfully!');
        window.open(`${process.env.REACT_APP_BACKEND_URL}${response.data.interactive}`, '_blank');
      } else {
        toast.error(`Error: ${response.data.message}`);
      }
    } catch (err) {
      toast.error(`DEM generation failed: ${err.response?.data?.message || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gradient-to-br from-blue-100 to-gray-200'} transition-colors duration-300`}>
      <div className="container mx-auto p-6">
        <header className="text-center mb-8 flex justify-between items-center">
          <div>
            <h1 className={`text-4xl font-bold ${darkMode ? 'text-blue-300' : 'text-blue-800'} animate__animated animate__fadeIn`}>
              Military Terrain DEM Dashboard
            </h1>
            <p className={`text-${darkMode ? 'gray-400' : 'gray-600'} mt-2 animate__animated animate__fadeIn animate__delay-1s`}>
              Upload KML/GeoJSON and TIFF files to analyze terrain insights.
            </p>
          </div>
          <button
            onClick={toggleDarkMode}
            className={`p-2 rounded-full ${darkMode ? 'bg-yellow-400 text-gray-900' : 'bg-gray-800 text-white'} hover:opacity-80 transition duration-300`}
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
        </header>
        <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className={`lg:col-span-1 ${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl shadow-2xl p-6 animate__animated animate__fadeInUp`}>
            <h2 className={`text-2xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-4`}>Data Input</h2>
            <FileUploader onDataParsed={handleFileData} onTifUpload={handleTifUpload} accept=".kml,.geojson,.tif,.tiff" />
            <VisualPreview />
            <button
              onClick={generateDEM}
              disabled={loading}
              className={`w-full mt-4 py-3 px-6 rounded-lg text-white font-semibold ${
                loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
              } transition duration-300 flex items-center justify-center animate__animated animate__pulse`}
            >
              {loading ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5 mr-2 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Generating...
                </>
              ) : (
                'Generate DEM Preview'
              )}
            </button>
            {(previewImage || slopeMap) && (
              <div className="mt-6 animate__animated animate__fadeIn">
                {previewImage && (
                  <>
                    <h3 className={`text-xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-2`}>Preview Image</h3>
                    <img
                      src={previewImage}
                      alt="DEM Preview"
                      className="w-full max-w-md mx-auto rounded-lg border shadow-md"
                    />
                  </>
                )}
                {slopeMap && (
                  <div className="mt-6">
                    <h3 className={`text-xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-2`}>Slope Map</h3>
                    <img
                      src={slopeMap}
                      alt="Slope Map"
                      className="w-full max-w-md mx-auto rounded-lg border shadow-md"
                    />
                  </div>
                )}
              </div>
            )}
            {(previewImage || interactiveMapUrl || downloadDem || slopeMap) && (
              <div className="mt-6 flex flex-wrap gap-4 animate__animated animate__fadeIn">
                {downloadDem && (
                  <a
                    href={downloadDem}
                    className={`flex items-center ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-800'} font-medium`}
                  >
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download DEM
                  </a>
                )}
                {slopeMap && (
                  <a
                    href={slopeMap}
                    className={`flex items-center ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-800'} font-medium`}
                  >
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download Slope Map
                  </a>
                )}
                {interactiveMapUrl && (
                  <a
                    href={interactiveMapUrl}
                    target="_blank"
                    className={`flex items-center ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-800'} font-medium`}
                  >
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6-10v13m6-10v10m5.553-6.894A1 1 0 0120 5.618v10.764a1 1 0 01-1.447.894L15 14.382"
                      />
                    </svg>
                    View Interactive Map
                  </a>
                )}
              </div>
            )}
            {geoData && (
              <div className="mt-6 animate__animated animate__fadeIn">
                <h3 className={`text-xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-2`}>Metadata</h3>
                <MetadataTable data={geoData} />
                <ExportButton />
              </div>
            )}
          </section>
          <section className={`lg:col-span-2 ${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl shadow-2xl p-6 animate__animated animate__fadeInUp`}>
            <h2 className={`text-2xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-4`}>Map Viewer</h2>
            <div className="h-96 rounded-lg border shadow-md">
              {geoData ? (
                <MapViewer data={geoData} />
              ) : (
                <p className={`p-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Please upload a KML, GeoJSON, or TIFF file to visualize the map.
                </p>
              )}
            </div>
            {geoData && (
              <div className="mt-6">
                <h3 className={`text-xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-2`}>Risk Analysis</h3>
                <RiskChart data={geoData} />
              </div>
            )}
          </section>
        </main>
        <ToastContainer position="top-right" autoClose={3000} theme={darkMode ? 'dark' : 'light'} />
      </div>
    </div>
  );
}

export default App;