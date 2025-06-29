# GeoFenceMe

**GeoFenceMe** is a real-time network and location-based geofencing web application. It allows you to monitor devices entering or exiting custom-defined IP zones and GPS-based geofences using a clean web UI with Leaflet.js integration.

---

## Features

-  **Admin login and session-based access control**
-  **Real-time network device scanning (ARP)**
-  **GPS zone creation directly on a map**
-  **Draggable, persistent markers for reference points**
-  **Trusted/Untrusted device management**
-  **Visual zone display with Leaflet**
-  **Device logs & alerts (email/audio/none)**
-  **Address geocoding and auto-pan**
-  **Device geolocation tracking (optional)**
-  **Zone entry notifications based on location**

---

## Requirements

- Python 3.8+
- Flask
- Requests
- Shapely
- Aplay (for audio alerts)
- A modern web browser

---

## Installation

1. **Clone this repo**:
   git clone https://github.com/yourusername/geofenceme.git
   cd geofenceme

---

##  Create and activate a virtual environment:
  python3 -m venv venv
  source venv/bin/activate

--0

##
  **Install Python dependencies:**
  pip install flask requests shapely

---

##  Running the App:
python app.py

  **Then Open your Browser to:
    http://127/0/0/1:5000

      ADMIN_USERNAME = 'admin'
      ADMIN_PASSWORD = 'password'

      these can be changed in app.py

---

##Zone and Marker Tools:
  **To Draw Zones:
    Visit the Zone Map, Use the Polygon tool to draw the zone, Name and then Save.
  
  **To Add Markers:
    Click Anywhere on the Map, Enter a label and marker is saved, Drag to Move and Location is Updated, Click 'Clear Markers' to remove.

  **Search Address:
     Enter an address (ex: Seattle, WA), Map will auto-pan to that location.

---

##Real-Time Geofence Alerts (Optional)
  To enable:
      1. Allow location access in Browser
      2. Frontend sends coordinates
      3. Backend checks zones and responds if any device is inside.

---

##Alerts
    Set your chosen alert method from the dashboard
        1. None
        2. Audio
        3. Email

---

Enhancements that can still be done:
    Mobile PWA Support
    Push Notifications
    User-defined geofences via mobile location
    Role-based Access Control

---

##License
MIT License
© 2025 Lauren Hall








   


