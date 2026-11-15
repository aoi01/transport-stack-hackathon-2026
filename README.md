# Transport Stack Hackathon 2026 — Doshisha University (Miyazaki Seminar)

Open-source tools for Delhi buses and metro, built for the
[Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/).

チーム向けの背景・課題整理・データ状況は [`docs/context.md`](docs/context.md) を参照。

## Problem

Phase 1: Problem 2 — Crowdedness-aware journey planner (tentative)

## Data

Data comes from [Delhi Transport Stack](https://delhi.transportstack.in) and is **not** committed (see `.gitignore`).
Place downloaded files under `data/raw/`:

| Folder | Dataset | Size | Status (2026-11-15) |
|---|---|---|---|
| `data/raw/bus_gps/` | Bus GPS, DTC, Oct 2026 (hackathon, public link) | 16.1 GB .7z / 124 GB unpacked | Available, not downloaded |
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
