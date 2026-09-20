# SIH 26124 prototype handoff

## Run the interface

From a local clone:

```sh
git pull
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173. The default demo works without a backend. Use the motion button to pause animation; operating-system reduced-motion preferences are respected. The landing page uses sample Hyderabad observations. External map tiles require internet access.

For the connected workspace, run the backend in a second terminal:

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Select **Connect backend**, enter the workspace, and sign in. Development seeding creates `admin` / `admin123`; use these only with a local demo database. Vite proxies `/api` to port 8000. For a separate frontend deployment configure `VITE_API_BASE_URL` and the backend's CORS origins.

For a fresh non-demo environment, set `SEED_DEMO_DATA=false`, configure a private database, and run `python bootstrap_admin.py` from `backend`. Set strong unique secrets and `APP_ENV=production`. Production startup rejects default JWT secrets and enabled demo seeding. Turning seeding off does not delete demo accounts/data already in an existing database. Use a new database or explicitly replace those accounts before deployment. Configure TLS, backups, evidence retention and device credentials for deployment; these remain operational work.

## Changes

- Midnight/mint animated landing page, perspective map, scroll reveals, animated metrics, staggered entrances, page transitions, hover feedback and persistent motion control.
- Responsive analytical cards, traffic composition, GPS corridor journeys, route delay observations, model readiness and a connected-mode login.
- Backend polling with error/retry states; event and alert updates only report success after persistence.
- Authenticated operational APIs and evidence access; administrator-only registration; inactive users rejected; read-only roles cannot mutate operations.
- Idempotent edge event IDs, source timestamps, bus/camera validation and linked alerts. Traffic metadata creates traffic observations. Repeated observations do not artificially inflate cluster confidence.
- Optional recorded-video processing with GPS, local YOLO weights/ByteTrack, conservative redaction and durable metadata/evidence delivery. Failed uploads remain in the queue with backoff.
- Reports and model-health screens avoid fabricated accuracy, bandwidth savings and guaranteed privacy claims.

## Recorded video workflow

Run from the repository root in a Python environment with backend dependencies. Install `edge/requirements-inference.txt` for optional YOLO tracking/OCR. Supply your own trusted, validated local weights. GPS CSV columns: `seconds,latitude,longitude,speed_kmh`, with samples at least every 10 seconds. Start time must include a timezone.

```sh
python -m edge.run_video --video recording.mp4 --gps gps.csv \
  --start-time 2026-09-20T09:00:00+05:30 --bus-id 1 \
  --road-weights ml/artifacts/road_defect.pt \
  --traffic-weights ml/artifacts/yolov8n.pt
```

Without weights, road processing only generates unvalidated OpenCV candidates; vehicle tracking is unavailable. To sync, set `URBAN_API_TOKEN` to a valid operator JWT and add `--sync`. Optional `--save-evidence` requires a traffic model and blurs detected person/vehicle regions. Missed detections remain possible. Review images before sharing. Local evidence remains after delivery; implement a retention policy. The file queue supports one process per cache path and needs disk-capacity monitoring; it is not a multi-worker broker. Re-run sync after authentication/network recovery; failed items are retained.

## Requirement comparison and remaining work

| SIH requirement | Current implementation | Remaining evidence/work |
| --- | --- | --- |
| Multi-camera edge framework | Camera manager and position-aware video runner | Concurrent hardware streams, synchronization, long-running device service |
| Road defects / missing infrastructure | Detector integration, heuristic candidates, GIS views | Validated weights for every required class, including missing dividers/crossings/signboards and waterlogging |
| Vehicle detection / counting | Optional YOLO tracking, class counts, congestion samples | Field count accuracy, camera calibration, validated speed and bottleneck thresholds |
| Vulnerable pedestrians | Uncalibrated risk rules using person boxes and bus speed | School-child context and validated crossing/trajectory models |
| Rash driving / hit-and-run / ANPR | Existing incident/ANPR processor components and review UI | End-to-end temporal incident detection, plate localization/OCR integration in the video runner, validated tracking and confidence |
| GIS and road conditions | Event layers, road segments and congestion intensity cells | Validated road scoring and map-layer aggregation at fleet scale |
| Origin–destination and route delays | Bus GPS endpoint-crossing journeys and observed delays | Passenger/private-vehicle OD, historical baselines and prediction validation |
| Central evidence and alerts | Protected ingestion/evidence, persistence, operator review | Fine-grained per-device permissions, tamper-evident audit, retention automation, deployment hardening |
| Bandwidth / model accuracy | Explicitly unmeasured | Representative dataset evaluation and hardware/traffic benchmarks |

This is a stronger demonstrable prototype, not a completed or field-validated SIH solution. No model training or measured accuracy is claimed.

## Verification

Run `npm run build` and `npm run lint` in `frontend`; run `python -m pytest tests -q` from the repository root. Tests cover processor/simulator behavior, protected APIs, idempotent ingestion, persisted updates, evidence upload/retrieval, offline queue recovery and recorded-video execution. Synthetic video tests validate plumbing, not detection accuracy. Browser rendering must be checked on a machine where Chromium can start.
