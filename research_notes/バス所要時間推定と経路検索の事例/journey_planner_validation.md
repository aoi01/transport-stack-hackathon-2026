# Journey planners using observed bus travel times, and how to validate them against actual trips and Google Maps

Context: Delhi Transport Stack Hackathon, Problem 1. Inputs are Delhi bus GTFS static (2,554 routes, 6,812 stops, 65k trips), historical GPS, and GTFS-RT. Entries are judged on accuracy against actual bus trips and against Google Maps.
Research date: 2026-11-14. About 20 tool calls were used, and several primary PDFs could not be retrieved (noted under each Gaps heading).

---

## Q1. How large is the error of schedule-based bus journey times compared with observed times, and how much do observed-speed models improve it?

### Takeaway
Very few studies report the error directly as minutes per journey; most report the effect on accessibility. The best direct measure is from San Francisco: schedule-based journey-time predictions had a median error of 14.9% against GPS-observed trips, and real-time-informed predictions had 11.7%. That is a statistically significant but "marginal" gain.

Accessibility studies show a moderate average bias (−1.5% to −15%) with very large local errors (>40%). Day-to-day variability affects results by about 50%, which is more than the average bias itself.

Delhi's static GTFS is known to be built on a constant-speed assumption with no dwell time. Rebuilding stop_times from GPS should therefore remove a large, systematic error.

