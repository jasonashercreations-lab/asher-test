# Raspberry Pi deployment

Run the scoreboard service on a Pi. Open the editor from any browser on your LAN.

## Install

```bash
# Install system deps
sudo apt update && sudo apt install -y python3-venv python3-pip git

# Clone or copy the project
sudo git clone https://your-fork-or-tarball /opt/nhlsb
cd /opt/nhlsb

# Build the frontend (one-time)
sudo apt install -y nodejs npm
(cd frontend && npm install && npm run build)

# Set up Python venv
cd backend
python3 -m venv ../.venv
../.venv/bin/pip install -e .
```

## LED matrix support

Install Henner Zeller's `rpi-rgb-led-matrix` Python bindings per upstream:
https://github.com/hzeller/rpi-rgb-led-matrix

Then wire up the `MatrixOutput` device in the Output panel of the editor.

## Run as a service

```bash
sudo cp /opt/nhlsb/docs/nhlsb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nhlsb
sudo systemctl start nhlsb
sudo systemctl status nhlsb
```

## Open the editor

From any device on your network:

```
http://<pi-hostname-or-ip>:8765/
```

## Troubleshooting

- `journalctl -u nhlsb -f` to watch logs
- Listen on `0.0.0.0` (already in the unit file) to allow remote access
- Open port 8765 in `ufw` if you have a firewall enabled
