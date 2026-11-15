# Transport Stack Hackathon 2026 — Doshisha University (Miyazaki Seminar)

Open-source tools for Delhi buses and metro, built for the
[Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/).

チーム向けの背景・課題整理・データ状況は [`docs/context.md`](docs/context.md) を参照。

## Problem

Phase 1: we built working prototypes for **both** Problem 1 (bus travel-time planner from observed GPS) and Problem 2 (crowdedness-aware planner from ticket data), sharing one journey-planner API.
Process, methods and validation results: [`docs/phase1_prototype.md`](docs/phase1_prototype.md)（日本語）.

| | Held-out week (Oct 25–31) result |
|---|---|
| P1 in-vehicle time | median abs. error **11.5%** (GTFS timetable 25.9%) |
| P1 door-to-door incl. wait | 24.9% with live GPS (15.9% when the next bus is visible), 36.5% timetable |
| P2 crowding | train→test correlation **0.83** for high-confidence cells, crowding level agreement 74–80%, within one level 97% |
| Planner | 100% of 200 random OD pairs answered, 0.13 s median |

### Run

```bash
pip install -r requirements.txt
# build data/models: see docs/phase1_prototype.md (section 1)
python -m uvicorn app.server:app --app-dir . --port 8000   # http://localhost:8000 , API docs at /docs
```

## Data

Data comes from [Delhi Transport Stack](https://delhi.transportstack.in) and is **not** committed (see `.gitignore`).
Place downloaded files under `data/raw/`:

| Folder | Dataset | Size | Status (2026-11-15) |
|---|---|---|---|
| `data/raw/bus_gps/` | Bus GPS, DTC, Oct 2026 (hackathon, public link) | 16.1 GB .7z / 124 GB unpacked | Downloaded (checksum OK); extract one day at a time |
| `data/raw/ticketing/` | Bus e-ticketing, Oct 2026, ~2.56M tickets (hackathon, public link) | 66 MB .zip / 290 MB | Downloaded (checksum OK) |
| `data/raw/gtfs_static/` | Delhi Buses: GTFS Static (DTC / DoT), feed v32 | 30 MB .zip | Downloaded |
| — | Delhi Buses: GTFS-RT feed (API, `x-api-key`) | ~0.6 MB per call | Working (key in `.env`) |
| `data/raw/metro_footfall/` | Delhi Metro: Hourly Footfall (DMRC) | — | Approved, not downloaded |

Full inventory, access details and how to handle the large GPS archive: [`docs/data.md`](docs/data.md).

## Key dates (IST)

| Milestone | Date |
|---|---|
| Registration | 20 Nov 2026 23:59 |
| Phase 1 submission (proposal + working prototype) | 24 Nov 2026 18:29 |
| Finale at IIIT Delhi | 11 Dec 2026 |
