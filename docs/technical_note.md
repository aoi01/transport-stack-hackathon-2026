# Technical note — Problem 1: real-time bus travel-time model and journey planner for Delhi

Team Promon (Doshisha University, Miyazaki Seminar) · Transport Stack Hackathon 2026, Phase 1

This note is the short version. The full lab notebook (Japanese, every experiment including the ones that failed) is
[`phase1_prototype.md`](phase1_prototype.md); the proposal is [`proposal.md`](proposal.md).

## 1. What we built

A journey planner for Delhi's buses whose times come from **what buses actually did** (October 2026 GPS, 31 days) rather
than from the GTFS timetable, plus **live bus positions** (GTFS-RT) when the user leaves now.

- `GET /journeys?from=lat,lng&to=lat,lng&depart=…|arrive=…&sort=fastest|comfort|fewer_transfers`
  returns up to 6 options (direct or one transfer, walking ≤ 800 m), each with walk / wait / ride times, a
  **"safe" arrival time (85th percentile)**, where the wait came from (live bus, turning-back bus, history), and the
  timetable time for comparison. Answers in about 1–4 s.
- A map UI (`/`) and a stop-passage inspector (`/passages`) that shows, for any route and day, the raw GPS, which
  point was taken as each stop passage, every bus on the line moving at once, and a time–distance (Marey) diagram
  against the timetable.

## 2. Data and the one idea everything rests on: stop passages

| Source | Use |
|---|---|
| DTC bus GPS, Oct 2026 (124 GB unpacked, ~10–30 s per point) | stop passages → ride times, waits, ground truth |
| GTFS static v32 (2,574 directional routes) | route stop sequences, the timetable baseline |
| GTFS-RT vehicle positions (OTD API, recorded by us) | live positions, recent link speeds |

GPS trip IDs do not join GTFS trip IDs, so we built our own **stop passages**: for each vehicle trip, the time it
passed each stop of its route.

1. Anchor passages: the GPS point closest to the stop within 60 m (`tsh.passages`). This catches only 77% of
   passages, because at speed there is often no point inside 60 m.
2. Interpolation (`tsh.passages_v2`): between anchors, GPS points are projected onto the stop-to-stop polyline and the
   time at each stop is interpolated. **96% of passages detected.** The "passage timetable" used for prediction now
   agrees with the ground truth 99% of the time (was 83%).
3. Terminal fill (`tsh.passages_term`, ground truth only): trips often stop being matched 1–2 stops before the
   terminus (the depot is off the road). If the same vehicle, under the same route label, comes within 200 m of the
   terminus within 30 min, the remaining stops are filled. This adds ~35k passages/day and halves the
   cases where a bus seen upstream seemed never to reach the user's stop (50% → 27% of such cases).
4. Split runs: 9% of trips are one physical run recorded as two trip IDs; we bridge them in the ground truth.

## 3. Models

**In-vehicle time.** Two LightGBM models: one per link (stop pair) and one per whole ride (stop *i* → *j*), averaged
with a weight fixed in advance (0.5). Features: link/route, time of day, day type, the usual time for that hour, and —
when available — how much slower than usual the preceding buses on the same links were in the last 30 min (from
recorded GTFS-RT). Quantile models give the 15th/85th percentiles; 85.1% of held-out rides arrived within the 85th
percentile.

**Waiting time — the hard part.** Delhi's GTFS times are not observed departures (they assume constant speed), and
in our data the actual headways are more irregular than random arrivals (median coefficient of variation 1.09; 12% of
gaps under 2 min = bunching). So:

- *Leaving later / planning ahead*: an **observed passage timetable** — for each route × stop × weekday/weekend, the
  times buses actually passed on the training days. The wait for a departure time is read off each past day.
- *Leaving now*: (a) a bus visible upstream on the same route → its ETA (ride model from its last position);
  (b) otherwise a bus of the opposite direction that will turn back at the terminus (learned vehicle chaining: 76%
  of next trips are the reverse direction) averaged with the elapsed time since the last bus and the next observed
  departure from the origin.
- Live ETAs are point predictions and fail in a recognisable way: the user misses a visible bus by tens of seconds, or
  the bus turns back before the stop. We measured these misses **on a calibration week inside the training period**
  and turned each live wait into a distribution (40 quantiles by source and predicted wait).

## 4. Choosing and timing a journey

For each candidate (≤ 40 after a distance pre-filter), the whole journey is **replayed on every past day of the same
type**: walk to the stop, take the first bus that actually passed on that day, ride (model median), transfer the same
way. A day with no bus within 4 h counts as "did not arrive". The departure is jittered ±10 min in 2-min steps.

Picking the option with the shortest replay is optimistic (the optimizer's curse: the winner is the one whose
estimate happened to be low). We **recalibrate the replay distribution** (quantile recalibration, Kuleshov et al. 2018)
on the calibration week: the displayed time and the safe arrival are the replay quantiles at which actual journeys
landed at 50% and 85%. Options that failed on more than half of the past days are pushed to the bottom.

