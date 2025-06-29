from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
import subprocess
import json
import os
from datetime import datetime
import ipaddress
import smtplib
from email.mime.text import MIMEText
from functools import wraps
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# File paths
KNOWN_DEVICES_FILE = 'known_devices.json'
LOG_FILE = 'device_log.txt'
ZONES_FILE = 'zones.json'
LAST_SEEN_FILE = 'last_seen.json'
ALERT_CONFIG_FILE = 'alert_config.json'
MARKERS_FILE = 'markers.json'

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

# Templates
login_template = """
<!DOCTYPE html>
<html><body>
<h2>Login</h2>
{% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
<form method="post">
  Username: <input type="text" name="username"><br>
  Password: <input type="password" name="password"><br>
  <input type="submit" value="Login">
</form>
</body></html>
"""

dashboard_template = """
<!DOCTYPE html>
<html>
<head>
    <title>GeoFenceMe Dashboard</title>
    <style>
        body { font-family: Arial; margin: 2em; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 8px; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .unknown { background-color: #fdd; }
        .alert { background-color: #ffeb3b; }
    </style>
    <script>
        async function fetchDevices() {
            const res = await fetch('/devices');
            const data = await res.json();
            const table = document.getElementById('deviceTable');
            table.innerHTML = '<tr><th>IP</th><th>MAC</th><th>Status</th><th>Zone</th><th>Inside</th><th>Action</th></tr>';
            data.devices.forEach(dev => {
                let buttonLabel = dev.status === 'unknown' ? 'Trust' : 'Untrust';
                let row = `<tr class="${dev.status === 'unknown' ? 'unknown' : ''} ${!dev.inside ? 'alert' : ''}">` +
                    `<td>${dev.ip}</td><td>${dev.mac}</td><td>${dev.status}</td><td>${dev.zone}</td><td>${dev.inside}</td>` +
                    `<td><button onclick="toggleTrust('${dev.mac}', '${dev.status}')">${buttonLabel}</button></td></tr>`;
                table.innerHTML += row;
            });
        }

        async function toggleTrust(mac, status) {
            const method = status === 'unknown' ? 'POST' : 'DELETE';
            await fetch('/whitelist', {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mac: mac })
            });
            fetchDevices();
        }

        async function setAlertMethod(method) {
            await fetch('/alerts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method })
            });
        }

        window.onload = () => {
            fetchDevices();
            setInterval(fetchDevices, 10000);
        }
    </script>
</head>
<body>
    <h1>GeoFenceMe Dashboard</h1>
    <p><a href="/logout">Logout</a></p>
    <p><a href="/gps">Define GPS Zone</a> | <a href="/logs">View Logs</a> | <a href="/devices_by_mac">Device Manager</a> | <a href="/map">View Zone Map</a></p>
    <strong>Alert Method:</strong>
    <button onclick="setAlertMethod('none')">None</button>
    <button onclick="setAlertMethod('audio')">Audio</button>
    <button onclick="setAlertMethod('email')">Email</button>
    <br><br>
    <table id="deviceTable"></table>
</body>
</html>
"""

