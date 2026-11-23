# Data

All data comes from [Delhi Transport Stack](https://delhi.transportstack.in) and is covered by its terms of use, so it
is **not** in this repository (`data/` is in `.gitignore`). Download it yourself and place it as below. Detailed
working notes (Japanese): [`data_notes_ja.md`](data_notes_ja.md).

| Dataset | Used for | Where to put it | Size | How to get it |
|---|---|---|---|---|
| Bus GPS, DTC, 1–31 Oct 2026 | stop passages, ride times, waits, ground truth | `data/raw/bus_gps/` | 16.1 GB .7z / 124 GB unpacked | public link on the hackathon page (no approval) |
| Delhi Buses: GTFS Static (DTC / DoT), feed v32 | routes, stop sequences, timetable baseline | `data/raw/gtfs_static/` | 30 MB .zip | Delhi Transport Stack portal (open) |
| Delhi Buses: GTFS-RT vehicle positions | live waits when leaving now; recent link speeds | recorded by `tsh.recorder` to `data/raw/gtfs_rt/` | ~0.6 MB per call | portal (API key, header `x-api-key`) |
| Bus e-ticketing, Oct 2026 (~2.56 M tickets) | crowding per leg | `data/raw/ticketing/` | 66 MB .zip | public link on the hackathon page |

## Bus GPS

- One SQLite file per day (`bus_movements_YYYY_MM_DD.db`, ~4 GB each) in one non-solid 7z, so days can be extracted
  one at a time. Table `vehicle_feed`: `vehicle_id`, `lat`, `lng`, `speed`, `route_id`, `trip_id`, `timestamp`
  (UTC epoch), `date` and `time` (IST).
- `python scripts/gps_to_parquet.py all` extracts each day, fixes types, drops duplicates and writes
  `data/interim/bus_gps/date=YYYY-MM-DD/part.parquet` (~30 min for 31 days; 124 GB of SQLite becomes 5.7 GB).
- What we found: 38% of rows repeat the same GPS fix (`time` is the polling time, `timestamp` the GPS time, so
  duplicates are dropped on `timestamp`). Median gap between points of one bus is 11 s. Feed delay (`time` −
  `timestamp`) has a median of 22 s and a 90th percentile of 166 s. 6,652 vehicles and 2,305 routes over the month.
- GPS trip IDs do not join GTFS trip IDs. Buses change routes from day to day (a vehicle serves its most common route on
  only 32% of days), so routes come from the GPS `route_id`, never from the vehicle number.

## GTFS Static (v32)

- 2,574 directional routes (DTC 1,814, DIMTS 760), 6,862 stops, 80,357 trips. One `service_id` that runs every day, so
  the timetable has no weekday/weekend difference.
- Timetable times are not observed departures; they assume constant speed along the route.

## GTFS-RT

- `GET https://dts-backend.transportstack.in/api/dataset/otd/get-file?agency=delhi-buses&category=realtime_gtfs&filename=VehiclePositions.pb`
  with header `x-api-key`. Put the key in `.env` as `DTS_API_KEY=…` (never committed); check it with
  `python scripts/check_gtfs_rt.py`.
- Each call returns ~5,400–5,900 vehicles (DTC and DIMTS). The feed updates about every 25 s, so points per bus are
  ~33 s apart, three times coarser than the archived GPS. No history is provided, so we record it ourselves
  (`python -m tsh.recorder`).

## E-ticketing

- Columns: `passenger_count`, `amount`, `vehicle_number` (missing in 48.5% of rows), `ticket_type_id`,
  `start_stop_name`, `end_stop_name`, `route` (e.g. `8UP`), `created_at` (IST), `is_ac`.
- Digital tickets only (a few percent of all riders). Both stops are named by the passenger, so stop names are
  matched to GTFS stops (`tsh.stopmatch`, 91.4% of tickets matched to both stops on the route).
- Where the vehicle number is present, the ticket's route agrees with that vehicle's GPS route on 92.3% of tickets;
  most disagreements are GPS direction or route labels lagging behind.

## Google Maps comparison

`experiments/p1_google/compare.py` asks the Google Maps Platform Routes API (key in `.env` as
`GOOGLE_MAPS_API_KEY=…`). Google's responses are stored under `data/` and are not committed; only aggregate error
statistics are (`results/google_compare_metrics.json`).
