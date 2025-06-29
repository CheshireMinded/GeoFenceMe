import subprocess
import time
import json
import os
from datetime import datetime

# Path to known devices file
KNOWN_DEVICES_FILE = 'known_devices.json'
LOG_FILE = 'device_log.txt'
SCAN_INTERVAL = 10  # seconds


def load_known_devices():
    if os.path.exists(KNOWN_DEVICES_FILE):
        with open(KNOWN_DEVICES_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_log(entry):
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def scan_network():
    # Run arp to get devices on local network
    output = subprocess.check_output(['arp', '-a']).decode()
    devices = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            ip = parts[1].strip('()')
            mac = parts[3]
            devices.append({'ip': ip, 'mac': mac})
    return devices


def main():
    known_devices = load_known_devices()
    seen_macs = set()

    while True:
        print("[+] Scanning network...")
        devices = scan_network()

        for device in devices:
            mac = device['mac']
            if mac not in seen_macs:
                seen_macs.add(mac)
                if mac in known_devices:
                    print(f"[KNOWN] {device['ip']} - {mac}")
                else:
                    print(f"[UNKNOWN] {device['ip']} - {mac}")
                    log_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'ip': device['ip'],
                        'mac': mac,
                        'status': 'unknown'
                    }
                    save_log(log_entry)
        time.sleep(SCAN_INTERVAL)


if __name__ == '__main__':
    main()
