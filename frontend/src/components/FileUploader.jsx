import React, { useState } from 'react';
import { toast } from 'react-toastify';

function FileUploader({ onDataParsed, onTifUpload, accept = '.kml,.geojson,.tif,.tiff' }) {
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      if (file.name.endsWith('.tif') || file.name.endsWith('.tiff')) {
        await onTifUpload(file);
      } else {
        const reader = new FileReader();
        reader.onload = (e) => {
          const parsedData = JSON.parse(e.target.result); // Assumes KML/GeoJSON parsing
          onDataParsed(parsedData);
        };
        reader.readAsText(file);
      }
    } catch (err) {
      toast.error(`File processing failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mb-4">
      <label className="block text-gray-700 font-medium mb-2">Upload File</label>
      <input
        type="file"
        accept={accept}
        onChange={handleFileChange}
        disabled={uploading}
        className={`w-full p-2 border rounded-lg ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      />
      {uploading && (
        <p className="mt-2 text-blue-600 flex items-center">
          <svg
            className="animate-spin h-5 w-5 mr-2"
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
          Uploading...
        </p>
      )}
    </div>
  );
}

export default FileUploader;