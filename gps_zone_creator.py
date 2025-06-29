from flask import Flask, jsonify, request, render_template_string
import subprocess
import json
import os
from datetime import datetime
import ipaddress
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

KNOWN_DEVICES_FILE = 'known_devices.json'
LOG_FILE = 'device_log.txt'
ZONES_FILE = 'zones.json'
LAST_SEEN_FILE = 'last_seen.json'
ALERT_CONFIG_FILE = 'alert_config.json'

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>GeoFenceMe Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .unknown { background-color: #fdd; }
        .alert { background-color: #ffeb3b; }
    </style>
    <script>
        async function fetchDevices() {
            const res = await fetch('/devices');
            const data = await res.json();
            const table = document.getElementById('deviceTable');
            table.innerHTML = '<tr><th>IP</th><th>MAC</th><th>Status</th><th>Zone</th><th>Inside</th></tr>';
            data.devices.forEach(dev => {
                let row = `<tr class="${dev.status === 'unknown' ? 'unknown' : ''} ${!dev.inside ? 'alert' : ''}">` +
                    `<td>${dev.ip}</td>` +
                    `<td>${dev.mac}</td>` +
                    `<td>${dev.status}</td>` +
                    `<td>${dev.zone}</td>` +
                    `<td>${dev.inside}</td>` +
                    `</tr>`;
                table.innerHTML += row;
            });
        }

        async function setAlertMethod(method) {
            await fetch('/alerts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method: method })
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
    <div>
        <strong>Alert Method:</strong>
        <button onclick="setAlertMethod('none')">None</button>
        <button onclick="setAlertMethod('audio')">Audio</button>
        <button onclick="setAlertMethod('email')">Email</button>
    </div>
    <br>
    <table id="deviceTable"></table>
    <br>
    <a href="/admin">Go to Device Manager</a>
</body>
</html>
"""

admin_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Device Manager</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
    <script>
        async function loadDevices() {
            const res = await fetch('/whitelist');
            const data = await res.json();
            const table = document.getElementById('deviceTable');
            table.innerHTML = '<tr><th>MAC Address</th><th>Label</th><th>Action</th></tr>';
            Object.entries(data).forEach(([mac, label]) => {
                table.innerHTML += `<tr><td>${mac}</td><td>${label}</td><td><button onclick="untrustDevice('${mac}')">Untrust</button></td></tr>`;
            });
        }

        async function trustDevice() {
            const mac = prompt("Enter MAC address to trust:");
            if (!mac) return;
            await fetch('/whitelist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mac })
            });
            loadDevices();
        }

        async function untrustDevice(mac) {
            await fetch('/whitelist', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mac })
            });
            loadDevices();
        }

        window.onload = loadDevices;
    </script>
</head>
<body>
    <h1>Trusted Devices</h1>
    <button onclick="trustDevice()">Add New Trusted Device</button>
    <table id="deviceTable"></table>
    <br>
    <a href="/">Back to Dashboard</a>
</body>
</html>
"""

def load_json_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def save_json_file(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def save_log(entry):
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def send_email_alert(subject, message):
    config = load_json_file(ALERT_CONFIG_FILE).get('email', {})
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = config.get('from')
    msg['To'] = config.get('to')

    try:
        with smtplib.SMTP_SSL(config.get('smtp_server', 'smtp.gmail.com'), 465) as server:
            server.login(config.get('from'), config.get('password'))
            server.send_message(msg)
    except Exception as e:
        print(f"Email alert failed: {e}")

def play_audio_alert():
    os.system('aplay alert.wav')

def alert_user(message):
    method = load_json_file(ALERT_CONFIG_FILE).get('method', 'none')
    if method == 'audio':
        play_audio_alert()
    elif method == 'email':
        send_email_alert("GeoFence Alert", message)

def scan_network():
    try:
        output = subprocess.check_output(['arp', '-a']).decode()
    except FileNotFoundError:
        return []
    devices = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            ip = parts[1].strip('()')
            mac = parts[3]
            devices.append({'ip': ip, 'mac': mac})
    return devices

def ip_in_range(ip, start, end):
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        return ipaddress.IPv4Address(start) <= ip_obj <= ipaddress.IPv4Address(end)
    except:
        return False

def get_zone_for_ip(ip, zones):
    for name, zone in zones.items():
        if zone['type'] == 'ip_range' and ip_in_range(ip, zone['start'], zone['end']):
            return name, True
    return 'none', False

@app.route('/')
def dashboard():
    return render_template_string(html_template)

@app.route('/admin')
def admin():
    return render_template_string(admin_template)

@app.route('/devices')
def get_devices():
    known_devices = load_json_file(KNOWN_DEVICES_FILE)
    zones = load_json_file(ZONES_FILE)
    last_seen = load_json_file(LAST_SEEN_FILE)
    raw_devices = scan_network()
    seen = []
    updated_seen = {}

    for dev in raw_devices:
        mac = dev['mac']
        status = 'known' if mac in known_devices else 'unknown'
        zone, inside = get_zone_for_ip(dev['ip'], zones)
        previous = last_seen.get(mac, {}).get('inside', None)

        if status == 'unknown' and (previous is None or previous != inside):
            alert_msg = f"Unknown device {mac} ({dev['ip']}) {'entered' if inside else 'exited'} zone {zone}"
            alert_user(alert_msg)
            save_log({
                'timestamp': datetime.now().isoformat(),
                'ip': dev['ip'],
                'mac': mac,
                'status': status,
                'zone': zone,
                'inside': inside,
                'event': 'entry' if inside else 'exit'
            })

        updated_seen[mac] = {'inside': inside}

        seen.append({
            'ip': dev['ip'],
            'mac': mac,
            'status': status,
            'zone': zone,
            'inside': inside
        })

    save_json_file(LAST_SEEN_FILE, updated_seen)
    return jsonify({'devices': seen})

@app.route('/whitelist', methods=['GET', 'POST', 'DELETE'])
def manage_whitelist():
    known = load_json_file(KNOWN_DEVICES_FILE)
    if request.method == 'GET':
        return jsonify(known)

    data = request.json
    mac = data.get('mac')
    if not mac:
        return jsonify({'error': 'No MAC provided'}), 400

    if request.method == 'POST':
        known[mac] = "Trusted Device"
        save_json_file(KNOWN_DEVICES_FILE, known)
    elif request.method == 'DELETE':
        if mac in known:
            del known[mac]
            save_json_file(KNOWN_DEVICES_FILE, known)
    return jsonify({'status': 'success'})

@app.route('/alerts', methods=['POST'])
def set_alert_method():
    data = request.json
    current = load_json_file(ALERT_CONFIG_FILE)
    current['method'] = data.get('method', 'none')
    save_json_file(ALERT_CONFIG_FILE, current)
    return jsonify({'status': 'alert method updated'})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE, 'r') as f:
        logs = [json.loads(line) for line in f if line.strip()]
    return jsonify(logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