map_template = """
<!DOCTYPE html>
<html>
<head>
<title>Zone Map</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet-draw@1.0.4/dist/leaflet.draw.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/leaflet-draw@1.0.4/dist/leaflet.draw.js"></script>
<style>
  #map { height: 600px; }
  #addressInput { width: 300px; padding: 6px; font-size: 14px; position: relative; z-index: 1000; }
</style>
</head>
<body>
<h2>Zone Map</h2>
<div style="margin-bottom: 10px;">
  <input type="text" id="addressInput" placeholder="Enter address" />
  <button onclick="geocodeAddress()">Go</button>
  <button onclick="clearMarkers()">Clear Markers</button>
</div>
<div id="map"></div>
<script>
const map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
    edit: { featureGroup: drawnItems },
    draw: { polygon: true, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
});
map.addControl(drawControl);

// Handle zone drawing
map.on('draw:created', function (e) {
    const layer = e.layer;
    const coords = layer.getLatLngs()[0].map(c => ({ lat: c.lat, lon: c.lng }));
    const name = prompt("Zone name:");
    if (name) {
        fetch('/save_gps_zone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, coords, type: 'gps' })
        }).then(() => location.reload());
    }
});

// Load zones
fetch('/zones').then(res => res.json()).then(data => {
    Object.entries(data).forEach(([name, zone]) => {
        if (zone.type === 'gps' && zone.coords.length > 2) {
            const poly = L.polygon(zone.coords.map(c => [c.lat, c.lon]), { color: 'blue' }).addTo(map);
            poly.bindPopup(name);
            drawnItems.addLayer(poly);
        }
    });
});

// Geocode address input
function geocodeAddress() {
    const addr = document.getElementById('addressInput').value;
    fetch(`/geocode?q=${encodeURIComponent(addr)}`)
        .then(res => res.json())
        .then(result => {
            if (result && result.lat && result.lon) {
                map.setView([parseFloat(result.lat), parseFloat(result.lon)], 16);
            } else {
                alert("Address not found");
            }
        })
        .catch(err => {
            console.error(err);
            alert("Failed to fetch location");
        });
}

// Click to add marker
map.on('click', function(e) {
    const label = prompt("Enter marker label:");
    if (label) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        L.marker([lat, lon]).bindPopup(label).addTo(map);
        fetch('/markers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lon, label })
        });
    }
});

// Load markers
fetch('/markers').then(res => res.json()).then(markers => {
    markers.forEach(m => {
        L.marker([m.lat, m.lon]).bindPopup(m.label).addTo(map);
    });
});

// Clear all markers
function clearMarkers() {
    if (confirm("Are you sure you want to remove all markers?")) {
        fetch('/markers', { method: 'DELETE' }).then(() => location.reload());
    }
}
</script>
<a href="/">Back to Dashboard</a>
</body>
</html>
"""



# Helper functions
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def load_json_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {path} is empty or corrupted. Returning empty dict.")
        return {}


