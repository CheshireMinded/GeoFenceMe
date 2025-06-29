from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this in production!

GPS_ZONES_FILE = 'gps_zones.json'
USERS_FILE = 'users.json'

# Dummy user credentials for demo (replace or load from secure file in production)
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {"admin": "password123"}

login_template = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
  <h2>Login</h2>
  <form method="POST">
    Username: <input name="username" type="text" /><br>
    Password: <input name="password" type="password" /><br>
    <button type="submit">Login</button>
  </form>
  {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
</body>
</html>
"""

gps_zone_template = """
<!DOCTYPE html>
<html>
<head>
  <title>GPS Zone Creator</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: Arial, sans-serif; padding: 2em; }
    button { padding: 10px; margin: 5px; }
    pre { background: #f4f4f4; padding: 10px; }
  </style>
  <script>
    let coordinates = [];

    function addPoint() {
      if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
      }

      navigator.geolocation.getCurrentPosition(position => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        coordinates.push([lat, lon]);
        updateDisplay();
      }, () => {
        alert("Unable to retrieve your location");
      });
    }

    function updateDisplay() {
      document.getElementById("output").textContent = JSON.stringify(coordinates, null, 2);
    }

    async function saveZone() {
      const name = prompt("Enter a name for this zone:");
      if (!name || coordinates.length < 3) {
        alert("You must provide a name and at least 3 points.");
        return;
      }

      const res = await fetch('/save-gps-zone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, coordinates })
      });

      const msg = await res.json();
      alert(msg.status || msg.error);
    }
  </script>
</head>
<body>
  <h1>GPS Zone Creator</h1>
  <p>Walk your boundary and press "Add Point" at key locations.</p>
  <button onclick="addPoint()">Add Point</button>
  <button onclick="saveZone()">Save Zone</button>
  <a href="/logout">Logout</a>
  <h3>Current Coordinates:</h3>
  <pre id="output"></pre>
</body>
</html>
"""

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['user'] = username
            return redirect(url_for('gps_zone_page'))
        else:
            error = 'Invalid credentials'
    return render_template_string(login_template, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/define-gps-zone')
def gps_zone_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template_string(gps_zone_template)

@app.route('/save-gps-zone', methods=['POST'])
def save_gps_zone():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    name = data.get('name')
    coordinates = data.get('coordinates')

    if not name or not coordinates or len(coordinates) < 3:
        return jsonify({'error': 'Invalid input'}), 400

    if os.path.exists(GPS_ZONES_FILE):
        with open(GPS_ZONES_FILE, 'r') as f:
            zones = json.load(f)
    else:
        zones = {}

    zones[name] = {
        'type': 'gps_polygon',
        'coordinates': coordinates,
        'created': datetime.now().isoformat()
    }

    with open(GPS_ZONES_FILE, 'w') as f:
        json.dump(zones, f, indent=2)

    return jsonify({'status': f'Zone "{name}" saved successfully.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=True)
