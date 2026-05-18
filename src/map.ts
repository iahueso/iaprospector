// src/map.ts

import L from 'leaflet';
import { businessLocations } from './data';

const map = L.map('map').setView([41.6488, -0.8891], 13); // Centered on Zaragoza

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
}).addTo(map);

businessLocations.forEach(location => {
    L.marker([location.lat, location.lng]).addTo(map)
        .bindPopup(location.name)
        .openPopup();
});