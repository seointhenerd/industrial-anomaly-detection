"""FastAPI dashboard server for Industrial Anomaly Detection."""

import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
SNAPSHOTS   = ROOT / "snapshots"
STATIC_DIR  = Path(__file__).parent / "static"
INDEX_HTML  = STATIC_DIR / "index.html"

app = FastAPI(title="Anomaly Detection Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=404, detail="index.html not built yet")
    return HTMLResponse(INDEX_HTML.read_text())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/sensors")
def get_sensors():
    path = DATA_DIR / "sensor_log.csv"
    if not path.exists():
        return []
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[-50:]


@app.get("/api/anomalies")
def get_anomalies():
    path = DATA_DIR / "anomaly_log.csv"
    if not path.exists():
        return []
    with path.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("timestamp")]
    rows = rows[-20:]
    rows.reverse()
    for row in rows:
        # CSV header may lack snapshot_file (written before that column was added);
        # DictReader puts the extra value under the None restkey in that case.
        if None in row:
            extras = row.pop(None)
            row["snapshot_file"] = extras[0] if extras else ""
        row.setdefault("snapshot_file", "")
    return rows


@app.get("/api/status")
def get_status():
    sensor_path  = DATA_DIR / "sensor_log.csv"
    anomaly_path = DATA_DIR / "anomaly_log.csv"
    if not sensor_path.exists():
        return {"status": "unknown", "timestamp": ""}
    with sensor_path.open(newline="") as f:
        sensor_rows = [r for r in csv.DictReader(f) if r.get("timestamp")]
    if not sensor_rows:
        return {"status": "unknown", "timestamp": ""}
    latest_ts = sensor_rows[-1]["timestamp"]
    if not anomaly_path.exists():
        return {"status": "ok", "timestamp": latest_ts}
    with anomaly_path.open(newline="") as f:
        anomaly_rows = [r for r in csv.DictReader(f) if r.get("timestamp")]
    is_anomaly = bool(anomaly_rows) and anomaly_rows[-1]["timestamp"] == latest_ts
    return {"status": "anomaly" if is_anomaly else "ok", "timestamp": latest_ts}


@app.get("/api/latest-snapshot")
def get_latest_snapshot():
    path = DATA_DIR / "anomaly_log.csv"
    if not path.exists():
        return {"snapshot_file": "", "timestamp": ""}
    with path.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("timestamp")]
    for row in reversed(rows):
        if None in row:
            extras = row.pop(None)
            row["snapshot_file"] = extras[0] if extras else ""
        row.setdefault("snapshot_file", "")
        if row["snapshot_file"]:
            return {"snapshot_file": row["snapshot_file"], "timestamp": row["timestamp"]}
    return {"snapshot_file": "", "timestamp": ""}


@app.get("/api/snapshots/{filename}")
def get_snapshot(filename: str):
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = SNAPSHOTS / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(str(path), media_type="image/jpeg")
