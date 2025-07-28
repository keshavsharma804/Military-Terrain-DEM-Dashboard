const map = L.map('map').setView([28.55, 77.05], 12);

// Base layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Load GeoJSON
fetch('http://localhost:5000/api/restricted')
  .then(res => res.json())
  .then(data => {
    L.geoJSON(data, {
      style: { color: 'red', weight: 2 }
    }).addTo(map);
  });

// Load KML as GeoJSON (converted on backend)
fetch('http://localhost:5000/api/zones')
  .then(res => res.json())
  .then(data => {
    L.geoJSON(data, {
      style: { color: 'blue', weight: 2 }
    }).addTo(map);
  });
