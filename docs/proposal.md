# Proposal — Problem 1: a bus journey planner for Delhi that tells the truth about waiting

Team Promon (Doshisha University, Miyazaki Seminar) · Transport Stack Hackathon 2026, Phase 1

## The problem

A Delhi bus rider asks two questions: *how long will this take* and *when should I leave*. Today's answers come
from the GTFS timetable, and the timetable is not what happens on the road:

- Ride times in the timetable are off by a median **25%** against observed October 2026 GPS, most in the evening peak.
- Waits are worse. Buses bunch and gaps are irregular (headway coefficient of variation ≈ 1.1), only about 85–95% of
  planned trips run (CAG audit of DTC, 2024), and most buses do not run the full route: 36% of runs start mid-route and
  86% of vehicles serve more than one line in a day.
- Result: if you leave at the latest time the timetable allows, you arrive on time **29.6%** of the time, and 57% of
  the time you are more than 10 minutes late (our replay of 600 trips on the held-out week).

Riders cope by leaving very early or by not taking the bus. Neither shows up in a timetable.

## Our solution

A journey planner and API (`GET /journeys`) whose every number is learned from what Delhi's buses actually did:

1. **Stop passages from raw GPS** — when each bus passed each stop, rebuilt for all 31 days of October
   (96% of passages detected, by projecting GPS onto the route and interpolating).
2. **Ride times** from LightGBM models on those passages, corrected by how slow the preceding buses were in the last
   30 minutes (live GTFS-RT).
3. **Waits** from an *observed* passage timetable when planning ahead, and from live positions when leaving now:
   a bus visible upstream, or a bus that will turn back at the terminus.
4. **Honest uncertainty**: each option is replayed on every past day of the same type, recalibrated so that the shown
   time is a true median and the **"safe arrival" is met 85% of the time** in calibration. Options that failed on most
   past days are pushed down — the planner learns which buses do not come.
5. **Arrive-by search**: the latest departure that made it on 85% of past days.

## Evidence (held-out week, never used in building)

| | Ours | Timetable |
|---|---|---|
| Ride time error (median) | **9.4%** | 25.2% |
| Door-to-door, leaving now (median) | **13.6%** | 25.3% |
| Door-to-door, planning ahead (median) | **16.1%** | 24.1% |
| Arrive-by: arrived in time | **79.6%** | 29.6% |

Full method and validation: [`technical_note.md`](technical_note.md).

## What is new

- We evaluate the *journey the planner recommends*, by replaying it on real GPS. This is how a rider experiences the
  planner, and it exposes failure modes that per-segment accuracy hides: recommending buses that never come, and the
  optimism of always picking the shortest estimate. We measured and fixed both.
- We explain *why* waits are hard in Delhi from the data itself (short-turning, line switching at midday crew
  changes, missed trips) and report a realistic error floor instead of over-fitting a point forecast.
- Everything runs on open data the city already publishes: GTFS, GTFS-RT positions and archived GPS. No commercial
  traffic feed.

## Feasibility

- Works today: FastAPI server, map UI, 1–4 s per query on a laptop; GTFS-RT is polled live.
- Nightly rebuild: new days of GPS are turned into passages with DuckDB in seconds to minutes per day; models are
  retrained from the passages.
- The API returns structured JSON (times, safe arrival, wait source, crowding), ready for Chalo/OTD-style apps.

## Users and impact

- Riders: a departure time they can trust (80% on time on a held-out week vs 30% with the timetable), and a planner that stops sending them to buses
  that do not run.
- Operators and DTC/DIMTS planners: the same passage data shows where buses turn back early, where gaps open up and
  which scheduled trips never run — the stop-passage inspector (`/passages`) already visualises this per route and day.

## Next (Phase 2)

1. Learn when and where each line short-turns, so a visible bus is only counted if it will reach the user's stop.
2. Separate Saturday from Sunday (Saturday is 4–8% slower) and add more calibration weeks to close the gap between
   the 85% target and the 76–80% reached on the held-out week.
3. Two-transfer search and street-network walking.
4. Feed passage-derived service reliability back to operators (missed trips, bunching) as a dashboard.
