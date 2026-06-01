#!/bin/bash
# Start dashboard server + receiver together. Ctrl+C stops both.
# Usage: ./start.sh [camera-ip]
#   or:  ESP32_CAM_IP=192.168.1.23 ./start.sh

cd "$(dirname "$0")"

export ESP32_CAM_IP="${1:-${ESP32_CAM_IP:-192.168.1.23}}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Industrial Anomaly Detection System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Dashboard : http://localhost:8000"
echo "  Camera IP : $ESP32_CAM_IP"
echo "  Press Ctrl+C to stop everything."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

dashboard/.venv/bin/uvicorn dashboard.server:app --host 0.0.0.0 --port 8000 \
    > /tmp/anomaly-dashboard.log 2>&1 &
DASHBOARD_PID=$!

cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$DASHBOARD_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

python3 receiver/receiver.py

cleanup