When leaving now, the first wait is the live distribution and everything after the transfer is replayed on past days.
**Arrive-by** walks the replay backwards and returns the latest departure that made it on 85% of past days (plus a
margin fitted on the calibration week).

## 5. Validation protocol

- Train on **1–24 Oct**, test on **25–31 Oct**, never touched while building. Every tuned value (quantile levels,
  margins, catch threshold, live-miss distribution) was chosen on **18–24 Oct**, with models rebuilt on 1–17 Oct.
- Journey test: 600 random origin–destination pairs 3–15 km apart, departures 07–21 h on test days. The top option is
  replayed on the test-week GPS ("had you followed it, when would you have arrived?"). Error = |predicted − actual|
  door-to-door time.
- Baselines: the GTFS timetable for the same option; planning ahead vs leaving now on the same pairs.

## 6. Results (held-out week 25–31 Oct)

| | This prototype | GTFS timetable |
|---|---|---|
| Ride time (stop *i* → *j*, 20,000 rides), median abs. error | **9.4%** with live data, 10.5% history only | 25.2% |
| Wait + ride (3,000 random arrivals at stops), median abs. error | **20.4%** | 36.5% |
| Live ETA of a visible bus, ±2 min / ±5 min (under 5 min ahead) | 70.6% / 84.7% | — |
| Journey, planning ahead: top option median error | **16.1%** | 24.1% |
| — within ±10 min | 43.6% | — |
| — picked the actually fastest option | 67.5% | — |
| — recommended a bus that never came | 12.0% | — |
| — arrived by the safe time (target 85%) | 76.3% | — |
| Journey, leaving now (live positions): median error | **13.6%** | 25.3% |
| — picked the actually fastest option | 73.1% | — |
| — arrived by the safe time (target 85%) | 79.1% | — |
| Arrive-by: arrived in time when leaving at our departure | **79.6%** | 29.6% (57% over 10 min late) |

Leaving now beats planning ahead on the same 353 pairs (16.0% → 12.9%; 95% bootstrap interval of the difference
−4.9 to −0.2 points). Ride and wait rows are scored on interpolated passages; journey rows on interpolated passages
with terminal fill and bridged split runs (the current ground truth, which can score 7% more top options than before).

## 7. Why the remaining error is hard — what the data and Delhi's operations say

We decomposed the door-to-door error of the leaving-now planner on 1,000 test pairs. Ride time contributes little
(~15% of squared error); **waits contribute ~85%**: the first wait when no bus is visible, and the transfer wait.

- **Buses do not run end to end.** Only 27.5% of runs go origin → terminus; 36% start mid-route, and of those 62%
  follow a run of the same line in the reverse direction (short-turning), 32% follow a different line. 86% of
  vehicles serve two or more lines in a day; line switches peak at 12–16 h (56% vs 17–34% at other hours), matching the
  midday crew-change window.
- **Scheduled trips are not all operated.** The 2024 CAG audit of DTC reports that only about 85–95% of planned trips
  ran (crew shortage, breakdowns, CNG refuelling, and a large share unexplained). On our test day 1,966 routes ran
  versus 2,574 in GTFS.
- **Consequence.** "The next bus starts at the origin" over-predicted waits by 13 min (median); "a reverse bus will
  turn back" left a quarter of users with no bus within 3 h. When no bus is visible, the actual wait is 0.74–1.82× the
  prediction (interquartile) — with headway CV ≈ 1, any single-number forecast keeps an error of about half the
  wait. We therefore communicate uncertainty as a safe arrival time instead of chasing a point estimate.

Things we tried and did not adopt (all measured on the same held-out pairs): GTFS timetable × probability of running,
rain adjustment (buses were faster in rain), calendar cleaning, replacing invisible-bus waits with the passage
timetable (leg error 18.2 → 10.9 min but door-to-door unchanged and optimistic), and live ETAs for the transfer bus
(median error 8.5 → 5.5 min where used, but the mean got worse and the safe arrival fell from 90% to 82% on 5,000
pairs — it failed our pre-registered adoption criteria).

## 8. Limitations

- One month of data and a single calibration week, so the 85% target lands at 76–80% on the test week.
- At most one transfer; walking is straight-line × 1.3.
- About 20% of top options cannot be scored because the bus is lost by GPS before the alighting stop.
- The recent-link-speed feature and the inspector UI still use the 60 m passages.

## 9. Credits

Open-source libraries: DuckDB, pandas, NumPy, Polars, PyArrow, LightGBM, SciPy, RapidFuzz, FastAPI, Uvicorn,
Matplotlib, gtfs-realtime-bindings, py7zr, Leaflet, OpenStreetMap tiles. Data: Delhi Transport Stack (DTC bus GPS,
GTFS static, GTFS-RT via Open Transit Data). AI tools: code, analyses and documents were written with
**Claude Code (Anthropic)** as an AI pair-programmer and research assistant; every number above was produced by
running the code in this repository on the hackathon data.
