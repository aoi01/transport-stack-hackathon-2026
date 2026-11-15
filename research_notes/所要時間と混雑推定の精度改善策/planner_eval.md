# Journey-planner improvement and rigorous evaluation (observed travel times + crowding, Delhi bus prototype)

Evidence-strength tags used below: **[S]** = primary text read directly (paper body or official docs); **[M]** = peer-reviewed, but only the abstract or a search-engine summary of the abstract was seen; **[W]** = news, secondary or third-party summary, or a figure whose provenance I could not confirm. All Google facts were read from developers.google.com on **2026-11-16**; none of those pages showed a "last updated" date.

---

## 1. Evaluation protocols that replay AVL data: journey-level accuracy and route-choice optimality

### Takeaway
The standard method is the one Berkeley used in 2011: plan trips for random OD pairs and times, rebuild what actually happened from the vehicle GPS traces, then score (a) the predicted versus realized door-to-door time of the recommended path and (b) whether the top recommendation was the realized fastest option, using paired tests. In that study real-time data cut the median error only from 14.9% to 11.7%. On trips with transfers, the real-time planner's top pick was the realized fastest option in only about 44% of cases (schedule-based: about 36%). The "~20%" figure often quoted is the share of cases where *both* planners got it right. Later work (Toronto, Fortaleza) turns archived AVL into a routable "retrospective" or "corrected" GTFS, which is the natural ground truth to replay against.

