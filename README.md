# Zaragoza Map PWA

This project is a Progressive Web App (PWA) that displays a map of Zaragoza with various business locations marked on it. The application utilizes modern web technologies to provide a responsive and interactive user experience.

## Project Structure

```
zaragoza-map-pwa
├── public
│   ├── index.html          # Main HTML document
│   ├── manifest.json       # PWA manifest file
│   └── service-worker.js    # Service worker for offline capabilities
├── src
│   ├── app.ts              # Entry point of the application
│   ├── map.ts              # Functions to initialize and display the map
│   ├── data.ts             # Business location data
│   └── styles.css          # CSS styles for the application
├── package.json             # npm configuration file
├── tsconfig.json           # TypeScript configuration file
└── README.md               # Project documentation
```

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd zaragoza-map-pwa
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the application**:
   ```bash
   npm start
   ```

4. **Open your browser** and navigate to `http://localhost:3000` (or the specified port) to view the application.

## Features

- Displays a map of Zaragoza with markers for five random business locations.
- Offline capabilities through service worker.
- Responsive design for mobile and desktop devices.

## Technologies Used

- TypeScript
- HTML5
- CSS3
- [Mapping Library] (e.g., Leaflet or Google Maps)
- Progressive Web App (PWA) standards

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.