# Detecting when buses pass, arrive at and leave stops in noisy bus GPS (AVL) data: methods, parameters, accuracy, Indian evidence

Research date: 2026-11-16.

**Context.** Delhi Transport Stack Hackathon. The team works with DTC bus GPS for October 2026: 561M points, median sampling interval 11 s (p90 22 s). Its current rule takes the nearest GPS point within 60 m of each stop, using one representative stop pattern per route. It then drops passages that break stop order and keeps trips with ≥5 detected stops.

**How the sources were read.** About 40 tool calls in total. These were read in full, or in the relevant section:
- TransitClock source: `ArrivalDepartureGeneratorDefaultImpl.java` and `CoreConfig.java`
- Newson & Krumm (2009)
- Pahwa et al. (2017, Delhi)
- Altaf & Biyani (2023, Delhi)
- Harsha et al. (2023, Mysuru)
- Wessel et al. (2016, Toronto)
- gps2gtfs (2024, Kandy)
- Sun et al. (2025, Gainesville)
- OSRM and Valhalla API docs

Two markers flag weaker sourcing:
- **(search snippet)**: the page was not opened, or returned 403. Treat these items as lower confidence.
- **(via sibling notes)**: another researcher extracted the item, in `research_notes/バス所要時間推定と経路検索の事例/india_delhi_gps_eta.md`.

## Q1. Buffer (geofence) approaches: choosing the radius, typical radii, nearest point vs interpolated crossing time

### Takeaway
- **Typical radii.** Published stop radii cluster at **20–60 m**. A radius of 100 m appears only as an outer cut-off or fallback.
- **The trade-off.** A larger radius detects more buses but times them less precisely. It also biases the sample by speed.
- **Delhi evidence.** The only quantitative radius study found uses Delhi data (DIMTS, 10 s). Widening the buffer from 15 m to 60 m raised detections from **427 to 730**. Mean spot speed rose from **11.3 to 16.5 km/h**.
- **Nearest point vs interpolation.** No study was found that measures how much timing error the "nearest point" rule causes compared with an interpolated crossing.
- **What transit software does.** Transit-specific software (TransitClock, retro-gtfs/Wessel) does *not* use the nearest point. It interpolates or extrapolates the stop time along the matched path.

### Cited Findings
**Radii used in practice**
- **DIMTS / IIT Delhi.** DIMTS "uses 25 meters buffer size for their analysis". IIT Delhi adopted 25 m to stay consistent with DIMTS — [Pahwa, Lakhotia, Tiwari 2017, EASTS vol.12](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)
- **Buffer-size test on DIMTS 10 s GPS** (one route per category; spot speed in km/h) — [Pahwa et al. 2017](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)

  | Radius | Unique bus detections | Mean speed | SD | 85th percentile |
  |---|---|---|---|---|
  | 15 m | 427 | 11.27 | 8.77 | 20.78 |
  | 25 m | 560 | 12.05 | 8.93 | 21.75 |
  | 30 m | 599 | 12.71 | 8.92 | 22.40 |
  | 45 m | 691 | 15.15 | 9.17 | 25.17 |
  | 60 m | 730 | 16.53 | 9.04 | 26.33 |

  The authors say a small buffer is biased "towards buses with slower movement rendering large TT and slower speeds". A large buffer catches buses "farther away from the bus stop".
- **Pahwa et al. 2017, how they counted passages** — [same source](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)
  - A trip can fall in the same buffer several times; they use only one instance per trip per buffer. The paper does not say which point is kept.
  - If a trip appears in a link's start buffer but not its end buffer, or the reverse, it is dropped for that link.
  - The DIMTS sample data column is "Time Received", and the text describes "the time stamp of when the GPS data was transmitted every 10 seconds".
