# Transport Stack Hackathon 2026 — Doshisha University (Miyazaki Seminar)

Open-source tools for Delhi buses and metro, built for the
[Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/).

チーム向けの背景・課題整理・データ状況は [`docs/context.md`](docs/context.md) を参照。

## Problem

Phase 1: we built working prototypes for **both** Problem 1 (bus travel-time planner from observed GPS) and Problem 2 (crowdedness-aware planner from ticket data), sharing one journey-planner API.
Process, methods and validation results: [`docs/phase1_prototype.md`](docs/phase1_prototype.md)（日本語）.

| | Held-out week (Oct 25–31) result |
|---|---|
| P1 in-vehicle time | median abs. error **9.4%** (ensemble of segment- and link-level LightGBM with recent preceding-bus data; 10.5% from history only); GTFS timetable 25.2%. Stop passages are now interpolated along the route between GPS points (96% of passages detected, was 77% with the nearest point within 60 m), and all models and the ground truth were rebuilt on them (docs section 17) |
| P1 wait / door-to-door | wait 28.9%, door-to-door 20.4% with live positions, opposite-direction trip chaining, and an "actual departures" timetable learned from October GPS for when no bus is visible (timetable 36.5%; GTFS timetable itself did not match actual departures) |
| P1 journey replay (600 OD pairs, planning ahead) | top option median error **15.3%** vs timetable 23.8%; ±10 min 45.6%; picked the actually fastest option 67.8% of the time; top options whose bus never came 12.5%. Options are timed and ranked by replaying each one on past days of the same type (departure jittered ±10 min). Picking the shortest of several replays is optimistic, so the replay distribution is recalibrated on a calibration week inside the training period (quantile recalibration): the "safe" arrival (target 85%) was met by 84.4% in that week and **81.1%** in the held-out week. Same truth, previous version: 17.2% / 83.2% (docs sections 16–17) |
| P1 journey replay, arrive by a given time | Like Google Maps, you can ask for an arrival time. The departure is the latest one that arrived in time on 85% of past days of the same type, moved 2 min (direct) or 16 min (with a transfer) earlier, margins chosen on the calibration week. Leaving then, **79.4%** of top options arrived in time in the held-out week (target 85%). Leaving at the latest time the GTFS timetable allows, only 29.6% arrived in time and 56% were over 10 min late (docs 16.9, 17) |
| P1 journey replay, leaving now (live bus positions) | top option median error **13.8%** vs timetable 26.1%; versus planning ahead on the same 326 pairs 15.2% → 13.4%; picked the actually fastest option 72.7% of the time. A bus seen upstream is often missed by seconds or turns back early, so each option's time adds how far live waits were off in the training period. The "safe" arrival (target 85%) was met by 79.5% in the held-out week (docs 16.5–16.9, 17) |
| P2 ticket → stop matching (all Oct tickets) | 91.4% of tickets get both stops on the GTFS route (was 79.2%): abbreviation/transliteration rules, a number guard, and stop aliases learned from where the bus was (GPS) when each ticket was bought; matches agree with the GPS-based stop 96.6% of the time |
| P2 crowding | trip-level holdout: Poisson deviance −5.6% and correlation 0.47→0.53 with trip-based shrinkage; per-route expansion bounded by vehicle capacity; seat/standing/crowded probabilities |
| P2 week-to-week check (route × stop-to-stop segment × hour) | median error 31% (uncapped 33%), of which **20% is the noise floor**: two random halves of the held-out week's own tickets already differ that much, so ≤10% is not reachable at this granularity with app tickets alone. Busy segments (≥500 training tickets) reach 11.7% when buses and riders are both counted by the hour they pass the segment (was 18%). Details: docs section 15 |
| Planner | answers in ~1–4 s |

Process, methods and all experiments (including what did not work): [`docs/phase1_prototype.md`](docs/phase1_prototype.md) sections 10–17（日本語）. Literature review: [`reports/`](reports/).

### Run

```bash
pip install -r requirements.txt
# build data/models: see docs/phase1_prototype.md (section 1)
python -m uvicorn app.server:app --app-dir . --port 8000   # http://localhost:8000 , API docs at /docs
```

- `http://localhost:8000/` — journey planner (travel time + crowding). Search by departure or arrival time; sort by fastest, comfort (crowding-weighted) or fewest transfers. API: `GET /journeys?from=lat,lng&to=lat,lng&depart=2026-11-17T08:30` or `&arrive=2026-11-17T09:30`.
- `http://localhost:8000/passages` — stop-passage inspector: for any route, day and trip, shows the bus's raw GPS points, the stops, which GPS point was taken as the passage of each stop (60 m rule; the planner itself now uses interpolated passages, docs 17), stops that were missed or rejected, a replay of the bus with every other bus on the same line (both directions) moving on the map at the same time, the share of trips in which each stop's passage was detected that day, and a time–distance (Marey) diagram of all trips that day against the timetable.

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
