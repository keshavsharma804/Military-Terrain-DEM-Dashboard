// src/components/MapViewer.jsx
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { useEffect, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';

const MapViewer = () => {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    axios.get('http://localhost:5000/api/layers')
      .then(res => setGeoData(res.data.geojson))
      .catch(err => console.error(err));
  }, []);

  return (
    <MapContainer center={[28.6139, 77.2090]} zoom={6} style={{ height: "500px" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {geoData && <GeoJSON data={geoData} />}
    </MapContainer>
  );
};

export default MapViewer;
