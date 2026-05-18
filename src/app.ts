// src/app.ts

import { initializeMap, addMarkers } from './map';
import { businessLocations } from './data';

const initApp = () => {
    const map = initializeMap('map', 41.6488, -0.8891, 13); // Centered on Zaragoza
    addMarkers(map, businessLocations);
};

document.addEventListener('DOMContentLoaded', initApp);