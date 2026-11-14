# Transport Stack Hackathon 2026 — Doshisha University (Miyazaki Seminar)

Open-source tools for Delhi buses and metro, built for the
[Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/).

チーム向けの背景・課題整理・データ状況は [`docs/context.md`](docs/context.md) を参照。

## Problem

Phase 1: Problem 2 — Crowdedness-aware journey planner (tentative)

## Data

Data comes from [Delhi Transport Stack](https://delhi.transportstack.in) and is **not** committed (see `.gitignore`).
Place downloaded files under `data/raw/`:

| Folder | Dataset | Status |
|---|---|---|
| `data/raw/gtfs_static/` | Delhi Buses: GTFS Static Data v1 (DTC / DoT) | Downloaded |
| `data/raw/gtfs_rt/` | Delhi Buses: GTFS-RT feed (API) | Subscribed |
| `data/raw/metro_footfall/` | Delhi Metro: Hourly Footfall (DMRC) | Approval pending |
| `data/raw/ticketing/` | E-ticketing / ETM data (hackathon) | Awaiting access details |

## Key dates (IST)

| Milestone | Date |
|---|---|
| Registration | 20 Nov 2026 23:59 |
| Phase 1 submission (proposal + working prototype) | 24 Nov 2026 18:29 |
| Finale at IIIT Delhi | 11 Dec 2026 |
