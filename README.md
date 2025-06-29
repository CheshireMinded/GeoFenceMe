# GeoFenceMe

**GeoFenceMe** is a real-time network and location-based geofencing web application. It allows you to
monitor devices entering or exiting custom-defined IP and GPS-based zones using a live dashboard with
Leaflet.js map integration.

## Features
- Admin login and session-based access control
- Real-time device scanning via ARP
- Define GPS zones directly on a map (no GPS walk required)
- Draggable, persistent map markers with labels
- Manage Trusted / Untrusted MAC addresses
- Device logs & real-time zone entry alerts
- Email or audio alert support
- Address geocoding + auto-pan
- Optional real-time geolocation reporting via browser

---

## Requirements
- Python 3.8+
- Flask
- Requests
- Shapely
- Aplay (sudo apt install alsa-utils on Linux)

---

## Installation
git clone https://github.com/yourusername/geofenceme.git
cd geofenceme

python3 -m venv venv
source venv/bin/activate

pip install flask requests shapely

---

## Run the App
python app.py
Then visit: http://127.0.0.1:5000

---

## Admin Login

| Username | Password |
|----------|----------|
| `admin`  | `password` |

You can change these credentials in your `app.py` file:

---

## 🗺️ Using the Zone Map

### ➕ Draw Zones
- Open the **Zone Map** from the dashboard.
- Use the polygon tool to draw a geofence.
- You'll be prompted to name the zone.
- Zones are saved to `zones.json`.

### 📍 Add Markers
- Click anywhere on the map to drop a labeled marker.
- Markers are **draggable** and their position is **persistently saved**.
- Marker data is stored in `markers.json`.

### ❌ Clear All Markers
- Use the **"Clear Markers"** button below the map.
- A confirmation prompt will appear before deletion.

### 🔎 Address Search
- Enter a street, city, or full address in the input box.
- The map will pan to the matched location using **Nominatim (OpenStreetMap)** geocoding.

## Optional: Real-Time Geolocation Alerts
    **Enable alerts when a browser enters a GPS zone:**
    
navigator.geolocation.watchPosition(pos => {
fetch('/report_location', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ lat: pos.coords.latitude, lon: pos.coords.longitude })
});
});

**Add this to your custom frontend if you want mobile-aware geofencing.**
Data Files
File	Purpose
zones.json	User-defined GPS/IP zones
| markers.json | Saved labeled draggable markers |
| known_devices.json | Trusted MAC addresses |
| device_log.txt | Log of events (entry/exits) |
| alert_config.json | Email/sound alert configuration |

---

## Alert Types
- None disables alerts
- Audio plays alert.wav using aplay
- Email sends email on zone entry/exit

Configure alert_config.json:
{
"method": "email",
"email": {
"from": "you@example.com",
"to": "admin@example.com",
"password": "your_app_password",
"smtp_server": "smtp.gmail.com"
}
}
Use Gmail app-specific passwords or SMTP relay.

---

## To-Do / Ideas
[ ] Push notifications via service workers
[ ] Secure admin password storage (e.g., bcrypt)
[ ] Mobile PWA support
[ ] Live tracking via device GPS
[ ] Zone time restrictions

---

## Developer Notes
Startup logs and device scans use system ARP table.
If using on a Raspberry Pi or similar network node, run the app with appropriate permissions to access ARP
data.

---

##License
MIT License
2025 Lauren Hall
Use this code freely, with attribution.