def save_json_file(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def scan_network():
    try:
        output = subprocess.check_output(['arp', '-a']).decode()
    except:
        return []
    result = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            result.append({'ip': parts[1].strip('()'), 'mac': parts[3]})
    return result

def ip_in_range(ip, start, end):
    try:
        return ipaddress.IPv4Address(start) <= ipaddress.IPv4Address(ip) <= ipaddress.IPv4Address(end)
    except:
        return False

def get_zone(ip, zones):
    for name, z in zones.items():
        if z['type'] == 'ip_range' and ip_in_range(ip, z['start'], z['end']):
            return name, True
    return 'none', False

def play_audio(): os.system('aplay alert.wav')

def send_email(subject, msg):
    config = load_json_file(ALERT_CONFIG_FILE).get('email', {})
    m = MIMEText(msg)
    m['Subject'] = subject; m['From'] = config.get('from'); m['To'] = config.get('to')
    try:
        with smtplib.SMTP_SSL(config.get('smtp_server', 'smtp.gmail.com'), 465) as s:
            s.login(config.get('from'), config.get('password'))
            s.send_message(m)
    except Exception as e:
        print("Email failed:", e)

def alert_user(message):
    method = load_json_file(ALERT_CONFIG_FILE).get('method', 'none')
    if method == 'audio': play_audio()
    elif method == 'email': send_email("GeoFence Alert", message)

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['user'] = ADMIN_USERNAME
            return redirect('/')
        else:
            error = 'Invalid credentials'
    return render_template_string(login_template, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/')
@login_required
def dashboard():
    return render_template_string(dashboard_template)

@app.route('/devices')
@login_required
def devices():
    known = load_json_file(KNOWN_DEVICES_FILE)
    zones = load_json_file(ZONES_FILE)
    last = load_json_file(LAST_SEEN_FILE)
    raw = scan_network()
    updated = {}
    final = []
    for d in raw:
        mac = d['mac']
        status = 'known' if mac in known else 'unknown'
        zone, inside = get_zone(d['ip'], zones)
        prev = last.get(mac, {}).get('inside')
        if status == 'unknown' and (prev is None or prev != inside):
            alert_user(f"Unknown device {mac} ({d['ip']}) {'entered' if inside else 'exited'} zone {zone}")
        updated[mac] = {'inside': inside}
        final.append({**d, 'status': status, 'zone': zone, 'inside': inside})
    save_json_file(LAST_SEEN_FILE, updated)
    return jsonify({'devices': final})

@app.route('/whitelist', methods=['GET', 'POST', 'DELETE'])
@login_required
def whitelist():
    known = load_json_file(KNOWN_DEVICES_FILE)
    if request.method == 'GET': return jsonify(known)
    mac = request.json.get('mac')
    if request.method == 'POST': known[mac] = 'Trusted'; save_json_file(KNOWN_DEVICES_FILE, known)
    elif request.method == 'DELETE': known.pop(mac, None); save_json_file(KNOWN_DEVICES_FILE, known)
    return jsonify({'status': 'ok'})

@app.route('/alerts', methods=['POST'])
@login_required
def alerts():
    data = request.json
    config = load_json_file(ALERT_CONFIG_FILE)
    config['method'] = data.get('method', 'none')
    save_json_file(ALERT_CONFIG_FILE, config)
    return jsonify({'status': 'updated'})

@app.route('/markers', methods=['GET', 'POST', 'DELETE'])
def markers():
    if request.method == 'GET':
        return jsonify(load_json_file(MARKERS_FILE))
    elif request.method == 'POST':
        data = request.get_json()
        markers = load_json_file(MARKERS_FILE)
        markers.append(data)
        save_json_file(MARKERS_FILE, markers)
        return jsonify({'status': 'saved'})
    elif request.method == 'DELETE':
        save_json_file(MARKERS_FILE, [])
        return jsonify({'status': 'cleared'})
        
@app.route('/markers/update', methods=['POST'])
def update_marker():
    data = request.get_json()
    if not all(k in data for k in ('label', 'lat', 'lon')):
        return jsonify({'error': 'Invalid data'}), 400

    markers = load_json_file(MARKERS_FILE)
    updated = False
    for m in markers:
        if m.get('label') == data['label']:
            m['lat'] = data['lat']
            m['lon'] = data['lon']
            updated = True
            break

    if updated:
        save_json_file(MARKERS_FILE, markers)
        return jsonify({'status': 'updated'})
    else:
        return jsonify({'error': 'Marker not found'}), 404


@app.route('/logs')
@login_required
def logs():
    if not os.path.exists(LOG_FILE): return jsonify([])
    return jsonify([json.loads(line) for line in open(LOG_FILE) if line.strip()])

@app.route('/devices_by_mac')
@login_required
def device_manager():
    return jsonify(load_json_file(KNOWN_DEVICES_FILE))

@app.route('/gps')
@login_required
def gps_page():
    return render_template_string("<h1>GPS Zone Definition Coming Soon</h1><a href='/'>Back</a>")

@app.route('/save_gps_zone', methods=['POST'])
@login_required
def save_gps_zone():
    data = request.get_json()
    zones = load_json_file(ZONES_FILE)
    zones[data['name']] = { 'type': data.get('type', 'gps'), 'coords': data['coords'] }
    save_json_file(ZONES_FILE, zones)
    return jsonify({'status': 'saved'})

@app.route('/map')
@login_required
def show_map():
    return render_template_string(map_template)

@app.route('/zones')
@login_required
def get_zones():
    return jsonify(load_json_file(ZONES_FILE))

@app.route('/geocode')
def geocode():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Missing query'}), 400

    try:
        r = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={"format": "json", "q": query},
            headers={"User-Agent": "GeoFenceMe/1.0"}
        )
        data = r.json()
        if r.ok and data:
            return jsonify(data[0])
        else:
            return jsonify({'error': 'Address not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