### Cited Findings
**Berkeley / UCTC "Transitr" study (the SF study in the brief) [S]**
- Jariyasunant, Work, Kerkez, Sengupta, Glaser & Bayen, "Mobile Transit Trip Planning with Real-Time Data", UC Transportation Center report UCTC-FR-2011-14 (Sept 2011). The planner ran a dynamic K-shortest-paths search over predicted link times, using NextBus real-time arrival predictions. It returned the 5 fastest routes, from precomputed feasible paths with at most 3 transfers. — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Protocol: more than 600 trips were planned with a schedule-based planner and with the real-time planner. OD pairs were drawn spatially uniformly at random over San Francisco, at various times of day, July 23–28 2009, on SFMTA buses and light rail (87 routes). Ground truth was the actual travel time along each path, reconstructed after the trip from on-board GPS. The same GPS tracks were used to find the *actual fastest* route for each OD. — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Component check first: 23,349 NextBus predictions were scored. Predictions 0–10 min ahead had a median error of 0, with the IQR within about 1 min. Error variance grows with the prediction horizon, and there were outliers in 1–5% of cases. More than 400 of the ~600 trips needed transfers occurring more than 10 min after the request. — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Journey-time accuracy: a Wilcoxon signed-rank test was run on the paired percentage errors of the two planners. Median error was 14.9% (schedule) vs 11.7% (real-time), z = 4.08, p < 0.00001. The authors call the improvement "marginal". — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Real-time accuracy by number of transfers (count of trips where real-time was more / less / equally accurate):
  - 0 transfers: 40 (41.6%) / 38 (39.6%) / 18 (18.8%)
  - 1 transfer: 232 (51.3%) / 190 (42.0%) / 30 (6.6%)
  - 2 transfers: 58 (48.8%) / 47 (39.5%) / 14 (11.8%)
  - That gives n ≈ 96 / 452 / 119, about 667 trips in total.
  - — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Route-choice optimality (Table 1, % of cases; only each planner's top-1 route was scored against the GPS-derived fastest route):

  | Outcome | Long (>30 min) | Short (≤30 min) | With transfers | No transfers |
  |---|---|---|---|---|
  | Both planners picked the optimal route | 27.3 | 44.4 | 20.5 | 75.0 |
  | Only real-time picked it | 20.3 | 16.7 | 23.8 | 0.0 |
  | Only schedule-based picked it | 14.1 | 11.0 | 15.6 | 4.1 |
  | Neither (real-time's pick was faster) | 12.5 | 11.2 | 13.9 | 4.2 |
  | Neither (schedule's pick was faster) | 10.2 | 5.6 | 11.4 | 0.0 |
  | Neither (same pick) | 15.6 | 11.1 | 14.8 | 16.7 |

  — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- The authors conclude that accuracy drops with how far ahead the planner must predict, and that transfers often happen more than 30 min after planning, which causes missed transfers. They recommend re-planning en route and building uncertainty into predictions. — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Context from the same paper: San Francisco schedule adherence at the time was about 70%. — [eScholarship](https://escholarship.org/uc/item/51t364vz)

**Fortaleza: GPS-corrected GTFS (Braga, Loureiro & Pereira 2023, J. Transport Geography 109:103590) [M/S]**
- One month of archived bus GPS was used to build corrected GTFS timetables in two versions: a median level of service and a "variability-state" level of service. Results:
  - The scheduled GTFS underestimates accessibility by 1.5% on average, but by more than 40% (over or under) in some areas, especially low-income ones.
  - Day-to-day travel-time variability has an average impact of 50% on accessibility estimates and raises measured accessibility inequality by 30%.
  - — [urbandemographics.org summary page](https://www.urbandemographics.org/publication/2023_jtg_public_transport_travel_time_inaccuracy_variability/)

**Retrospective GTFS from AVL (Toronto and other North American agencies) [M]**
- Wessel, Allen & Farber (2017, J. Transport Geography 62:92–97) built a *routable retrospective timetable* from a real-time vehicle-location feed plus GTFS. In a Toronto (TTC) case they found substantial aggregate accessibility differences between scheduled and observed service. — [World Transit Research](https://worldtransitresearch.info/research/6567); [EconPapers](https://econpapers.repec.org/RePEc:eee:jotrge:v:62:y:2017:i:c:p:92-97)
- Wessel & Farber (2019, J. Transport and Land Use, doi 10.5198/jtlu.2019.1502) used archived AVL from four agencies, including TTC, as routable ground truth. Real accessibility in high-access zones was about 5–15% below the schedule's prediction, and low-access origins showed more hour-to-hour variability. — [JTLU](https://jtlu.org/index.php/jtlu/article/view/1502)

**Learning from past observation days, evaluated on held-out days (Zurich) [M]**
- Böhmová, Mihalák, Pröger, Šrámek & Widmayer (ATMOS 2013) take "daily records" of observed travel times across the whole network for a few past days. They find journeys that are feasible in any record and define a reliability measure for a journey. They target large cities with high-frequency, non-hierarchical networks, which fits Delhi buses. — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2013.27)
- The follow-up (ATMOS 2015) evaluates these strategies on real Zurich delay data against natural baselines. It shows that how "typical" the past observations are relates to each method's predictive quality. — [Maastricht CRIS](https://cris.maastrichtuniversity.nl/en/publications/robust-routing-in-urban-public-transportation-evaluating-strategi)
- Geissmann & Gianinazzi (ATMOS 2019) evaluated on Zurich delay data and report on-time arrival as the outcome metric (detail in Q2). — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2019.4)

### Inferences
- **Correction to the brief.** "Optimal route only ~20% with transfers" is the *both-planners-correct* cell. Derived from Table 1, the real-time planner's own top-1 hit rate was:
  - 44.3% on transfer trips (schedule-based: 36.1%)
  - 75.0% on no-transfer trips (schedule-based: 79.1%)
  - 47.6% on trips over 30 min and 61.1% on trips of 30 min or less (schedule-based: 41.4% / 55.4%)
  - In 40.1% of transfer trips, *neither* planner chose the fastest route.
  - So route-choice optimality is mainly a transfer problem, and live data alone helped only modestly.
- **Statistical power, back-calculated from Berkeley.** On the 571 transfer trips, the discordant pairs were about 136 (only real-time correct) vs about 89 (only schedule correct). That gives McNemar χ² ≈ (136−89)²/225 ≈ 9.7, p ≈ 0.002. So a sample of about 600 OD×time instances can detect a hit-rate gap of about 8 percentage points between two planner variants.
  - To estimate a single hit rate within ±5 pp (95% CI) you need about 385 instances; for ±3 pp, about 1,070.
  - Our current 200 OD pairs give roughly ±7 pp on a proportion, so add departure-time replicates (for example 200 OD × 3–5 times of day) and cluster bootstrap CIs by OD.
- **Recommended replay protocol for the held-out week.** It mirrors Berkeley and the retrospective-GTFS approach:
  1. Turn held-out AVL into a *realized timetable*: per trip, stop arrival and departure times interpolated from GPS.
  2. For each sampled (OD, departure time t0), take the planner's prediction made at t0 using only information available at t0 (no leakage of held-out GPS into the medians or "live" corrections; simulate live positions as of t0).
  3. Simulate the traveller following the top option: walk, board the first *actual* vehicle of the recommended route arriving after them, ride realized times, then transfer under the same walking and slack rules. Record the realized door-to-door time.
  4. Compute the *oracle*: the best realized itinerary, from an exact router (for example RAPTOR) run on the realized timetable with the same walking, transfer and slack constraints.
  5. Report:
     - signed bias plus MAE / median APE / P90 absolute error in minutes
     - share of trips within ±5 and ±10 min
     - top-1 and top-3 hit rate
     - regret (realized time of the chosen option − oracle): mean, P90, and % with more than 5 min regret
     - all stratified by number of transfers, trip length (≤30 / >30 min), peak vs off-peak, and prediction horizon
  6. Tests: Wilcoxon signed-rank for paired errors (as Berkeley did); McNemar for paired hit rates; OD-clustered bootstrap CIs.
- For the hackathon's "known actual travel times for sample location pairs", report the same door-to-door metrics (MAE in minutes, MAPE, share within ±5/±10 min) for **our planner and Google against the same ground truth**. Add a paired "win rate" (share of pairs where we are closer) with a sign test or Wilcoxon.

### Gaps
- The Fortaleza paper's journey-level error numbers (as opposed to accessibility deltas) and its exact number of GPS days were not visible on the summary page.
- Wessel & Farber's Toronto-specific percentage was not retrieved.
- I found no published replay study of a journey planner in an Indian city.
- I found no study reporting top-3 hit rates or regret distributions for bus planners, beyond Berkeley's top-1 table.

---

## 2. Reliability-aware routing (percentile times, mean–variance or risk-averse routing, "leave by" buffers)

### Takeaway
The strongest quantified evidence of a user outcome is Geissmann & Gianinazzi (ATMOS 2019). Replaying Zurich delay data, stochastic and adaptive routing got travellers to the destination on time 5–11 percentage points more often than schedule-based routing for most destinations, and 20–40 points more often for some remote ones, at about 0.1 s per query. Engines such as R5 already produce travel-time *percentiles* for headway-based service by Monte Carlo. I found no controlled field evidence that "leave-by" buffers shown in apps change user outcomes.

### Cited Findings
- Geissmann & Gianinazzi, "Routing in Stochastic Public Transit Networks" (ATMOS 2019). They build robust, adaptive policies on temporal graphs where connections fail at random, in near-linear time. On real Zurich delay data, compared with a purely schedule-based policy, travellers arrive on time 5–11 pp more often for most destinations and 20–40 pp more often for certain remote destinations. A policy for 1-hour journeys is computed in about 0.1 s. **[S – abstract page]** — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2019.4)
- Böhmová et al. (2013) define a journey reliability measure computed from past daily records, with algorithms to compute it. **[M]** — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2013.27)
- Berkeley Transitr: the error variance of real-time predictions grows with horizon. The authors recommend "incorporation of uncertainty into bus arrival estimates" and en-route re-planning to handle missed transfers. **[S]** — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- Fortaleza: day-to-day variability shifts accessibility estimates by 50% on average. A single median timetable hides most of what travellers experience. **[M/S]** — [urbandemographics.org](https://www.urbandemographics.org/publication/2023_jtg_public_transport_travel_time_inaccuracy_variability/)
- R5 (Conveyal), via r5r: an R5-specific RAPTOR extension samples many simulated schedules when service is defined by headways (frequencies.txt). Defaults are 5 Monte Carlo draws per minute of the departure window, and results are reported at chosen travel-time percentiles (default median; up to 5 percentiles). **[S – package docs]** — [r5r time_window vignette](https://cloud.r-project.org/web/packages/r5r/vignettes/time_window.html)
- The method comes from Conway, Byrd & van der Linden (2017, TRR 2653), who apply Monte Carlo methods to the uncertainty that arises when routes are specified by headways rather than timetables. **[M]** — [TRB preprint](https://d1rbsgppyrdqq4.cloudfront.net/s3fs-public/c160/TRB_17-06602_TRR_manuscript_preprint.pdf)
- RAPTOR's journal version names "reliability of transfers" (with fare zones) as an example of an extra McRAPTOR criterion. **[M]** — [IDEAS/RePEc abstract](https://ideas.repec.org/a/inm/ortrsc/v49y2015i3p591-604.html)
- Google transit underestimates door-to-door commute time by about 5 min relative to self-reported times in Canada. This suggests point estimates without buffers are biased low for transit (see Q5). **[S]** — [Findings](https://findingspress.org/article/143380-exploring-the-mis-match-between-reported-and-calculated-commute-travel-times)

### Inferences
- Our medians plus expected waits are point estimates. To rank by reliability, propagate distributions along each itinerary:
  - in-vehicle-time quantiles per segment and time of day from GPS
  - the empirical headway distribution, including bunching (random-arrival wait ≈ E[H]/2·(1+CV²), a standard result not re-sourced here)
  - for near-term departures, live positions
  - combined by Monte Carlo, R5-style
- Rank by P50 (or by mean + λ·SD), and show "leave by" = target arrival − P85/P90.
- Evaluate **calibration** on the held-out week. Check that realized times fall at or below the predicted P90 about 90% of the time (coverage), and compute a CRPS/pinball loss for the predicted quantiles.
- Report the on-time rate for a stated deadline (the Geissmann metric) for "fastest-median" versus "reliable" recommendations on the same OD set.
- The live-correction horizon matters. Berkeley's NextBus predictions were good up to about 10–15 min ahead but degraded beyond that. So use live positions mainly for the first wait and the first leg, and fall back to historical distributions for later legs and transfers.

### Gaps
- No quantified value-of-reliability (reliability ratio) for Indian bus users was found.
- No randomized or field study was found showing that displaying "leave-by" buffers improves punctuality or satisfaction.
- No India-specific evaluation of risk-averse transit routing was found.

---

## 3. Transfer modelling in irregular networks (minimum transfer time, missed-connection risk, synchronization)

### Takeaway
Transfers are where planners fail. In the Berkeley replay, trips with transfers had the lowest rate of choosing the optimal route, and the authors attribute large errors to missed transfers predicted more than 30 min ahead. Mature engines use an explicit transfer slack (OpenTripPlanner default: 2 min) plus walk time. The literature measures missed-transfer risk empirically from AVL (as Risk of Missing Transfers and total time penalty). Stochastic or adaptive policies that account for failing connections give measurable on-time gains.

### Cited Findings
- Berkeley:
  - More than 400 of ~600 trips needed transfers occurring more than 10 min after the request.
  - Estimation errors at transfer points ("often occur greater than 30 minutes from the time the trip is initially planned") led to "missed transfers and large discrepancies".
  - The share of transfer trips where both planners chose the actual fastest route was only 20.5%, versus 75.0% without transfers.
  - Real-time data helped most on 1-transfer trips (51.3% more accurate vs 42.0% less accurate).
  - **[S]** — [eScholarship](https://escholarship.org/uc/item/51t364vz)
- OpenTripPlanner 2 defaults:
  - `transferSlack` = PT2M ("the extra time needed to make a safe transfer"); `boardSlack` = 0; `alightSlack` = 0
  - walk speed 1.35 m/s; `walkReluctance` 2.0; `waitReluctance` 1.0; `transferPenalty` 0 ("additional penalty added to boardings after the first")
  - Transfers are optimized after the Raptor search.
  - **[S]** — [OTP RouteRequest docs](https://docs.opentripplanner.org/en/latest/RouteRequest/)
- Liu & Miller (2020/2021, Urban Studies) define:
  - Risk of Missing Transfers (RoMT), the empirical probability of a missed bus-to-bus transfer
  - Average Total Time Penalty, the time lost against the schedule
  - Both are computed from GTFS plus real-time or APC data for COTA (Columbus, Ohio). **[S – abstract page]** — [OSU summary](https://u.osu.edu/miller.81/2020/06/17/measuring-risk-of-missing-transfers-in-public-transit-systems-using-high-resolution-schedule-and-real-time-bus-location-data)
  - Back-to-school season and Fridays show higher risk and penalty. RoMT is *not* significantly correlated with frequency. Simulated dedicated bus lanes cut the average time penalty. **[M]** — [IDEAS/RePEc](https://ideas.repec.org/a/sae/urbstu/v58y2021i15p3140-3156.html)
- University of Brescia: an offline framework that preprocesses archived AVL (about 145,000 records on real routes) to diagnose where and when planned transfers are not delivered, plus a "rate of transfers" method between route pairs. **[M]** — [IRIS UniBS paper 1](https://iris.unibs.it/bitstream/11379/541728/7/09369876.pdf); [IRIS UniBS paper 2](https://iris.unibs.it/retrieve/ddc633e4-68cc-4e2e-e053-3705fe0a4c80/1-s2.0-S2352146521009534-main.pdf)
- Mai, List & Hranac (2012, TRR) simulated the travel-time impact of missed connections in San Diego as a function of passenger arrival rate, on-time performance and schedule design. **[W – abstract listing]** — [World Transit Research](https://www.worldtransitresearch.info/research/4567)
- Adaptive (fallback-aware) routing that treats connections as able to fail: +5–11 pp on-time (Zurich). **[S – abstract]** — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2019.4)

### Inferences
- For Delhi's headway-driven and irregular service, model the second-leg wait as conditional on the *arrival-time distribution* at the transfer stop. Use:
  - live positions of the connecting route's vehicles if the transfer is within about 15 min
  - otherwise the observed headway distribution for that stop and hour
  - plus a slack (start with 2 min, OTP-style, then calibrate) plus walk time at *network* distance (our 250 m straight-line radius may hide road-crossing detours)
- Score each itinerary by P(make planned connection) and by the expected time *including the fallback* (the next vehicle on the same or a parallel route), rather than assuming the transfer is always made.
- Evaluate transfers separately in the replay:
  - share of recommended transfers actually made in the realized timetable
  - realized transfer wait vs predicted (bias, MAE)
  - hit rate and regret for transfer vs non-transfer itineraries
- Our ≤1-transfer cap may cut off options. About 18% of Berkeley's planned trips (119 of ~667) used 2 transfers. Measure how often an exact router on our network finds a strictly better 2-transfer option.

### Gaps
- No published headline "percentage of planned bus transfers missed" was retrieved. The Liu & Miller and Brescia numbers are inside the full texts, which were not accessible.
- No Delhi or India study on transfer synchronization or missed-connection rates was found.

---

## 4. Access/egress walking: straight-line × detour vs OSM network walking

### Takeaway
A single global 1.3× factor is a reasonable average but a poor per-OD model. Indian guidance (IRC:103 draft) treats a pedestrian detour ratio of up to 1.5 as the *acceptable* design limit, and the 19–20% average route lengthening in car-dominated stop surroundings shows that real walks deviate from simple factors. Network walking (OSM) captures barriers such as arterials without crossings, rail lines, drains and gated colonies, which straight-line methods miss. In six Indian cities, switching from Euclidean to network distance changed the cities' accessibility rankings. No India-specific OD-level error statistics for "Euclid × factor vs network" were found.

### Cited Findings
- IRC:103 (Guidelines for Pedestrian Facilities, draft) sets the pedestrian detour ratio (actual walking distance / direct distance) to be **within 1.5**. It also recommends that the nearest bus stop and IPT stand be within 50 m of a crossing. **[M – draft guideline; final may differ]** — [NITI for States PDF](https://www.nitiforstates.gov.in/public-assets/Policy/policy_files/GNANAO000329.pdf)
- "Pedestrian Access to Public Transport" (2022): car-dominated surroundings of stops lengthen walking routes by **19–20% on average**, and about 20% of people do not take the shortest walking path to stops. **[W – ResearchGate abstract]** — [ResearchGate](https://www.researchgate.net/publication/365610936_Pedestrian_Access_to_Public_Transport)
- Yenisetty & Bahadure (2020, ISPRS IJGI 9(7):446) compared Euclidean distance with OSM road-network distance from transit stops to amenities in six Indian cities. The choice of distance measure **changes city rankings**. **[M]** — [Semantic Scholar record / DOI](https://doi.org/10.3390/ijgi9070446)
- Delhi walking distances:
  - Mean walk from bus stops to destinations of 659 m (men) and 640 m (women). **[W]** — [ResearchGate](https://www.researchgate.net/publication/296873395_A_study_for_commuter_walk_distance_from_bus_stops_to_different_destination_along_routes_in_Delhi)
  - Delhi Metro walk access: mean 590 m, and 86% of walk-access trips are ≤800 m. **[W]** — [ResearchGate](https://www.researchgate.net/publication/342028948_How_Far_People_Can_Walk_to_Access_Metro_A_Study_of_Access_Trip_Characteristics_of_Delhi_Metro_Users)
- Boeing (2017/2019) used OSM walkable and drivable networks for 40 US cities and about 4 million simulated routes. Walking networks are generally less circuitous than driving networks, and circuity "varies substantially" across place types. **[S – abstract page]** — [arXiv 1708.00836](https://arxiv.org/abs/1708.00836)
- Poudyal, Ghoshal & Kirkley (2023, J. R. Soc. Interface) show that pairwise network circuity separates cities by development level and region. The detour factor is city-specific, not universal. **[S – abstract]** — [arXiv 2305.09194](https://arxiv.org/abs/2305.09194)
- Google's walking times match self-reported walking times closely (difference about 1 min overall and not significant in most regions). Transit and car times show about a 5-min mismatch. **[S]** — [Findings](https://findingspress.org/article/143380-exploring-the-mis-match-between-reported-and-calculated-commute-travel-times)
- OTP's default walk speed is 1.35 m/s (4.86 km/h), versus our 4.5 km/h (1.25 m/s). **[S]** — [OTP docs](https://docs.opentripplanner.org/en/latest/RouteRequest/)

### Inferences
- Error magnitude for our parameters:
  - An 800 m straight-line access walk at ×1.3 and 4.5 km/h gives 1,040 m, or about 13.9 min.
  - If the true ratio is 1.1 or 1.5, the time is about 11.7 or 16.0 min, roughly ±2 min *per end* and up to ±4 min door-to-door. That is comparable to typical in-vehicle prediction errors.
  - Barriers can push individual ratios above 2, and can also make the "nearest" stop the wrong stop.
- Cheap upgrade: compute OSM foot-network distances (OSRM, Valhalla or OTP street routing) from each origin and destination to the K nearest stops, and for transfer pairs within 250 m. Keep straight-line ×1.3 only as a fallback.
- Measure locally: sample about 1,000 random point→stop pairs in Delhi and report the distribution of network/Euclidean ratios (median, P90, share >1.5), by distance band and ward type. Then report how often the chosen boarding stop changes and how much door-to-door time changes.
- Walk speed: 4.5 km/h is plausible for Delhi, but heat, crowding and crossing waits add time. Calibrate it, or add a fixed crossing penalty, against field-measured door-to-door trips if the hackathon's "known actual times" include walking.

### Gaps
- No measured India-specific OD-level error of Euclid×1.3 versus OSM network walking was found.
- The detour indices by city in Yenisetty & Bahadure were not accessible (MDPI returned HTTP 403).
- No Delhi-specific pedestrian detour-ratio dataset was found.

---

## 5. Google Maps comparison: Routes API transit (2025–2026), pricing, limits, past departure times, Terms of Service, published accuracy

### Takeaway
As of 2026-11-16:
- The **Routes API** is the only non-legacy route API. Directions API and Distance Matrix became Legacy on **2025-03-01**.
- TRANSIT requests are the only mode that **may use past departure times, up to 7 days back** (future: up to 100 days).
- Compute Routes has a free monthly cap per SKU tier (Essentials 10,000 / Pro 5,000 / Enterprise 1,000), then $5 / $10 / $15 per 1,000 calls. The quota is 3,000 QPM, and transit route matrices are capped at 100 elements per request.
- Policies forbid storing or pre-fetching Google content outside the Services (except coordinates cached up to 30 days, and place IDs), forbid bulk download of directions, and forbid creating content from Google results.

Published independent accuracy evidence for Google transit ETAs is thin. The best study (Canada, 2025) finds Google transit door-to-door times are about 5 min *shorter* than reported times. Nothing comparable was found for India.

### Cited Findings
**API status and behaviour (official docs, read 2026-11-16) [S]**
- Directions API, Distance Matrix API, the JS Directions Service and the JS Distance Matrix Service all became **Legacy on March 1, 2025**. Replacements are the Routes API and the JS Route/RouteMatrix classes. Docs: "In most cases, keep legacy APIs disabled on new projects"; there is a feedback-form route to activate the legacy APIs as a short-term workaround. — [Google Maps Platform legacy page](https://developers.google.com/maps/legacy)
- computeRoutes, departure and arrival times:
  - `departureTime` defaults to request time. A past `departureTime` is allowed **only when travelMode = TRANSIT**: "Transit trips are available for up to 7 days in the past or 100 days in the future."
  - `arrivalTime` is honoured only for TRANSIT. You can specify `departureTime` or `arrivalTime`, but not both.
  - `routingPreference` (traffic awareness) is only for DRIVE or TWO_WHEELER.
  - Alternatives: the reference says the `routes` array "can hold up to three routes" when alternatives are computed, with none if intermediate waypoints are used. The transit guide says "up to 3 additional routes". The wording conflicts, so assume at most about 3–4 itineraries per call.
  - `transitFare` is text only. Step stop times are "estimated".
  - — [computeRoutes reference](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes)
- Transit guide:
  - Response fields: `transitDetails` (`stopDetails` arrival/departure stop with name and location, `arrivalTime`/`departureTime`, `headsign`, `transitLine` {agencies, name, nameShort, color, textColor, vehicle}, `stopCount`), `localizedValues`, and `stepsOverview`.
  - `transitFare` is "only provided if the API can determine transit fare information for all steps".
  - `transitPreferences.allowedTravelModes` takes BUS, SUBWAY, TRAIN, LIGHT_RAIL or RAIL, but other modes may still be returned. `routingPreference` takes LESS_WALKING or FEWER_TRANSFERS.
  - No intermediate waypoints for transit. Up to 3 additional routes.
  - "Transit schedules change frequently… no guarantee to provide consistent results for predictions far in advance."
  - — [Routes API transit guide](https://developers.google.com/maps/documentation/routes/transit-route)
- Quotas:
  - Compute Routes: **3,000 queries per minute**.
  - Compute Route Matrix: **3,000 elements per minute**. Maximum elements per request: **100 for TRANSIT** (also 100 for TRAFFIC_AWARE_OPTIMAL), 625 otherwise.
  - — [Routes API usage & billing](https://developers.google.com/maps/documentation/routes/usage-and-billing)
- Pricing (USD per 1,000 billable events per month, tiers aggregated per billing account):
  - Compute Routes **Essentials**: free cap 10,000, then $5.00 (to 100k), $4.00 (100k–500k), $3.00 (500k–1M), $1.50 (1M–5M), $0.38 (5M+)
  - **Pro**: free 5,000, then $10.00 / 8.00 / 6.00 / 3.00 / 0.75
  - **Enterprise**: free 1,000, then $15.00 / 12.00 / 9.00 / 4.50 / 1.14
  - Route Matrix SKUs are priced identically.
  - Legacy Directions: Essentials-equivalent, $5.00 per 1,000, 10,000 free.
  - Category examples: Essentials = basic features, up to 10 waypoints; Pro = e.g. TRAFFIC_AWARE / TRAFFIC_AWARE_OPTIMAL; Enterprise = e.g. two-wheeler.
  - — [GMP pricing](https://developers.google.com/maps/billing-and-pricing/pricing); [usage & billing](https://developers.google.com/maps/documentation/routes/usage-and-billing)

**Policies / Terms (official Routes API policies page) [S]**
- "Cache or store Google Maps Content only as expressly permitted under the Google Maps Platform Service Specific Terms."
- Do not "pre-fetch, index, store, or redistribute Google Maps Content outside the Services".
- Bulk download is prohibited, explicitly including "directions, distance matrix results".
- Latitude/longitude may be cached for up to 30 consecutive calendar days. Place IDs may be stored indefinitely.
- "Don't create content based on Google Maps Content."
- Attribution: the Google Maps logo where possible, or the text "Google Maps" if space is limited; it must be visible and legible; third-party attributions must be shown when Google provides them.
- — [Routes API policies](https://developers.google.com/maps/documentation/routes/policies)
- A third-party monitor of GMP terms (not authoritative) also describes a general caching ban except where the Service Specific Terms allow it, with per-API caching tables (for example, Directions lat/lng for up to 30 days in archived versions). **[W]** — [ConductAtlas](https://conductatlas.com/platform/google-maps/google-maps-platform-terms-of-service/data-caching-and-bulk-download-restrictions/); [archived GMP Service Specific Terms index](https://cloud.google.com/maps-platform/terms/maps-service-terms/index-20240522)

**What Google's transit ETAs are based on, and how accurate they are**
- Google Research blog (Fabrikant, 2019-06-27): live bus-delay forecasts are built from real-time car traffic, bus route and stop data, location and time embeddings, and anonymized user bus trips. The feature launched **first in India**, about 3 weeks before the post.
  - The only accuracy example is one Sydney trip, "within 1.5 minutes".
  - Adding official schedules "haven't improved our forecasts significantly".
  - No aggregate accuracy figures are given.
  - **[S – vendor self-report]** — [Google Research blog](https://research.google/blog/predicting-bus-delays-with-machine-learning/)
- BusTr (Barnes et al., KDD 2020; Google) predicts bus travel times from real-time traffic. It reports a **30% MAPE improvement** over the DeepTTE baseline and serves systems lacking official real-time tracking. The abstract gives no schedule baseline or India-specific numbers. **[M]** — [arXiv 2007.00882](https://arxiv.org/abs/2007.00882)
- Delhi: in July 2021 Google Maps added real-time bus information for Delhi, in partnership with the Delhi Transport Department, DIMTS, IIIT-Delhi and Lepton. Initially about 3,000 cluster buses were covered, with DTC to follow. **[W – news]** — [Business Today](https://businesstoday.in/technology/story/google-maps-rolls-out-real-time-bus-information-for-delhi-commuters-here-is-how-it-works-301333-2021-07-14); [Business Insider India](https://www.businessinsider.in/tech/news/google-maps-adds-real-time-bus-arrival-times-for-delhi-commuters/articleshow/84408946.cms)
- Valero, Negm & El-Geneidy (2025, Findings): 7,022 workers in 12 Canadian regions, 1,545 of them transit users.
  - Google "best guess" times were queried for the same weekday and departure time as each reported commute.
  - Transit mean (Google − reported) = **−5.14 min** (−5.26 min in the quintile analysis); car −6.04; cycling −2.67; walking about 1 min and mostly not significant.
  - The authors suggest adding about 5 min to Google transit and car times.
  - Caveats: exclusions (reported >90 min, Google <5 min, |difference| >20 min) and rounding of self-reports to 5 min.
  - **[S]** — [Findings](https://findingspress.org/article/143380-exploring-the-mis-match-between-reported-and-calculated-commute-travel-times)
- Bastarianto, Hancock, Ilahi et al. (2025, Case Studies on Transport Policy 21:101508), "Mind the Gap": Jakarta travel-diary times and costs vs Google Maps API. The gaps vary systematically by mode and may bias behaviour models. The numbers were not retrievable (HTTP 403). **[M]** — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2213624X25001452); [White Rose eprint](https://eprints.whiterose.ac.uk/id/eprint/228392)

### Inferences
- **Practical setup.**
  - Enable the Routes API, not the legacy Directions API.
  - 200 OD × 5 departure times = 1,000 computeRoutes calls. That fits inside the free monthly cap of any tier, *if* transit bills as Essentials or Pro. The SKU that TRANSIT triggers is not stated on the pages read, so check the Cloud billing report after a test call.
  - Use field masks to request only the fields you need.
  - Respect 3,000 QPM. For a matrix approach, TRANSIT allows only 100 elements per request.
- **Aligning with ground truth.**
  - Past departure times only reach 7 days back, so you cannot ask Google about an old held-out week.
  - Either (a) collect fresh AVL plus Google queries for the same days and times within the last 7 days, or (b) compare Google's answer for an upcoming weekday and time to our realized-time *distribution* for that weekday and time from held-out weeks (median and P10–P90).
  - Google's past or future transit answers are presumably schedule-based or predicted, not realized. Delhi buses have had some real-time data in Google since 2021, so Google may be strong for "now" queries.
- **A strong, fair comparison.** Replay *Google's recommended itinerary* (line, boarding and alighting stops) against our realized AVL timetable to get its *realized* time and regret. Compare that with replaying our own top option. This tests route choice, not just ETA, and needs only identifiers from the Google response, not stored polylines.
- **Terms of Service risk.**
  - Keep only what the evaluation needs, for as short a time as possible, and do not redistribute raw Google responses.
  - Do not use Google outputs to fit or calibrate our model ("don't create content based on Google Maps Content").
  - Do not display Google routes on a non-Google basemap.
  - Ask the hackathon organisers whether they will supply the Google baseline themselves. That sidesteps the caching and storage questions.
  - This is not legal advice.
- Expect Google to be biased *short* by a few minutes door-to-door (Canada: about 5 min) because of walking-access, waiting and dwell assumptions. Report signed bias as well as MAE, so systematic offsets are visible.

### Gaps
- The exact SKU (Essentials, Pro or Enterprise) billed for TRANSIT computeRoutes was not stated on the fetched pages.
- The main GMP Terms of Service and the current Service Specific Terms pages could not be text-extracted. I could not confirm whether any **benchmarking or public performance-comparison clause** exists, or the exact Routes API display and caching table.
- No peer-reviewed comparison of Google transit ETAs against observed bus trips in India was found.
- No source states whether Routes API past-time transit results reflect realized delays or only schedules.

---

## 6. Crowding-aware routing: do users value it, how much time they trade, how to evaluate it

### Takeaway
Users clearly dislike crowding, but revealed-preference (RP) multipliers for buses and trams are modest: about 1.16 when all seats are full, about 1.3–1.4 for frequent riders or at 4 standees/m². Stated-preference (SP) values are higher: a bus study puts the disutility at 6 standees/m² at about 2.5× seated, and Mumbai rail crush loads reach roughly 2–4×. Our 1.0 / 1.5 / 2.3 weights sit within this envelope, with 2.3 at the SP/high-density end. With real-time crowding information:
- 50–70% of Krakow respondents would consider skipping an excessively overcrowded vehicle, typically accepting 2–13 min of extra wait.
- In a Stockholm metro pilot the share boarding the most crowded car fell by about 4 percentage points, and about 25% of passengers noticed and used the information.

Evaluation should cover both the accuracy of the crowding prediction per leg and the *trade-off quality* of recommendations.

### Cited Findings
**Valuation (time multipliers)**
- Yap, Cats & van Arem (smart-card RP; Dutch urban tram and bus): average crowding multiplier on in-vehicle time **1.16 when all seats are occupied**, **1.31 for frequent travellers**. The conference version gives **1.40 at 4 standing pax/m²**. **[M]** — [TU Delft repository (journal version)](https://repository.tudelft.nl/record/uuid:f5b0c489-e359-4095-b49d-9f3cacccb2da); [TU Delft repository (conference version)](https://repository.tudelft.nl/record/uuid:203268f5-b98d-43d6-81a7-c992fb52a24f); [World Transit Research](https://www.worldtransitresearch.info/research/7671)
- Hörcher, Graham & Anderson (2017, TR-B 95:105–125; metro, smart card + train location, RP): **standing penalty = 26.5%** of uncrowded in-vehicle-time value, plus **11.9% per additional pax/m²**. They note "stated choice methods may overestimate the user cost of crowding". **[S – abstract]** — [EconPapers](https://econpapers.repec.org/RePEc:eee:transb:v:95:y:2017:i:c:p:105-125)
- A metro RP study using smart-card transactions and train occupancy (Transport Policy 47:94–104, 2016): standing multiplier **1.18–1.24** at current AM-peak crowding, up to **1.55 at 3 standing pax/m²**. A secondary summary credits it to Sun, Erath & Chakirov. My recollection is Tirachini, Sun, Erath & Chakirov, Singapore MRT. Authors and city are not verified. **[W/M]** — [IDEAS/RePEc](https://ideas.repec.org/a/eee/trapol/v47y2016icp94-104.html)
- Batarce, Muñoz & Ortúzar (2016, TR-A 91:358–378; **bus**, SP with crowding pictures): marginal disutility of travel time at **6 standing pax/m² ≈ 2.5×** that with seats available. Ignoring crowding overestimates bus demand and the benefits of pure time savings. **[S – abstract page]** — [PUC Chile page](https://ing.uc.cl/?p=48841)
- Sahu, Sharma & Guharoy (2018, Public Transport; **Mumbai suburban rail**, SP):
  - Standing in a crowded train (7–9 standees/m²) for up to 10 min adds **0.94 min of perceived cost per minute**; for up to 20 min, **1.26**.
  - Crush loads (14–16/m²) add **2.82**.
  - Women perceive larger losses.
  - The "per minute" values look additive, i.e. multipliers of about 1.9–3.8, but this interpretation should be confirmed in the full text.
  - **[M]** — [TRID](https://trid.trb.org/View/1495556)
- Basu & Hunt (2012, TR-A 46(9)) value headway and ride time at different standee densities, Mumbai SP. Numbers not retrieved. **[M]** — [EconPapers](https://econpapers.repec.org/RePEc:eee:transa:v:46:y:2012:i:9:p:1465-1476)
- A 2023 Transportation paper reports that crowding has been valued more negatively since COVID-19. Only fragments were seen. **[W]** — [Springer PDF](https://link.springer.com/content/pdf/10.1007/s11116-023-10420-1.pdf)

**Behavioural response to crowding information**
- Drabicki et al. (2023, Krakow SP, "Should I stay or should I board?"): **50–70%** of respondents consider skipping an excessively overcrowded first departure, and **10–30%** would skip one with moderate standing crowding. Acceptable extra waits are typically **2–13 min**, sometimes over 20 min. **[M]** — [TU Delft repository](https://repository.tudelft.nl/record/uuid:6ec82017-dbd4-416e-91ba-1394c36bdd9c)
- Post-COVID follow-up: willingness to wait is now also driven by the expectation of a *seat* on the next departure. **[M]** — [TU Delft repository](https://repository.tudelft.nl/record/uuid:6763c6f1-0312-4cae-bfc5-613d8fbd3875)
- Simulation: real-time crowding information reduces overcrowding, headway deviations and denied-boarding risk in moderately saturated bus networks. **[M]** — [TU Delft repository](https://repository.tudelft.nl/record/uuid:eec538e4-021a-4753-ab1d-fee12062fe8c)
- Zhang, Jenelius & Kottenhoff (2017, Public Transport 9(3):483–499; Stockholm metro pilot; video, surveys, load measurements, control period):
  - On trains crowded on arrival, the share boarding the most crowded car fell by **4.3 pp**, and the less crowded car rose by **4.1 pp**. Statistically significant.
  - About **25%** of passengers noticed, understood and found the information useful. Many valued it even without changing behaviour.
  - **[M]** — [Springer](https://link.springer.com/article/10.1007/s12469-016-0150-y)

### Inferences
- **Sanity-check our weights.**
  - Standing 1.5 sits between RP (about 1.2–1.4) and SP mid-range values.
  - Crowded 2.3 is close to SP values at about 6 pax/m² (2.5×, bus) and below the Mumbai crush-load range (roughly 2–4×).
  - Because RP evidence suggests SP overstates crowding costs, run a **sensitivity analysis**: low set ≈ 1.0 / 1.2 / 1.6, high set ≈ 1.0 / 1.6 / 2.5. Report how often the top recommendation changes, a "rank stability" metric.
- **Evaluate crowding in three layers.**
  1. *Per-leg crowding prediction* vs held-out ticket-derived load: confusion matrix over seated / standing / crowded, quadratic-weighted kappa, ordinal MAE, and calibration of P(seat).
  2. *Recommendation trade-off*: for each OD where the crowding-weighted option differs from the fastest, report the extra minutes accepted and the crowded minutes avoided. Check the extra time against the 2–13 min acceptable-wait evidence. Report the share of ODs where the comfort option costs more than 10 extra minutes, which is probably not acceptable to many users.
  3. *Realized comfort in replay*: did the actual bus the traveller would have boarded have the predicted load class?
- Ticket data measure boardings, not on-board load. Load per segment needs boarding-and-alighting inference, for example from the destination stage on Delhi ETM tickets if it is present. Note this as a validation-design caveat.
- A user-facing claim such as "users would accept X min for a seat" should be backed by a small SP survey or an in-app A/B test. Evidence from India (Mumbai rail) suggests larger penalties, and larger ones for women, so consider segment-specific weights.

### Gaps
- No Indian *bus* crowding-valuation study (Delhi or elsewhere) was found. The Indian evidence is Mumbai suburban rail.
- No RP evidence was found on how often users actually choose a slower, less crowded *route* (as opposed to waiting for the next vehicle) when an app suggests it.
- No CHI or HCI paper with quantified uptake of crowding-aware route suggestions was retrieved.

---

## 7. Multi-criteria routing algorithms (RAPTOR, McRAPTOR, time-dependent or frequency-based) vs our heuristic search

### Takeaway
RAPTOR computes *all* Pareto-optimal journeys (arrival time × number of transfers) on a London-scale network in about **7 ms**. That is 9× faster than multi-label-correcting Dijkstra, without preprocessing, so it handles live delays. McRAPTOR adds criteria such as fare zones, and could carry a crowding-perceived cost, at about **100–260 ms**. rRAPTOR gives full departure-time profiles in about **87 ms**. Production engines (OTP2 Range Raptor; R5 with Monte Carlo for headway-based service) build on it. The benefit over our heuristic is guaranteed optimality and Pareto completeness, including ≥2 transfers and wider transfer walks. I found no published quantification of the "heuristic vs exact" quality gap for bus networks; measure it on our data.

### Cited Findings
- Delling, Pajor & Werneck, "Round-Based Public Transit Routing" (ALENEX 2012; Transportation Science 49(3):591–604, 2015).
  - Each round adds one trip (transfer), and each route is scanned at most once per round. There is no preprocessing, so it works in "fully dynamic scenarios".
  - **[S]** — [Microsoft Research PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf); [MSR page](https://www.microsoft.com/en-us/research/?p=162045)
- Benchmark (London TfL, one Tuesday in 2011): 20,843 stops; 2,225 routes; 133,011 trips; 5,132,672 departures; 45,652 footpaths; 10,000 random queries on a 2011 dual 6-core Xeon X5680. The figures below are from Tables 1–2; parallel speedups are reported separately in Table 3.
  - RAPTOR: **7.3 ms** average, 8.4 rounds, 1.9 Pareto journeys.
  - vs MLC 67.2 ms (9× slower), Layered Dijkstra 44.5 ms, Time-Dijkstra 14.2 ms (arrival time only).
  - rRAPTOR, 2-hour range: **87.0 ms**, 16.3 journeys.
  - McRAPTOR with **fare zones**: **107.4 ms**, 9.0 journeys (4.7× more journeys than plain RAPTOR), 3.7× faster than MLC (399.5 ms).
  - McRAPTOR emulating a range query: 259.8 ms.
  - All variants reach the whole network within about 5 rounds.
  - **[S]** — [Microsoft Research PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf)
- The journal version lists fare zones and **reliability of transfers** as example extra criteria. **[M]** — [IDEAS/RePEc](https://ideas.repec.org/a/inm/ortrsc/v49y2015i3p591-604.html)
- OpenTripPlanner 2:
  - Range-Raptor search window ("All optimal travels that depart within the search window is guaranteed to be found").
  - Pareto-optimal results on `time`, `number-of-transfers` and `generalized-cost`.
  - Generalized cost built from walk, wait and transfer reluctance and penalties.
  - Transfer optimization after Raptor.
  - **[S]** — [OTP RouteRequest docs](https://docs.opentripplanner.org/en/latest/RouteRequest/)
- R5 / r5r: RAPTOR extension that samples simulated schedules for frequency-based GTFS (5 draws per minute by default) and returns travel-time percentiles. **[S]** — [r5r vignette](https://cloud.r-project.org/web/packages/r5r/vignettes/time_window.html); based on Conway et al. 2017 — [TRB preprint](https://d1rbsgppyrdqq4.cloudfront.net/s3fs-public/c160/TRB_17-06602_TRR_manuscript_preprint.pdf)
- Stochastic or adaptive routing policies on temporal graphs run in near-linear time, about 0.1 s for 1-hour journeys (Zurich). **[S – abstract]** — [DROPS](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ATMOS.2019.4)
- The Berkeley planner used precomputed K-shortest feasible paths (≤3 transfers) with dynamic link times. This heuristic-with-enumeration design gave the hit rates in Q1. **[S]** — [eScholarship](https://escholarship.org/uc/item/51t364vz)

### Inferences
- Our 0.13 s per query is already interactive. Moving to RAPTOR is about **solution quality and completeness**, not speed:
  - ≥2 transfers
  - transfer walks beyond 250 m at network distance
  - exact Pareto sets over {arrival time, transfers, crowding-weighted perceived time, walking}
  - departure-time profiles (rRAPTOR) to show "leave-by" options
- A Delhi bus network is likely smaller than London's 5.1M departures, so McRAPTOR with 3–4 criteria should stay well under 1 s. Bag sizes grow with criteria, so use relaxed or ε-dominance for the crowding cost.
- Feeding observed times into RAPTOR:
  - Turn the GPS-median segment times plus observed headways into a *synthetic timetable* per time-of-day band (trip-based), **or**
  - use frequency-based RAPTOR with Monte Carlo schedule draws (R5-style), which outputs percentiles directly and matches our headway-based waits.
  - For "now" queries, overwrite the near-term departures with live positions.
- Quantify the benefit on our data. Run exact RAPTOR alongside the current heuristic on the same OD×time sample, using both the predicted and the realized (held-out AVL) timetables. Report:
  - the share of ODs where the heuristic's best option is Pareto-dominated
  - the mean and P90 time loss
  - the share where the optimum needs 2 or more transfers or a transfer walk over 250 m
  - the change in replay hit rate and regret (Q1 metrics)
- The *same exact router on the realized timetable* is also the oracle for the route-choice evaluation in Q1, so it pays twice.

### Gaps
- No published study was found that quantifies the optimality gap of heuristic transit search versus RAPTOR or McRAPTOR on real bus networks.
- No published McRAPTOR implementation with a crowding criterion and an evaluation in a developing-country bus network was found.
- Delhi network size (stops, trips) was not sourced here.