- **IIIT-Delhi, Altaf & Biyani 2023** (Delhi OTD feed, polled every 10 s; 190 GB; six months) — [arXiv 2306.15941](https://arxiv.org/pdf/2306.15941)
  - Arrival is "the time at which the distance of the bus from the stop is minimal for a particular trip".
  - Trips whose minimum distance is over 100 m are ignored ("we assume that no data was fetched").
  - "approximately 40% of the total buses passing through a stop send the data within an average minimum distance of 30m ± 20m". Only those trips were used.
- **IIIT-Delhi benchmark dataset.** Raw points within 50 m of a stop are snapped to it. 50 m was chosen because fast buses may not ping near the stop (via sibling notes) — [Jain et al. 2019](https://ar5iv.arxiv.org/html/1910.08903)
- **TransitClock defaults** — [TransitClock CoreConfig.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/configData/CoreConfig.java)
  - `beforeStopDistance` = 50 m: "How far a vehicle can be ahead of a stop in meters and be considered to have arrived".
  - `afterStopDistance` = 50 m.
  - `maxDistanceFromSegment` = 60 m: "How far a location can be from a path segment and still be considered a match".
- **Gainesville, USA** (GTFS-RT about every 15–20 s). Stops are projected onto the route shape and given a 20 m buffer. Arrival is when the bus first enters it; departure is when it first exits — [Sun, Spall, Wong, Zhao 2025, arXiv 2503.05907](https://arxiv.org/html/2503.05907)
- **Toronto TTC** (NextBus, vehicles report about every 20 s). Stops within 20 m of the map-matched route are matched to a point on it. The stop time "is interpolated linearly from the times associated with the vehicle position reports" — [Wessel, Allen, Farber, GIScience 2016 short paper](https://escholarship.org/content/qt5vm764rp/qt5vm764rp.pdf); journal version [J. Transport Geography 62 (2017) 92–97](https://econpapers.repec.org/RePEc:eee:jotrge:v:62:y:2017:i:c:p:92-97)
- **gps2gtfs** (Python package, University of Moratuwa; tested in Kandy, Sri Lanka). It uses a 50 m stop buffer. If no point falls inside, it enlarges the buffer to 100 m and takes the closest point. It reports no accuracy results — [Ratneswaran, Thayasivam, Thillaiambalam 2024, arXiv 2412.15221](https://arxiv.org/html/2412.15221v1)
- **Caltrans study** (search snippet). The buffer extends 30 m (about 100 ft) either side of the geocoded stop. Departure is inferred from pings just outside the zone, and physically impossible negative dwell times are corrected — [Caltrans CA24-3514](https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/final-reports/ca24-3514-v2-a11y.pdf)
- **Open GPS-to-GTFS dataset paper** (search snippet; the page returned 403). It uses a 25 m radius "to account for potential GPS inaccuracies". It argues the radius should vary with stop density, road geometry and signal accuracy. It says sampling intervals above about 10–15 s may require interpolation — [MDPI Data 10(8):119, 2025](https://www.mdpi.com/2306-5729/10/8/119)

**How large GPS error is (an input to choosing the radius)**
- Newson & Krumm estimated GPS noise at σz = **4.07 m** on their test drive (1.4826 × median absolute deviation) — [Newson & Krumm 2009](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf)
- Pahwa et al.: devices offer about **4 m** horizontal accuracy. The Delhi data still had missing points (poor signal, tall buildings) and "erratic" off-route movement (drivers taking shortcuts or detours), which was excluded — [Pahwa et al. 2017](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)

**Nearest point vs interpolation**
- TransitClock never takes the nearest AVL report as the stop time — [ArrivalDepartureGeneratorDefaultImpl.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/core/ArrivalDepartureGeneratorDefaultImpl.java)
  - Its stated aim is to "extrapolate in order to determine when a vehicle really arrives/departs a stop".
  - It computes two candidate times from expected travel times. It keeps the later one for a departure and the earlier one for an arrival.
  - For stops skipped between two reports, it scales expected travel and dwell times by speedRatio = elapsed AVL time / expected travel time.
- One study compared a neural network with linear interpolation for *real-time* arrival estimation at different location-data intervals. It reports an RMSE improvement of "up to 6.18 s". The error-vs-interval curves were not retrieved (abstract, search snippet) — [ResearchGate 298731943](https://www.researchgate.net/publication/298731943_The_effect_of_time_interval_of_bus_location_data_on_real-time_bus_arrival_estimations)

### Inferences
- **Timing error of the current nearest-point rule.**
  - Assume the bus passes at roughly constant speed *v*, sampling interval Δt, with at least one point inside the radius.
  - The nearest point is then up to vΔt/2 from the stop along the road, so the time error is roughly uniform within ±Δt/2.
  - Per stop: SD = Δt/√12, which is **3.2 s at 11 s** and **6.4 s at 22 s**.
  - Per link (the difference of two independent stop errors): SD = Δt/√6, which is **4.5 s** at 11 s and **9.0 s** at 22 s.
  - Against Delhi's mean link time of 3 min 43 s (Pahwa, route 611WB), this is about 2–4%. On short links of 40–60 s it is roughly 8–22%. It widens percentiles and variability more than it shifts the mean.
- **Turning the team's distances into time.**
  - The median distance of 17.5 m is about 3.5 s at 5 m/s (18 km/h), or about 9 s at 2 m/s.
  - The p90 of 43.7 m is about 9–22 s at the same speeds.
  - GPS noise is about 4 m, and the stop pole to bus lane is about 5–10 m. So most of the 17.5 m / 43.7 m is offset along the road caused by sampling. Interpolation removes this part.
- **Speed threshold for missed detections.**
  - A point is guaranteed to fall within ±r along the road only if vΔt ≤ 2r.
  - With r = 60 m: guaranteed only for buses at or below 10.9 m/s (39 km/h) at Δt = 11 s, and only at or below 5.5 m/s (20 km/h) at Δt = 22 s (the team's p90).
  - Pahwa's mean link speed on 611WB was 22 km/h. So on stretches with long gaps between points, the passages that go missing are the free-flowing ones. The surviving link-time sample is biased towards slow trips that stopped.
  - This is the same bias Pahwa saw by changing the radius, caused here by the sampling interval instead.
- **Recommendation.**
  - Use the radius only as a **gate**: lateral distance from the route shape ≤ about 60 m (the same as TransitClock's `maxDistanceFromSegment`), plus a ±20–50 m along-route zone around each stop.
  - Take the **time** from the interpolated along-route crossing.
  - Then any trip with points on both sides of a stop gets a passage whatever its speed, which removes the bias above.
  - Mark crossings interpolated across long gaps (>120–180 s) as imputed.
- **Check what `timestamp` is.** It must be the GPS fix time, not the time the server received the point. The DIMTS column is literally "Time Received". The team's feed latency (median 22 s, p90 166 s) would directly corrupt passage times if the receipt time were used. It would also make buffered points arrive bunched under the same timestamp.

### Gaps
- No peer-reviewed study was found that measures the timing error or detection rate of nearest point vs interpolated crossing as a function of sampling interval.
- No formula was found that links the best radius to sampling interval and GPS error.
- The MDPI dataset paper and the Caltrans report were not opened; their details are unverified.

## Q2. Linear referencing: projecting points onto the route shape, interpolating crossing times, and handling edge cases (opposite carriageway, loops, repeated passes, terminals, layovers, backward jumps)

### Takeaway
- **The standard pattern.** Each point is matched to the known trip path (route shape or map-matched road path) and turned into distance along the route. Stop times are then interpolated along that distance.
- **How edge cases are handled.** By rules, not by statistical models:
  - match only forward along the route;
  - never let times go backwards;
  - split trips at gaps;
  - apply special logic at terminals and layovers.
- **Ready-made parameters.** TransitClock's defaults are a sensible starting set.
- **Accuracy.** No source reports the accuracy of the projection-plus-interpolation step itself against ground truth.

### Cited Findings
- **Toronto (Wessel et al.)** — [Wessel et al. 2016](https://escholarship.org/content/qt5vm764rp/qt5vm764rp.pdf)
  - A trip is one vehicle's trace. It ends when the vehicle changes its reported route or heading, or sends no update for more than 60 s.
  - Points were map-matched to OpenStreetMap with OSRM. About **2%** of trips could not be matched plausibly and were discarded, "much of this due to clear GPS error".
  - Stops within 20 m of the route were matched, and stop times were interpolated linearly.
- **Gainesville (Sun et al.)** — [arXiv 2503.05907](https://arxiv.org/html/2503.05907)
  - Stops and intersections are projected onto the route shape, each with a 20 m zone.
  - Link travel time runs from departure at stop *i*−1 to departure at stop *i*.
  - Dwell is departure minus arrival.
  - Road travel time is arrival at *i* minus departure from *i*−1, minus time spent at intersections.
- **Delhi route 399 (Bhutani et al. 2022).** Raw GPS was "filtered off the GPS noise" by "simple route projection" before computing 800 m section times (via sibling notes) — [arXiv 2210.01655](https://arxiv.org/pdf/2210.01655v1.pdf)
- **TransitClock matching defaults** — [CoreConfig.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/configData/CoreConfig.java)

  | Parameter | Default | Meaning |
  |---|---|---|
  | `maxDistanceFromSegment` | 60 m | Max distance from the path to count as a match |
  | `maxHeadingOffsetFromSegment` | 360° | Heading is effectively not used |
  | `distanceBetweenAvlsForInitialMatchingWithoutHeading` | 100 m | For initial matching when heading is missing |
  | `distanceFromEndOfBlockForInitialMatching` | 250 m | No initial match this close to the end of the vehicle's day of work (its "block") |
  | `distanceFromLastStopForEndMatching` | 250 m | Proximity to the last stop for end matching |
  | `layoverDistance` | 2000 m | "How far vehicle can be away from layover stop and still match to it" |
  | `distanceFromLayoverForEarlyDeparture` | 180 m | Distance past a layover stop to count as an early departure |
  | `allowableNumberOfBadMatches` | 2 | Bad matches allowed in a row |
  | `timeForDeterminingNoProgress` / `minDistanceForNoProgress` | 8 min / 60 m | Detects a vehicle that is not moving |

- **TransitClock arrival/departure safeguards** — [ArrivalDepartureGeneratorDefaultImpl.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/core/ArrivalDepartureGeneratorDefaultImpl.java)
  - `maxStopsBetweenMatches` = 12: no events are generated if more stops were passed between two matches.
  - `maxStopsWhenNoPreviousMatch` = 1.
  - `tooManyStopsTraversed` rejects cases with ≥4 stops passed at more than one stop per 15 s: "If traversing more than a stop every 15 seconds then there must be a problem".
  - Departures are forced to come after the last arrival: "don't want arrival/departure times to ever go backwards".
  - Arrivals must fall after the previous AVL time, and departures before the new AVL time.
  - An arrival extrapolated past the current AVL time is held until the next report.
- **Delhi, separating the two directions (Pahwa et al.)** — [Pahwa et al. 2017](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)
  - The AVL file mixed UP and DOWN directions.
  - Their first attempt put a 30 m buffer on the left of each direction's line, since India drives on the left. It failed where both directions share a road with no kerb separation, because buses "may enter the other lane".
  - The final rule starts a trip in a direction when the bus comes within 25 m (Haversine) of that direction's first stop.
- **Terminals (gps2gtfs)** — [arXiv 2412.15221](https://arxiv.org/html/2412.15221v1)
  - Drivers keep engines running at terminals, so engine state cannot split trips.
  - A trip starts at the *last* point inside the origin terminal buffer (100 m in the example code). It ends at the first zero-speed point.
- **Gaps.**
  - Newson & Krumm split the data into separate trips when a break exceeds 180 s — [Newson & Krumm 2009](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf)
  - OSRM match uses `gaps=split` by default, and timestamp jumps over 60 s can split the trace — [OSRM HTTP API docs](https://raw.githubusercontent.com/Project-OSRM/osrm-backend/master/docs/http.md)

### Inferences
Sketch of an implementation in Python/DuckDB:

1. **Route lines and stop positions.**
   - Build one polyline per route **and direction** (GTFS `shapes.txt` with `shape_dist_traveled`, or DTC/DIMTS route geometry, which carries "Distance From Origin" segments; see Pahwa's appendix).
   - Use UTM zone 43N (EPSG:32643) for Delhi.
   - Snap stops to the polyline with the same forward-only procedure, so stop distance increases with stop sequence.
   - Flag stops more than ~30 m from the line. They may be on the wrong side of the road, or belong to a different stop pattern.
2. **Windowed projection.**
   - Break the polyline into straight segments (x1, y1, x2, y2, cumulative distance). The projection parameter and lateral distance are plain SQL arithmetic.
   - Only consider candidate segments within a forward window [s_prev − 50 m, s_prev + v_max·Δt + 50 m], with v_max of 20–25 m/s.
   - This one rule handles loops, figure-8 routes, stops served twice, and stops on the opposite carriageway. The other pass, or the other side of the road, falls outside the window or belongs to another direction's line.
   - For routes with many loops, the robust version is a 1-D Viterbi along the polyline (Newson & Krumm's HMM applied to the route line rather than the road network).
3. **Gate off-route points.** Treat a point more than 60 m from the line (TransitClock's limit) as off-route, e.g. a detour. A run of off-route points stops interpolation, so no passages are invented through a detour.
4. **Backward jitter.**
   - Use the running maximum of distance along the route within the trip.
   - A *persistent* backward jump of more than about 100–200 m is not noise: it means the trip was split or assigned wrongly.
5. **Crossing times.**
   - For each stop distance s_j, find the bracketing points s_k ≤ s_j < s_{k+1} with a DuckDB `ASOF JOIN` or `LAG`/`LEAD`, and interpolate the time linearly.
   - Compute three times per stop:
     - arrival at s_j − r_before;
     - departure at s_j + r_after (r = 20–50 m; Sun et al. use 20 m, TransitClock 50 m);
     - passage at s_j.
6. **Terminals.**
   - First stop: departure is the **last exit** from the origin zone, never the nearest point. With layover points in the trip, the nearest point can fall anywhere in a layover lasting minutes.
   - Last stop: arrival is the **first entry**.
7. **Gaps and sanity checks.**
   - Interpolate only across gaps of ≤120–180 s and ≤ about 12 stops (Newson & Krumm 180 s; TransitClock 12 stops), and flag these as imputed. Beyond that, leave the passage missing.
   - Reject segments that imply more than one stop every 15 s over ≥4 stops.
- **Python alternative.** Shapely 2's vectorised `line_locate_point` is fast. But it projects onto the *closest* part of the line anywhere, so it is unsafe for loops unless you clip the line to a window first.
- **What the team's existing filters already cover.** "Drop passages that break stop order" is a weak form of the forward-only rule. "Keep trips with ≥5 stops" partly replaces gap logic. Neither fixes timing within a stop or the speed-selection bias.

### Gaps
- No accuracy figures were found for projection plus interpolation against ground truth.
- I did not read TransitClock's spatial-matching code, so I could not see how it handles loop or self-overlapping shapes. The window rule above is my own design.
- How DTC trip IDs are assigned at termini, and whether one representative pattern fits each route's variants, could not be checked from published sources.

## Q3. HMM map matching (Newson & Krumm, OSRM, Valhalla Meili, GraphHopper, FMM) and transit systems (TransitClock, OneBusAway, Swiftly, GTFS-RT): how they infer stop events, and how accurate they are

### Takeaway
- **Road-network matchers.** HMM matchers (Newson & Krumm; OSRM `match`; Valhalla Meili) recover the road path reliably even with sparse points: **0.11% route error at 30 s sampling** in Newson & Krumm.
- **They don't produce stop events.** Their output is matched positions, so a separate step is still needed to time stops.
- **With a known route shape**, matching to the shape is enough. This is what TransitClock does.
- **Verified transit logic.** Of the transit systems, only TransitClock's arrival/departure logic was verified here. No public documentation was found for Swiftly; OneBusAway and GTFS-RT feed generators were not checked.

### Cited Findings
- **Newson & Krumm 2009** — [Newson & Krumm 2009](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf)
  - Model:
    - Measurement error is Gaussian with σz = 4.07 m.
    - Roads more than 200 m from a point get zero probability.
    - The move from one point to the next is scored by an exponential penalty on |great-circle distance − route distance|, with β estimated robustly.
  - Robustness tests:
    - They simulated sampling periods of 2–600 s, plus added Gaussian noise.
    - "the error is only 0.11% even when the sampling period grows to 30 seconds".
    - At longer sampling periods the method tolerates noise "as high as 50 meters standard deviation". It is *more* sensitive to noise at 1 s sampling.
    - Breaks over 180 s are split into separate trips.
  - Their ground truth is a hand-corrected match. Only the path is known; the exact position at each point "is unknowable".
- **OSRM `match`** — [OSRM HTTP API docs](https://raw.githubusercontent.com/Project-OSRM/osrm-backend/master/docs/http.md)
  - Inputs:
    - `radiuses` defaults to 5 m: "The radius for each point should be the standard error of the location measured in meters from the true location".
    - Other options: `timestamps`, `gaps` (split by default, or ignore), `tidy`.
  - Outputs:
    - Unmatched outliers come back as null.
    - Each tracepoint carries `matchings_index`, `waypoint_index`, `alternatives_count` (0 means unambiguous) and its distance from the input point.
    - Each matching has a `confidence` between 0 and 1.
- **Valhalla map matching** — [Valhalla map-matching API](https://valhalla.github.io/valhalla/api/map-matching/)
  - `shape_match` defaults to `walk_or_snap`.
  - `trace_options`: `search_radius` (max 100 m), `gps_accuracy`, `breakage_distance`, `interpolation_distance`, `turn_penalty_factor`. The page gives no defaults for these.
  - `matched_points` returns, per input point: `type` (matched / interpolated / unmatched), `edge_index`, `distance_along_edge` and `distance_from_trace_point`.
  - `use_timestamps` defaults to false.
- **TransitClock.** It matches points to the trip pattern within 60 m. It then writes separate Arrival and Departure records per stop, using the interpolation, extrapolation and safeguards listed in Q2 — [ArrivalDepartureGeneratorDefaultImpl.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/core/ArrivalDepartureGeneratorDefaultImpl.java); [CoreConfig.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/configData/CoreConfig.java)
- **retro-gtfs / Wessel.** OSRM map matching followed by linear interpolation of stop times; about 2% of trips could not be matched — [Wessel et al. 2016](https://escholarship.org/content/qt5vm764rp/qt5vm764rp.pdf). The open-source tool is [SAUSy-Lab/retro-gtfs](https://github.com/SAUSy-Lab/retro-gtfs). Its README says its output "is not directly useful for routing actual people on a network".
- **Swiftly.** Searches found no public documentation of how Swiftly sets arrival and departure times (search returned only unrelated sources).

### Inferences
- **For stop timing, skip road-network HMM.** Use linear referencing on the route shape (Q2).
- **Where OSRM or Valhalla do help:**
  - building or repairing route shapes where DTC geometry is missing or wrong;
  - detecting detours, i.e. points far from the shape that fit another road well.
- **If you use OSRM `match`:**
  - set `radiuses` per point at 10–20 m rather than the 5 m default, which assumes open sky (Delhi has urban canyons);
  - pass `timestamps`;
  - keep `gaps=split`.
  - Use Valhalla's `distance_along_edge` and `type=interpolated` points if you need positions on the road network.
- **The team's sampling is not the problem.** Newson & Krumm's 0.11% at 30 s suggests 11 s (p90 22 s) is comfortably within the range where the path is reliable. The remaining error is in *timing*, not path.

### Gaps
- Not verified in this session:
  - GraphHopper map matching, Fast Map Matching (FMM) and pfaedle (parameters, defaults);
  - how OneBusAway and Swiftly infer stop events;
  - GTFS-RT TripUpdates generators, including whether and how TransitClock produces them.
- No published stop-time accuracy was found for TransitClock, nor for any HMM map-matching tool, against ground truth.

## Q4. Arrival vs departure vs passage: detecting dwell from low speed or clusters of points, and what matters for travel-time modelling

### Takeaway
- **"Passage" is ambiguous when the bus dwells.** Robust pipelines record **arrival** (entering the zone) and **departure** (leaving it) separately, and define link times consistently, e.g. departure to departure in Sun et al.
- **Dwell is detected from low speed:**
  - below 5 km/h (Mysuru);
  - speed = 0 in the reported speed field (gps2gtfs);
  - a threshold derived from a simple simulation of a bus stopping.
- **Indian buses often do not stop fully**, and the speed fields in Delhi feeds have been unreliable. So speed should be derived from positions.

### Cited Findings
- **Sun et al.** Link time is departure to departure; dwell is departure minus arrival; road time is arrival at *i* minus departure from *i*−1, minus intersection time. The 20 m zone uses first entry and first exit — [arXiv 2503.05907](https://arxiv.org/html/2503.05907)
- **gps2gtfs** — [arXiv 2412.15221](https://arxiv.org/html/2412.15221v1)
  - Arrival is the first speed = 0 record inside the 50 m buffer; departure is the next record with speed > 0.
  - If there is no zero-speed record, the closest point is used for both and dwell is set to 0 (a skipped stop or missing data).
  - The paper notes that sparser sampling reduces dwell accuracy.
- **Mysuru (Harsha, Mulangi, Panditharadhya 2023)** — [European Transport 94 (2023), paper 2](https://www.istiee.unict.it/sites/default/files/files/ET_2023_94_2.pdf)
  - Data: Mysore City Transport Division, about 500 GPS-equipped buses, ITS since 2012, 10 s interval. Route CBS–Yelwala (18.46 km), May–June 2018.
  - Total stop delay = deceleration delay + stopped delay + acceleration delay. Each part comes from four critical points t1–t4 in the speed and acceleration profiles.
  - A bus counts as "stopped" when speed is below 5 km/h (after Mousa 2002).
  - Trips with no slowdown near the stop (speed never below 5 m/s) are excluded.
  - Drivers often do not stop fully when no passengers are waiting.
  - The GEV distribution fit the delays best.
- **Pahwa et al.** Links were defined stop to stop "to account for the bias of the dwell times at bus stops" — [Pahwa et al. 2017](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)
- **TransitClock** — [ArrivalDepartureGeneratorDefaultImpl.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/core/ArrivalDepartureGeneratorDefaultImpl.java)
  - Arrival and departure are separate events.
  - Stop (dwell) time between reports comes from the expected stop time in the vehicle's schedule (its "block").
  - Code comments note the schedule may not leave enough time "for wait time stops".
- **Bus dwelling patterns** (search snippet). One paper sets the "stopped" speed threshold with a simple simulation of a bus stopping, because recorded speed may never reach zero — [ResearchGate 319053695](https://www.researchgate.net/publication/319053695_Evaluation_of_bus_dwelling_patterns_using_bus_GPS_data)
- **Glick & Figliozzi, PSU 2017** (search snippet). Using only stop-level records without GPS trajectories can bias estimates of what drives dwell time — [Measuring the Determinants of Bus Dwell Time](http://web.cecs.pdx.edu/~maf/Journals/2017_Measuring_the_Determinants_of_Bus_Dwell_Time.pdf)
- **Delhi speed field.**
  - EMBARQ's Route 419 GPS (2012) recorded speed as 10 km/h instead of 0, because of a system limitation (via sibling notes) — [EMBARQ SlideShare](https://www.slideshare.net/EMBARQNetwork/embarq-india-talking-transit-august-2012-star-bus)
  - A hobby archive of the Delhi Open Transit Data (OTD) GTFS-RT feed reports speed always 0 and about 44% empty responses (search snippet) — [where-is-my-bus](https://github.com/Nagaraj0000b/where-is-my-bus)
- **Bengaluru (BMTC).** The ITS reports positions every 10 s and logs where a bus stopped, when, and for how long. This is journalism, not a study (search snippet) — [FactorDaily](https://archive.factordaily.com/longform/big-data-real-time-gps-tonic-not-steroids-bengalurus-bus-service/)

### Inferences
- **Which times a journey planner needs.**
  - In-vehicle time from A to B = **arrival(B) − departure(A)**.
  - Running time for a link = arrival(*i*) − departure(*i*−1).
  - Dwell = departure(*i*) − arrival(*i*).
  - Store arrival and departure for every stop; all of these can then be derived.
- **What nearest-point passages do to dwell.** Each link time absorbs a random share of the dwell at both of its stops. The sum telescopes, so whole-route totals stay right. But per-link distributions get noisier, and an A→B time carries about ±½ a dwell at each end.
- **First-stop layover.** When layover points belong to the trip, "nearest to stop" can pick a moment minutes before the real departure. Check the distribution of first-link times for a long right tail; this is a likely source of outliers in the current method.
- **Detecting dwell in Delhi.**
  - Derive speed as along-route distance / Δt; don't trust the reported speed field.
  - Flag a stop event when the derived speed is below about 5 km/h (Mysuru threshold) for at least one interval inside the stop zone.
  - At 11 s sampling, dwells shorter than about 10 s cannot be seen. Treat dwell as known only to lie between 0 and Δt (interval-censored); don't record it as zero.

### Gaps
- No Indian study was found that checks dwell detection against manual observation.
- The IIT Madras paper "Mining bus stops from raw GPS data of bus trajectories" (Chennai) reports about **99%** accuracy for identifying stops (search snippet; the page returned 403). Its dwell-time accuracy was not seen — [IITM WSAI](https://wsai.iitm.ac.in/publications/mining-bus-stops-from-raw-gps-data/)

## Q5. Indian studies of bus GPS stop detection and travel times (Delhi, Bengaluru, Chennai, Mysuru, Hyderabad, Pune)

### Takeaway
- **Methods.** Indian studies use simple rules on about 10 s GPS:
  - a 25 m buffer (DIMTS / IIT Delhi);
  - 50 m snapping (IIIT-D benchmark);
  - minimum distance with a 100 m cut-off (IIIT-D);
  - route projection (TCS Research, Delhi);
  - trajectory-based delay with a 5 km/h stop threshold (Mysuru).
- **Data problems documented:**
  - missing points;
  - detours off the route;
  - the two directions mixed together;
  - timetables not followed;
  - unreliable speed fields;
  - gaps in the feed.
- **Accuracy.** No Indian study found reports a validated timing error for stop-passage detection.

### Cited Findings
**Delhi**
- **IIT Delhi (Pahwa, Lakhotia, Tiwari 2017)** — [EASTS 12](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en)
  - Data: DIMTS GPS for September 2016, 25 routes, every 10 s. Fields: vehicle registration, date, "Time Received", latitude, longitude, instantaneous speed.
  - DIMTS also supplied route geometry segments with distance from origin, and stop sequences with distance.
  - Method: separate directions, then 25 m stop buffers, then link travel time and space-mean speed.
  - Results for route 611WB: mean link time **3 min 43 s** (SD 2 min 44 s); space-mean speed **22.0 km/h** (SD 5.6). Mean link length is 547.7 m (SD 398.5 m).
- **IIIT-Delhi (Altaf & Biyani 2023).**
  - The network has 6,747 stops and over 7,000 buses on 2,000 routes.
  - The paper blames missing pings on "network failure or other issues".
  - Arrival is the time of minimum distance to the stop, and the 100 m cut-off applies. Only about 40% of passing buses report within 30 ± 20 m of the stop — [arXiv 2306.15941](https://arxiv.org/pdf/2306.15941)
- **IIIT-Delhi benchmark (Jain et al. 2019)** (via sibling notes) — [ar5iv 1910.08903](https://ar5iv.arxiv.org/html/1910.08903)
  - Covers 543 routes and 3,464 stops, at 10 s.
  - Points are snapped to stops within 50 m, and only every third stop was used to reduce noise.
  - It found "significant randomness in the starting time": the timetable was not followed.
- **TCS Research (Bhutani et al. 2022), Delhi route 399.** Route projection, then 800 m sections (via sibling notes) — [arXiv 2210.01655](https://arxiv.org/pdf/2210.01655v1.pdf)
- **Delhi feed quality, from hobby projects** (search snippets).
  - One OTD GTFS-RT archive reports about 44% empty responses and speed always 0 — [where-is-my-bus](https://github.com/Nagaraj0000b/where-is-my-bus)
  - One tracker discards pings older than 180 s — [DTC-Tracker](https://github.com/saranshgemini18-del/DTC-Tracker)
  - One project matched pings to stops for 6,000+ buses over six hours — [how-Delhi-buses-move](https://github.com/rishabhjain9196/how-Delhi-buses-move)

**Mysuru**
- Harsha M. M. and Panditharadhya B. J. (Siddaganga Institute of Technology) with Raviraj H. Mulangi (NIT Karnataka), 2023. The Mysuru ITS logs every 10 s; delay components are derived from bus trajectories (Q4). There is no stop-level passenger data, because the agency records tickets by "stage", where one stage groups several stops — [European Transport 94 (2023)](https://www.istiee.unict.it/sites/default/files/files/ET_2023_94_2.pdf)

**Chennai and Bengaluru**
- Chennai (IIT Madras): stops mined from raw GPS with about 99% accuracy (search snippet) — [IITM WSAI](https://wsai.iitm.ac.in/publications/mining-bus-stops-from-raw-gps-data/). Search results also describe 5 s GPS on Chennai route 19B (search snippet; source not verified).
- Bengaluru: BMTC ITS logs positions every 10 s, plus stop and dwell records (journalism, search snippet) — [FactorDaily](https://archive.factordaily.com/longform/big-data-real-time-gps-tonic-not-steroids-bengalurus-bus-service/)

**Elsewhere in South Asia**
- gps2gtfs (Kandy, Sri Lanka): 50/100 m buffers, speed-zero rules for dwell, trips started from the last point in the terminal buffer. No accuracy reported — [arXiv 2412.15221](https://arxiv.org/html/2412.15221v1)

### Inferences
- **The team's rule matches local practice.** 60 m nearest point is in line with, and slightly more generous than, Indian practice (25–100 m, minimum distance).
- **What hasn't been published in India.** Interpolated crossings, separate arrival and departure times, windowed projection, and thinning-based validation have not been reported in the Indian literature found. These are clear places to improve, and to stand out in a hackathon write-up.
- **Interpolation matters more than radius tuning.** IIIT-D found only about 40% of passing buses with a ping near the stop in OTD data. Both that and DIMTS's "Time Received" column point the same way. Check the timestamps first (Q1), then switch to interpolation.

### Gaps
- Nothing was found on Chartr's stop-detection methods, or on Hyderabad or Pune bus GPS stop detection.
- No peer-reviewed BMTC stop-detection study was found.
- The IIT Madras full text was not accessible (403).
- Pahwa et al. do not say which point is kept as the "one instance" inside a buffer.

## Q6. Validating stop-passage detection without ground truth, and visualising it (time–space "Marey" diagrams)

### Takeaway
- **No standard benchmark exists.** The practical toolkit combines:
  - synthetic degradation (thinning points and adding noise), as Newson & Krumm did for map matching;
  - internal consistency rules, such as TransitClock's checks;
  - independent proxies (schedule, ticket-machine timestamps);
  - a small field sample;
  - time–space (Marey) diagrams for visual checks.

### Cited Findings
- **Newson & Krumm's degradation tests.** They checked robustness by subsampling 1 s data to periods of 2–600 s and adding Gaussian noise. Their ground truth was hand-corrected, and only the *path* is truly known, not the exact position at each point — [Newson & Krumm 2009](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf)
- **TransitClock's sanity checks**, usable as consistency tests — [ArrivalDepartureGeneratorDefaultImpl.java](https://raw.githubusercontent.com/TheTransitClock/transitime/HEAD/transitclock/src/main/java/org/transitclock/core/ArrivalDepartureGeneratorDefaultImpl.java)
  - no more than one stop per 15 s;
  - at most 12 stops between two reports;
  - times never go backwards.
- **Wessel et al.** checked discarded trips visually and found many "ambiguous or erroneous", "much of this due to clear GPS error" — [Wessel et al. 2016](https://escholarship.org/content/qt5vm764rp/qt5vm764rp.pdf)
- **Caltrans** treats negative dwell as physically impossible and corrects it, i.e. an internal consistency check (search snippet) — [Caltrans CA24-3514](https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/final-reports/ca24-3514-v2-a11y.pdf)
- **Marey and time–space diagrams** (all search snippets):
  - A US patent describes a dynamic Marey-style diagram: distance from trip origin on the y-axis, time of day on the x-axis, actual trips as solid lines, scheduled as dashed, stops as circles — [US 10572847](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10572847)
  - A TRB paper adds schedule adherence and passenger load (from passenger counters) to Marey graphs — [TRID 1217341](https://trid.trb.org/view/1217341)
  - PSU / TriMet plot cumulative distance against time for Route 9, where the slope is the bus's average speed. TriMet's "second generation" data has 5 s granularity — [PSU TREC report](https://ppms.trec.pdx.edu/media/project_files/Exploring_Applications_of_Second-Generation_Archived_Transit_Data.pdf)
  - gtfs-to-chart draws Marey charts from GTFS schedules: slope shows speed, vertical segments show dwell, and circular routes display poorly — [gtfs-to-chart](https://awesome.ecosyste.ms/projects/github.com%2FBlinkTagInc%2Fgtfs-to-chart)
  - MetroViz is a visual analytics tool for ridership and schedule adherence — [arXiv 1507.05215](https://arxiv.org/pdf/1507.05215)
  - Anwar, Zeng and Arisona (2014) compute headways and bus separation in a time–space cube — [FHNW](https://irf.fhnw.ch/entities/publication/875355a1-b350-44e2-a497-2893a09c0694/full?back=true)

### Inferences
Validation plan suited to the team's data:

1. **Thinning experiment** (Newson & Krumm–style degradation, applied to timing).
   - Take trips sampled at ≤10 s. Treat the interpolated passage times from the full data as the reference.
   - Drop every 2nd, 3rd and 4th point (≈22 / 33 / 44 s) and recompute with (a) nearest point within 60 m and (b) interpolation.
   - Report per method and per interval: detection rate, bias, MAE and p90 absolute error, for stop times and for link times. Extrapolate down to 11 s.
   - Optionally add N(0, 10–20 m) noise to test robustness.
   - This also measures the speed-selection bias: compare link-speed distributions with and without the passages lost at sparser sampling.
2. **Consistency checks** (no ground truth needed).
   - Passage times rise with stop sequence.
   - Implied link speeds are plausible (e.g. 2–60 km/h), and no more than one stop per 15 s is passed.
   - The sum of link times equals last-minus-first passage on complete trips.
   - Buses on the same route rarely overtake: check the FIFO violation rate across consecutive stops.
   - Look for stops with chronically low detection rates; they usually mean wrong coordinates or the wrong stop pattern.
   - Look at the right tail of first-link times (layover contamination).
   - Count negative dwells.
   - Compare the two methods on the same trips.
3. **Independent proxies.**
   - Offsets from the GTFS timetable (expect large spread; Delhi doesn't follow the timetable).
   - Ticket-machine (ETM) timestamps tagged with a stop or stage, if available. A ticket shows the bus was at that stage at that time, which gives a lower and upper bound on the dwell window.
4. **Small field sample.** Film or log 3–5 stops for about 2 hours, noting bus number, arrival and departure. Or ride along with a 1 Hz phone GPS logger on a few DTC trips; this also gives dense data for the thinning experiment.
5. **Marey diagram per route-day.**
   - x = time, y = distance along the route.
   - Show raw projected points in grey, detected passages coloured by method, and horizontal lines at stop distances.
   - What to look for:

     | Pattern on the chart | Likely meaning |
     |---|---|
     | Backward steps | Projection or loop errors |
     | Long flat runs at terminals | Layover contamination |
     | Vertical jumps | Gaps in the data |
     | Lines crossing | Overtaking or mis-assigned trips |
     | Dots off the lines | Bad passages |

   - Plotly or matplotlib is enough; overlay the GTFS schedule as dashed lines, as in the patent's design.

### Gaps
- No published thinning or degradation experiment was found that evaluates the *timing* of stop events (Newson & Krumm evaluate the path only).
- No Indian field validation of GPS-derived stop times was found.
- No source was found on whether DTC or Delhi ETM data carry stop-level timestamps (see the sibling notes on ETM).