### Cited Findings
- **San Francisco (Berkeley ITS).** Two K-shortest-path planners used the same algorithm: one ran on published SFMTA timetables, the other on NextBus predictions. Each planner's predicted trip time was compared with the actual trip time from vehicle GPS traces.
  - Sample: over 600 OD pairs on 87 routes, planned July 23–28, 2009.
  - Median travel-time error: **14.9% (schedule) vs 11.7% (real-time)**, Wilcoxon z = 4.08, p < .00001. The authors call this a marginal improvement.
  - Share of trips where real-time was more / less / equally accurate than schedule:
    - 0 transfers: 41.6% / 39.6% / 18.8% (n = 96)
    - 1 transfer: 51.3% / 42.0% / 6.6% (n = 452)
    - 2 transfers: 48.8% / 39.5% / 11.8% (n = 119)
  - The planner's top route matched the truly fastest route in only about 20–75% of cases, depending on trip type. For trips with transfers, both planners picked the optimal route in only 20.5% of cases.
  - NextBus arrival predictions within a 0–10 min horizon had median error 0 and IQR about 1 min, with 1–5% outliers.
  - Caveat: the per-transfer counts sum to 667, which does not match "600+". — [Berkeley ITS, Mobile Transit Trip Planning with Real-Time Data](https://its.berkeley.edu/publications/mobile-transit-trip-planning-real-time-data)
- **Wessel & Farber (2019), *JTLU*.**
  - Data: archived AVL from 4 North American agencies, reconstructed into a "retrospective GTFS" covering 5 days. Travel times and accessibility were computed at every minute of the peak periods, using both the schedule feed and the retrospective feed.
  - Higher-access zones converge on accessibility **5–15% lower than the schedule predicts**.
  - Lower-access origins give less reliable estimates.
  - Errors are strongly spatially patterned.
  - Momentary (single-minute) measures are only weakly related to real momentary access. — [Wessel & Farber 2019, On the accuracy of schedule-based GTFS for measuring accessibility](https://jtlu.org/index.php/jtlu/article/view/1502)
- **Wessel, Allen & Farber (2017), *J. Transport Geography* 62:92–97.** This paper sets out the method for building a routable retrospective GTFS from a real-time vehicle-location feed (NextBus) plus GTFS. The Toronto (TTC) case study found "substantial aggregate accessibility differences" between scheduled and observed service. The abstract gives no percentage. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jotrge/v62y2017icp92-97.html); [WTR summary](https://worldtransitresearch.info/research/6567)
- **Braga, Loureiro & Pereira (2023), *J. Transport Geography*, Fortaleza.**
  - Method: one month of bus GPS was used to correct the GTFS timetables. They built two feeds, a median-service GTFS and a variability-state GTFS.
  - Scheduled GTFS **underestimates accessibility by about 1.5% on average**. Locally the error exceeds **±40%**, concentrated in low-income areas.
  - Day-to-day variability affects accessibility estimates by about **50% on average** and raises measured inequality by about 30%. — [IPEA publication page](https://ipea.gov.br/acessooportunidades/publication/2023_jtg_public_transport_travel_time_inaccuracy_variability)
- **Liu, Porr & Miller (Columbus, COTA; *J. Geographical Systems* 2023; *JTG* 2024).**
  - Schedule-based accessibility overestimates real access.
  - Retrospective AVL-based measures can also overestimate, because they assume riders have perfect knowledge of delays.
  - They propose "realizable accessibility" based on the space-time prism, the most conservative of the three measures.
  - They define "accessibility unreliability" as realizable minus scheduled accessibility. — [WTR summary](https://www.worldtransitresearch.info/research/10288); [IDEAS JTG 2024](https://ideas.repec.org/a/eee/jotrge/v114y2024ics0966692323002417.html); [Liu publication page](https://luyuliu.github.io/publication/JTG-transitresiliency)
- **Delhi-specific (Tarar, Mukherjee & Rao, 2021).**
  - Data: DIMTS static GTFS compared with OTD real-time positions (10-second pings, 5–20 Jan 2020), plus GPS-app field trips on 1–5 Feb 2020 as ground truth.
  - The static GTFS has **identical arrival and departure times at each stop (no dwell)**. Inter-stop times come from a **constant-speed assumption**, so it is "highly incompatible" with real trips, and trip counts and headways also diverge.
  - On routes 764 UP and GL23 UP, buses arrived early in all periods compared with the schedule.
  - Data quality: on route 764 UP only 2,070 usable records came from about 32,400 expected pings. About 37% of stops had missing data, and the longest gap was about 12 minutes.
  - Route 67: link-level IQR across 42 journeys flags the high-variability links. — [Tarar, Mukherjee, Rao 2021, Scientific Journal of Silesian University of Technology, Series Transport vol. 111](https://sjsutst.polsl.pl/archives/2021/vol111/169_SJSUTST111_2021_Tarar_Mukherjee_Rao.htm)
- **Limits of schedule-based tools.** r5r/R5 percentiles across a time window capture variation in service within the window. They do **not** capture schedule deviation that is missing from the GTFS; the authors point to separate tools that build GTFS reflecting real deviations. — [Pereira et al., r5r, Findings](https://doi.org/10.32866/001c.21262)
- **Google's own model ignores agency schedules.** Google Maps bus-delay forecasts are trained on agency real-time bus-position sequences combined with real-time car-traffic speeds along the route and inferred user bus trips. **Official schedules did not significantly improve forecasts in Google's experiments.** The feature first launched in India. The post gives no aggregate error metric; its only number is that one Sydney trip stayed "within 1.5 min" of the real bus. — [Google Research blog, Predicting Bus Delays with ML](https://research.google/blog/predicting-bus-delays-with-machine-learning/)

### Inferences
- Because Delhi's static GTFS uses constant speed and no dwell, its errors should be **systematic and time-of-day dependent**: too fast in peaks, too slow off-peak (consistent with buses arriving early relative to schedule). Replacing in-vehicle time with GPS-derived **segment × time-of-day bin** medians should remove most of that bias.
  - Plausible gain: from the 15–25% MAPE range down toward the about 10–12% seen in San Francisco. This is not directly measured for Delhi.
- The remaining error after fixing in-vehicle time is dominated by **wait-time and transfer variability**, plus **route choice**. San Francisco showed that even the real-time planner often chose a sub-optimal route. Good wait-time modelling (Q4) therefore matters as much as speeds.
- Google's evidence that schedules add nothing once real positions and traffic speeds are known suggests a strong baseline: GPS segment speeds with time-of-day and day-of-week effects.
- Delhi GPS has gaps (about 37% missing stops on one route in 2020). The pipeline needs gap interpolation between pings, and a fallback to route-level or corridor-level speed per time bin when a segment has too few observations.

### Gaps
- I could not retrieve the full text of Wessel et al. (2017 or 2019), so I have no minutes-level travel-time error numbers (for example, median OD travel-time difference) from them. The 2017 PDF link at sausy.ca returned 404.
- I found no published per-journey MAE (minutes) for schedule vs. observed bus journey times in an Indian city.

---

## Q2. What evaluation protocol is credible for "accuracy against actual bus trips and against Google Maps"?

### Takeaway
A credible protocol has four parts:
1. Hold out GPS days that were not used to build the speed model.
2. Reconstruct "actual" door-to-door journeys from the held-out trajectories: walk + actual wait until the next actual bus + actual ride + actual transfer.
3. Report MAE, MAPE, median absolute error, and % within ±5/±10 min, split by time-of-day and number of transfers. Also report route-choice agreement.
4. Query Google Routes API (TRANSIT) for the same OD and departure times, either live or within its allowed 7-day past window, and score both systems against the same ground truth.

The metrics come from prior studies: percentage error plus a Wilcoxon signed-rank paired test (Berkeley), and MAE/MAPE when a model is compared against Google times. I found no rigorous academic study that validates Google transit ETAs against observed trips. Google publishes no aggregate accuracy figure.

### Cited Findings
- **Berkeley protocol (model for the ground-truth design).**
  - Random OD pairs across the city, queried at different times of day, with predicted trip time recorded at query time.
  - The "actual" trip time and the truly fastest route were reconstructed after the fact from vehicle GPS traces.
  - Metrics: percentage error per trip; Wilcoxon signed-rank test for the paired comparison; share of trips where planner A beat B; and route optimality (did the top route equal the actual fastest route). Results were split by long/short trips and by transfers. — [Berkeley ITS](https://its.berkeley.edu/publications/mobile-transit-trip-planning-real-time-data)
- **Delhi field ground truth.** Tarar et al. validated OTD real-time data against **field trips recorded with a GPS-enabled app**. This kind of independent ground truth could be used for a few hackathon test trips. — [Tarar et al. 2021](https://sjsutst.polsl.pl/archives/2021/vol111/169_SJSUTST111_2021_Tarar_Mukherjee_Rao.htm)
- **Google as the reference.**
  - The Melbourne AToM model used the Google Distance API as the "expected" PT and driving travel time against which simulated times were compared. They noted Google **cannot give estimates for a past trip**, so they used current Google data instead. — [AToM, arXiv 2112.12071](https://arxiv.org/pdf/2112.12071)
  - Another study validated its predicted travel times against Google times using MAE, MAPE, and MSE. — [arXiv 2602.15069](https://arxiv.org/pdf/2602.15069)
- **No academic validation of Google transit ETAs found.** Searches did not surface a study that validates Google transit ETA against observed bus trips with MAE. The nearest item is a student poster from Singapore that compared SGBuses, MyTransport.SG, and Google Maps bus-arrival estimates on 50 samples using mean absolute difference (SGBuses best at 86.02, units probably seconds; Google's figure not in the snippet). — [IASE poster](https://iase-web.org/islp/documents/posters2023/1_Singapore_Poster.pdf)
- **Google Routes API, TRANSIT mode.**
  - `departureTime` **may be in the past up to 7 days** and up to 100 days in the future.
  - `computeAlternativeRoutes` returns up to 3 extra routes.
  - `transitPreferences.allowedTravelModes` (BUS etc.) is only a preference, not a strict filter. `routingPreference` is LESS_WALKING or FEWER_TRANSFERS.
  - No intermediate waypoints.
  - Per-step `transitDetails` include departure and arrival stop, departure and arrival time, headsign, stopCount, and transitLine.
  - Docs note that far-future predictions are not guaranteed consistent and that functionality varies by region. — [Google Routes API, Get a transit route](https://developers.google.com/maps/documentation/routes/transit-route)
- **Google Maps Platform terms (relevant constraints).**
  - Directions API content: lat/lng may be cached temporarily for **up to 30 consecutive calendar days** and must then be deleted. — [Maps Service Specific Terms (archived version)](https://cloud.google.com/archive/maps-platform/terms/maps-service-terms-20251001)
  - Directions API section 3.2: Google Maps content from the Directions API **must not be used together with a non-Google map**. Older archived versions differ on this point. — [Maps Service Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms?hl=sv); [archived 20260604](https://cloud.google.com/archive/maps-platform/terms/maps-service-terms-20260604)
  - General ToS has a "no competing product" clause: you may not use the APIs to create or improve a product that competes with Google Maps. This comes from a third-party transcription and was not verified against the original. — [ConductAtlas summary](https://conductatlas.com/platform/google-maps/google-maps-platform-terms-of-service/no-competing-product-restriction/)
  - Place IDs from the Directions and Routes APIs may be cached. — (search result summary of service terms)

### Inferences
Recommended protocol for the hackathon:
1. **Split.** Build segment and time-bin speeds from GPS days D1…Dn−k. Hold out the last k days (for example, 1 week).
2. **Ground-truth journeys.** Sample about 300–1,000 OD pairs, stratified by distance band (<5, 5–15, >15 km), by 0, 1, or 2 transfers, and by time bin (AM peak, midday, PM peak, night). For each OD and departure t, simulate the "actual" journey on held-out trajectories:
   - walk time from OSM routing;
   - the actual first bus of the chosen route passing the boarding stop after arrival (actual wait);
   - the actual ride time from GPS;
   - for transfers, the actual next bus at the transfer stop.

   This is an oracle replay of the planner's itinerary. Also compute the "best achievable actual journey" by running RAPTOR on a retrospective GTFS of that held-out day, following Wessel et al., to score route-choice optimality.
3. **Systems compared.** (a) Schedule-only GTFS; (b) our observed-time planner; (c) Google Routes API TRANSIT for the same OD and departure. Query Google at or near real time for future departures; the past window is limited to 7 days, so Google queries should be logged during the hold-out week itself.
4. **Metrics.**
   - MAE (min), median AE, MAPE, and bias (mean signed error).
   - % within ±5 min and ±10 min (or ±10% / ±20%).
   - P90 absolute error.
   - Paired Wilcoxon test against the schedule baseline and against Google.
   - Route agreement with Google (same first-boarded route; same set of routes).
   - Every metric broken down by time bin, number of transfers, and distance.
5. **Field validation.** If time allows, record 10–20 real door-to-door trips with a phone GPS app as an independent check, as Tarar et al. did in Delhi.
6. **Terms hygiene.**
   - Store Google results only as derived evaluation metrics (durations, error stats). Do not store route geometries beyond 30 days.
   - Never render Google route content on a non-Google basemap (for example, Leaflet/OSM). Show the Google comparison as a numeric table or chart only.
   - Do not use Google outputs to train or calibrate the model, given the competing-product clause. Use them only as an external benchmark.
   - The organisers likely run their own Google comparison; confirm what they expect.
7. **Honest framing.** Google already uses real-time bus positions plus traffic speeds in India, per its blog. The realistic win is on systematic peak-hour bias and on routes and stops that Google does not cover, not a universal beat. Report where each system is better.

### Gaps
- I could not fetch the current live English Maps Service Specific Terms page (the fetch was truncated), so I have no verified wording on benchmarking or publication of comparisons or for Routes API-specific transit restrictions. Check it manually.
- I found no published Google transit ETA error statistics for Delhi or India.

---

## Q3. Which open-source stack delivers `GET /journeys?from=&to=&depart=` plus a map UI fastest (about 10 days)?

### Takeaway
There are three viable paths:
- **(A) Fastest and most robust: OpenTripPlanner 2 on a rewritten GTFS.** Rewrite `stop_times.txt` so each trip's inter-stop times come from GPS median speeds for that segment and that trip's departure time bin, add dwell, then use OTP's built-in OSM walking, transfers, RAPTOR, and its GTFS GraphQL `planConnection`. Wrap it in a thin FastAPI `/journeys` endpoint.
- **(B) Python-native: r5py** for batch evaluation and travel-time matrices (OD grids, percentiles over a time window).
- **(C) Custom RAPTOR** (pyraptor or your own) only if you need stochastic wait or reliability buffers inside the search.

The cleanest trick in every path is the same: **inject observed times by rewriting GTFS stop_times per time bin**, the retrospective-GTFS idea of Wessel et al. and Braga et al. Do not modify the routing engine.

### Cited Findings
- **OTP2.**
  - Much better performance on large networks than OTP1.
  - Uses GTFS-RT **TripUpdates** for real-time routing changes; Service Alerts no longer affect routing.
  - Recent releases reduce graph-build memory (#6724, #6752), improve GTFS-RT delay propagation (#7106), and allow a missing arrival time at the first stop (#7245).
  - Exposes the GTFS GraphQL API with `planConnection` (#6339).
  - — [OTP v2 vs v1 comparison](https://docs.opentripplanner.org/en/v2.8.0/Version-Comparison/); [OTP changelog](https://docs.opentripplanner.org/en/latest/Changelog/); [GitHub](https://github.com/OpenTripPlanner/OpenTripPlanner)
- **r5py / r5r (Conveyal R5).**
  - Travel time is the median of minute-by-minute runs across a departure time window. r5py docs differ on the default window (10 min in v1.0 docs vs 60 min elsewhere).
  - `frequencies.txt` triggers Monte Carlo draws (r5r default: 5 draws per minute). Without frequencies the time window is still swept deterministically.
  - The departure date must fall within the GTFS `calendar` validity. — [r5py v1.0 travel-time matrices](https://r5py.readthedocs.io/v1.0.0/user-guide/user-manual/travel-time-matrices.html); [r5r manual](https://ipeagit.r-universe.dev/r5r/doc/manual.html); [r5r time_window vignette](https://cran.r-universe.dev/r5r/doc/time_window.html)
- **Conveyal methodology.** R5 by default assumes **perfect reliability** of transit operations. With frequency-based routes, travel-time distributions also reflect how the simulated schedules interact; lower percentiles mean shorter simulated waits. — [Conveyal methodology docs](https://docs-5tf7pbyrq-conveyal.vercel.app/analysis/methodology)
- **pyraptor (lmeulen).**
  - Python RAPTOR and McRAPTOR on GTFS (tested on Dutch GTFS).
  - Supports single queries, range queries over a departure window, and Pareto multi-criteria (arrival, fare, number of trips).
  - Pre-processes GTFS into an optimized timetable; MIT license; on PyPI. — [GitHub lmeulen/pyraptor](https://github.com/lmeulen/pyraptor); [PyPI](https://pypi.org/project/pyraptor)
  - Alternatives: PatrickSteil/RAPTORPython; planarnetwork/raptor (TypeScript). — [RAPTORPython](https://github.com/PatrickSteil/RAPTORPython); [planarnetwork/raptor](https://www.github.com/planarnetwork/raptor/blob/010c90b5110c1493fb4e349b192c6b0dad4d3916/README.md)
- **Retrospective GTFS method.** Archived vehicle locations are converted into a GTFS whose `stop_times` reflect the actual trips, so any GTFS router can use them. — [Wessel, Allen & Farber 2017](https://ideas.repec.org/a/eee/jotrge/v62y2017icp92-97.html); [Braga et al. 2023 (median-service and variability-state GTFS)](https://ipea.gov.br/acessooportunidades/publication/2023_jtg_public_transport_travel_time_inaccuracy_variability)
- **Delhi data availability.**
  - The OTD portal (IIIT-Delhi with DIMTS) publishes static GTFS and a real-time feed with about 10-second updates. — [Delhi OTD documentation](https://otd.delhi.gov.in/documentation); [Medium: Delhi launches OTD](https://medium.com/redact/delhi-government-launches-open-transit-data-platform-for-buses-b1ed9b80e996)
  - Chartr describes itself as the data backbone of the Delhi Transport Stack (vendor claim). — [Chartr Transport Stack](https://chartr.in/products/transport-stack/)
  - MobilityDatabase lists a DTC GTFS feed. — [MobilityDatabase mdb-3139](https://mobilitydatabase.org/feeds/gtfs/mdb-3139)

### Inferences
Suggested plan for 10 days (my synthesis, not taken from a source):
- **Day 1–2: GPS processing.**
  - Map-match GPS pings to GTFS shapes and routes, or project onto the stop sequence by linear referencing.
  - Derive stop-passage times by interpolating between pings.
  - Compute per (route_id, direction, from_stop → to_stop, time bin of 30–60 min, weekday/weekend): the median and P85 link time, plus dwell.
  - Fallbacks for sparse cells: same segment in other time bins (scaled), then corridor or route average speed, then the original schedule.
- **Day 3: GTFS rewriting.** For each of the 65k trips, walk the stop sequence, cumulatively adding the observed link and dwell times for the bin in which the bus *reaches* each segment (time-dependent propagation). Write `stop_times.txt` with real arrival ≠ departure. Validate with gtfs-validator. Optionally emit a second "P85/pessimistic" GTFS for reliability buffers.
- **Day 3–4: routing engine.** Use OTP2 with Delhi OSM plus the rewritten GTFS.
  - Graph build for a city of Delhi's size likely needs about 8–16 GB RAM (unverified estimate).
  - OTP gives walk access and egress, transfers on the OSM street graph, and itineraries with legs and polylines.
  - Optionally attach the GTFS-RT TripUpdates updater for "now" queries.
  - Alternative: r5py if the team is Python-only and needs mass OD evaluation; it returns travel-time matrices and detailed itineraries but has a weaker interactive API.
- **Day 5: API.** FastAPI `GET /journeys?from=lat,lon&to=lat,lon&depart=ISO` calls OTP GraphQL and post-processes:
  - adds a wait-time model (Q4);
  - adds P50 and P85 total-time bands;
  - returns legs (walk, bus with route, stops, times) as JSON and GeoJSON.
- **Day 6: UI.** MapLibre GL or Leaflet with OSM tiles: click-to-set origin and destination, a departure-time picker, and itinerary cards. Do not draw Google routes on this map; show the Google comparison numerically.
- **Day 7–9:** run the evaluation harness from Q2 and tune bins and fallbacks.
- **Day 10:** demo and write-up.
- **Why rewrite GTFS instead of using a custom RAPTOR:** OTP and R5 handle OSM walking, transfer generation, and stop snapping, which are the slowest parts to build from scratch.
- **When to choose a custom RAPTOR (pyraptor):** when you need time-dependent stochastic waits or reliability-aware (P85) criteria inside the search. pyraptor's McRAPTOR could add "reliability" as a criterion. Pure Python RAPTOR on 65k trips is feasible but slow for range queries; precomputing footpaths from OSM is extra work.
- **Frequency-based GTFS alternative:** convert high-headway irregular routes into `frequencies.txt` with observed mean headway per bin, and let R5 Monte Carlo draws represent waiting uncertainty. Caveat: OTP2's support for `frequencies.txt` is less natural than R5's, so test it.

### Gaps
- I did not verify current OTP2 graph-build RAM and time for Delhi-scale data. The OTP RealtimeUpdaters docs page returned 503.
- I did not verify r5py's current default `departure_time_window`; the docs conflict.
- I did not determine whether the hackathon GTFS includes `shapes.txt` (affects map matching).

---

## Q4. How should waiting time be modelled for unreliable or long-headway buses (headway/2, reliability buffers)?

### Takeaway
Use the irregular-headway formula E[W] = H̄·(1 + CV²)/2, with observed headways per stop × route × time bin, rather than H/2. Add a reliability buffer (P95 minus mean wait, or the Uniman reliability buffer time) for a "plan-safe" journey time.

For long headways (roughly >10–12 min, common in Delhi), riders time their arrival. Wait should then be modelled as schedule- or prediction-anchored: actual next-bus wait plus an early-arrival margin, not half the headway.

### Cited Findings
- **Random-arrival waiting.** Under random passenger arrivals, mean wait is half the headway. With irregular headways (Welding 1957; Holroyd & Scraggs 1966; Osuna & Newell 1972), the expected wait is mean headway × (1 + C²)/2, where C is the headway coefficient of variation. C is widely used as a reliability measure. — [core.ac.uk thesis on transit reliability](https://core.ac.uk/download/235055197.pdf); [ETH research collection](https://research-collection.ethz.ch/bitstream/handle/20.500.11850/64815/eth-30952-01.pdf)
- **Furth & Muller (2006).**
  - Traditional measures separate waiting from reliability and so underestimate the real cost of waiting.
  - They introduce **potential waiting time**: the extra time passengers must budget, typically P95 wait minus mean wait.
  - **Excess waiting time** is actual wait minus scheduled wait. — [WTR: Service Reliability and Hidden Waiting Time](https://www.worldtransitresearch.info/research/402); [Changzhou BRT reliability](https://www.academia.edu/83312002/Measuring_Bus_Service_Reliability_An_Example_of_Bus_Rapid_Transit_in_Changzhou)
- **Reliability buffer time (Uniman et al. 2010).** Budgeted journey time (for example, P95) minus mean journey time, per OD and time interval. It is passenger-oriented, in contrast to the operator-oriented headway CV. — [core.ac.uk](https://core.ac.uk/download/235055197.pdf)
- **R5's treatment.** R5 assumes perfect reliability. For frequency routes it simulates random schedules, and the chosen percentile reflects both departure choice and wait. — [Conveyal methodology](https://docs-5tf7pbyrq-conveyal.vercel.app/analysis/methodology)
- **Realizable accessibility.** Assuming perfect knowledge of delays, as AVL-retrospective routing implicitly does, overestimates what riders can achieve. — [Liu/Porr/Miller WTR](https://www.worldtransitresearch.info/research/10288)

### Inferences
Implementation for the planner:
- From GPS, compute actual headways at each stop × route × 30–60 min bin, giving H̄ and CV.
- **First-boarding wait:**
  - If live GTFS-RT exists for "now" queries: use the predicted arrival plus a small margin.
  - Otherwise, for future or departure-time queries with H̄ ≤ about 12 min: E[W] = H̄(1 + CV²)/2.
  - For H̄ > about 12 min: assume riders arrive about 2–5 min before the expected bus, so wait = margin + the expected lateness spread.
- **Transfer wait:** use the same formula. Transfers cannot be timed, so the random-arrival formula fits better there.
- **Output:** expected total time (P50) plus a "safe" time (P85/P95) built from wait P95 and ride-time P85. Report both in the JSON.
- **Evaluation:** the "actual" journey in Q2 uses the real next bus, so the wait model is directly testable. Compare the H/2, H(1 + CV²)/2, and oracle variants.
- The Berkeley results (real-time helps most when transfers are involved) and the Fortaleza result (variability about 50% of the effect) suggest that **wait and transfer modelling is where much of the remaining error lies**.

### Gaps
- I did not retrieve the original Furth & Muller (2006) or Uniman et al. (2010) text, so the exact definitions above come from secondary summaries.
- I found no Delhi-specific measurements of headway CV or passenger arrival behaviour.
- The ~12 min threshold between random and timed passenger arrival is a rule of thumb from my background knowledge, not a cited value in these notes.
