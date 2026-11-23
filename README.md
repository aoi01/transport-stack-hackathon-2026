# Delhi bus journey planner from observed GPS — Transport Stack Hackathon 2026

Team **Promon** (Doshisha University, Miyazaki Seminar) · Phase 1 submission for
**Problem 1: Real-time bus traffic model and journey planner**
([Transport Stack Hackathon 2026](https://delhi.transportstack.in/hackathon/)).

| Submission item | Where |
|---|---|
| Proposal | [`docs/proposal.md`](docs/proposal.md) |
| Technical note | [`docs/technical_note.md`](docs/technical_note.md) |
| Working prototype | `app/` (API + map UI) and `src/tsh/` (models), run instructions below |
| Demo video | uploaded with the submission form |
| Full lab notebook, every experiment incl. failures (Japanese) | [`docs/phase1_prototype.md`](docs/phase1_prototype.md) |

## In one paragraph

Delhi's GTFS timetable does not describe what buses do: ride times are off by 25%, and leaving at the latest time the
timetable allows gets you there on time only 30% of the time. We rebuilt **when every bus passed every stop** from the
October 2026 GPS (96% of passages), learned ride times and waits from those passages, use live GTFS-RT positions when
you leave now, and **replay every recommended journey on past days** to give a median time and an honest
"safe arrival" (85th percentile). Everything is validated on a held-out week by replaying the recommended journey on
that week's real GPS.

## Results (held-out week 25–31 Oct; trained on 1–24 Oct; tuning on 18–24 Oct only)

| | This prototype | GTFS timetable |
|---|---|---|
| Ride time, median abs. error (20,000 rides) | **9.4%** (10.5% without live data) | 25.2% |
| Wait + ride from a stop, median abs. error (3,000 cases) | **20.4%** | 36.5% |
| Door-to-door, **leaving now** (600 OD pairs, top option replayed on GPS) | **13.6%** | 25.3% |
| Door-to-door, **planning ahead** | **16.1%**; ±10 min 43.6%; picked the actually fastest 67.5% | 24.1% |
| "Safe" arrival met (target 85%) | 79.1% leaving now · 76.3% planning ahead | — |
| **Arrive by** a given time: arrived in time | **79.6%** | 29.6% (57% > 10 min late) |
| Query time | ~1–4 s | — |

How it works, the validation protocol, why the remaining error is mostly waiting (short-turning, line switching,
missed trips) and what did not work: [`docs/technical_note.md`](docs/technical_note.md).

## Run

```bash
pip install -r requirements.txt
# build passages and models from the raw data: docs/phase1_prototype.md, section 1 ("再現手順") and section 17
python -m uvicorn app.server:app --app-dir . --port 8000
```

- `http://localhost:8000/` — journey planner. Depart now / at a time / arrive by; sort by fastest, comfort
  (crowding-weighted) or fewest transfers. Each option shows walk, wait (and where it came from: live bus, turning-back
  bus, history), ride, the timetable's time, and a safe arrival.
- API: `GET /journeys?from=28.6676,77.2285&to=28.5494,77.2510&depart=2026-11-17T08:30` (or `&arrive=…`,
  `&sort=fewer_transfers`, `&realtime=false`). Interactive docs at `/docs`.
- `http://localhost:8000/passages` — stop-passage inspector: raw GPS of any trip, which point became each stop
  passage, all buses of the line moving together, per-stop detection rate, and a time–distance (Marey) diagram
  against the timetable.
- Live waits need a Delhi Transport Stack GTFS-RT key in `.env` (`DTS_API_KEY=…`); without it the planner uses history.

Code map: `src/tsh/passages*.py` (stop passages), `traveltime.py`, `seg_ml.py` (ride models), `waitmodel.py`,
`realtime.py`, `live_excess.py` (waits), `planner.py` (search, replay, calibration), `validate_*.py` (evaluation),
`experiments/` (one folder per investigation), `results/` (metrics JSON).

## Data

Data comes from [Delhi Transport Stack](https://delhi.transportstack.in) and is **not** committed (see `.gitignore`).
Place downloaded files under `data/raw/`:

| Folder | Dataset | Size |
|---|---|---|
| `data/raw/bus_gps/` | Bus GPS, DTC, Oct 2026 | 16.1 GB .7z / 124 GB unpacked |
| `data/raw/gtfs_static/` | Delhi Buses: GTFS Static (DTC / DoT), feed v32 | 30 MB .zip |
| — | Delhi Buses: GTFS-RT feed (API, `x-api-key`) | ~0.6 MB per call |
| `data/raw/ticketing/` | Bus e-ticketing, Oct 2026 (used for crowding, below) | 66 MB .zip |

Details: [`docs/data.md`](docs/data.md).

## Also in this repository: crowding (Problem 2 work)

The planner also shows expected crowding per leg (seat / standing / crowded probabilities) estimated from e-tickets:
91.4% of tickets matched to both stops on the GTFS route; week-to-week error 31% at route × segment × hour, of which
20% is the noise floor of app tickets alone. Details: `docs/phase1_prototype.md` sections 6–7, 13 and 15.

## Credits

- Open-source libraries: DuckDB, pandas, NumPy, Polars, PyArrow, LightGBM, SciPy, RapidFuzz, FastAPI, Uvicorn,
  Matplotlib, gtfs-realtime-bindings, py7zr, Leaflet, Material Symbols icons; map tiles © OpenStreetMap contributors.
- Data: Delhi Transport Stack (DTC bus GPS, GTFS static, GTFS-RT via Open Transit Data).
- AI tools: code, analyses and documents were developed with **Claude Code (Anthropic)** as an AI pair-programmer and
  research assistant. All reported numbers come from running the code in this repository on the hackathon data.
- Methods we build on are cited in the technical note and the lab notebook (e.g. quantile recalibration,
  Kuleshov et al. 2018; robust routing from past days, Böhmová et al. 2013/2015; optimizer's curse, Smith & Winkler 2006).
