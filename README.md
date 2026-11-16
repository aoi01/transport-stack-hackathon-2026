# Transport Stack Hackathon 2026 — Doshisha University (Miyazaki Seminar)

Open-source tools for Delhi buses and metro, built for the
[Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/).

チーム向けの背景・課題整理・データ状況は [`docs/context.md`](docs/context.md) を参照。

## Problem

Phase 1: we built working prototypes for **both** Problem 1 (bus travel-time planner from observed GPS) and Problem 2 (crowdedness-aware planner from ticket data), sharing one journey-planner API.
Process, methods and validation results: [`docs/phase1_prototype.md`](docs/phase1_prototype.md)（日本語）.

| | Held-out week (Oct 25–31) result |
|---|---|
| P1 in-vehicle time | median abs. error **10.0%** (ensemble of segment- and link-level LightGBM with recent preceding-bus data); GTFS timetable 25.9%. 85th-percentile "safe" time is calibrated (85.1% of rides arrive within it) |
| P1 wait / door-to-door | wait 28.9%, door-to-door 20.4% with live positions, opposite-direction trip chaining, and an "actual departures" timetable learned from October GPS for when no bus is visible (timetable 36.5%; GTFS timetable itself did not match actual departures) |
| P1 journey replay (600 OD pairs, planning ahead) | top option median error 35.5% vs timetable 43.0%; picked the actually fastest option 62% of the time |
| P2 ticket → stop matching (all Oct tickets) | 91.4% of tickets get both stops on the GTFS route (was 79.2%): abbreviation/transliteration rules, a number guard, and stop aliases learned from where the bus was (GPS) when each ticket was bought; matches agree with the GPS-based stop 96.6% of the time |
| P2 crowding | trip-level holdout: Poisson deviance −5.6% and correlation 0.47→0.53 with trip-based shrinkage; per-route expansion bounded by vehicle capacity; seat/standing/crowded probabilities |
| Planner | answers in ~1–4 s |

Process, methods and all experiments (including what did not work): [`docs/phase1_prototype.md`](docs/phase1_prototype.md) sections 10–12（日本語）. Literature review: [`reports/`](reports/).

### Run

```bash
pip install -r requirements.txt
# build data/models: see docs/phase1_prototype.md (section 1)
python -m uvicorn app.server:app --app-dir . --port 8000   # http://localhost:8000 , API docs at /docs
```

- `http://localhost:8000/` — journey planner (travel time + crowding).
- `http://localhost:8000/passages` — stop-passage inspector: for any route, day and trip, shows the bus's raw GPS points, the stops, which GPS point was taken as the passage of each stop (60 m rule), stops that were missed or rejected, a replay of the bus with every other bus on the same line (both directions) moving on the map at the same time, the share of trips in which each stop's passage was detected that day, and a time–distance (Marey) diagram of all trips that day against the timetable.

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
