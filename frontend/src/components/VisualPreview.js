// src/components/VisualPreview.js
import React, { useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { toast } from "react-toastify";

function VisualPreview() {
  const [features, setFeatures] = useState(null);
  const [loading, setLoading] = useState(false);

  // VisualPreview.js
const handleFileUpload = async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  setLoading(true);
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/visual-preview`, {
      method: "POST",
      headers: {
        "x-api-key": process.env.REACT_APP_API_KEY,
      },
      body: formData,
    });

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    setFeatures(data);
    toast.success("Preview loaded successfully!");
  } catch (err) {
    toast.error(`Error: ${err.message}`);
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="mt-6">
      <input type="file" accept=".kml,.geojson,.shp" onChange={handleFileUpload} />
      {loading && <p className="text-sm text-blue-500 mt-2">Loading map preview...</p>}
      {features && (
        <MapContainer center={[20, 78]} zoom={4} className="h-96 mt-4 rounded-xl shadow">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <GeoJSON data={features} />
        </MapContainer>
      )}
    </div>
  );
}

export default VisualPreview;
