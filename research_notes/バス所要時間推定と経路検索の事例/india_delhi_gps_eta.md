# Bus travel time / ETA prediction in India (focus: Delhi): prior work, data quality, Google Maps baseline

Research date: 2026-11-14. Context: Delhi Transport Stack Hackathon Problem 1 (bus journey planner using in-vehicle times from observed GPS speeds; evaluated against actual bus trip times and Google Maps; Phase 1 due 24 Nov 2026).
Note: about 20 tool calls. Several primary PDFs (IIT Madras APTS report, coeut slides, TRID, i-scholar review, IIIT-D repository) could not be fetched (404 or connection errors), so some accuracy figures below come from abstracts or search snippets and are flagged as such.

## Q1. What accuracy (MAE/MAPE) has been reported for bus travel time prediction in Indian cities?

### Takeaway
Published Indian results fall roughly in the 10-25% MAPE range. Kalman-filter and historic-average baselines are typically 20-40% MAPE. The only Delhi-specific deep-learning paper found (TCS Research, Route 399) gives improvements over baselines but no absolute MAPE in the extracted text. IIT Madras (Vanajakshi) work reports accuracy as "±X min within a window", and its headline absolute MAPE figures could not be retrieved.

### Cited Findings
**Delhi**
- Bhutani, Pachal, Achar (TCS Research Chennai), "Bus Arrival Time Prediction" with a GRU encoder-decoder (Seq2Seq), arXiv 2210.01655 (2022) — [arXiv](https://arxiv.org/abs/2210.01655); details from the full-text PDF ([PDF](https://arxiv.org/pdf/2210.01655v1.pdf)):
  - Data: one Delhi route (Route 399). GPS from all trips, Sept–Oct 2019. Mon–Sat only, because Sunday traffic is very different. The first 7 weeks were used for training and the last week for testing.
  - Route split into uniform **800 m sections (34 sections)**. Raw GPS "had to be filtered off the GPS noise" using **simple route projection** before computing section travel times.
  - Inputs: the current bus's traversed section times; the **closest previous bus's** section travel and entry times on the downstream sections (real-time and temporal); the **same-weekday previous-week trip** (weekly seasonality).
  - Results: the bidirectional-decoder model (EDB) beats LNKF (linear Kalman), SVKF (SVM+Kalman), DeepAR, ConvLSTM and the unidirectional ED. Its MAPE advantage is up to **14.08% / 16.41% / 4.04% / 2.5% / 4.64%**, and its MAE advantage up to **32.96 s / 55.36 s / 14.76 s / 15.08 s / 8.33 s** respectively. For 5-step-ahead prediction the MAPE improvement is up to 14.32% over LNKF; for 10-step it is up to 11.18% over LNKF. Absolute MAPE values are shown only in figures (Fig. 4–6), which were not extracted.
- Karan Dhingra (IIIT-Delhi M.Tech thesis, advisor Pravesh Biyani, 2021), "Scalable spatio-temporal arrival time estimation for public transit": proposes the SSTG spatio-temporal graph model on open Delhi GTFS/GTFS-RT data and handles cold-start stops. It uses an **MSLE-weighted loss to bias towards over-estimating ETA**, to avoid the costly underestimates. It claims to outperform existing methods. No numbers were extracted — [IIIT-D repository](https://repository.iiitd.edu.in/xmlui/handle/123456789/1094?show=full) (via search snippet; the page itself timed out).

**Chennai (IIT Madras, Lelitha Vanajakshi group)**
- Vanajakshi, Subramanian, Sivanandan (2009, IET Intelligent Transport Systems): Kalman filter with **space discretization**, predicting the next bus from the previous two buses' GPS-derived section travel times. Chennai MTC buses, heterogeneous traffic — [ISC record](https://manuscript.isc.ac/Inventory/49/1061262.htm); [TRID](https://trid.trb.org/view/848058).
- Kumar et al. (2015), "Analytical approach to identify the optimum inputs for a bus travel time prediction method": two Chennai routes, **prediction within ±5 min for a 30-min window in 92% of instances** — [WTR](https://www.worldtransitresearch.info/research/5921).
- Kumar, Dogiparthi, Vanajakshi, Subramanian (2017, *Transport* 32(4) 358–367): exponential smoothing as the state equation plus a Kalman filter. Tested on **105 trips** in Chennai, it had lower MAPE than exponential smoothing alone in **100 of 105 trips** — [Transport journal](https://tede.vgtu.lt/index.php/Transport/article/view/1115). The absolute MAPE is not in the abstract.
- Jairam, Anil Kumar, Arkatkar, Vanajakshi (2018, TRR, doi 10.1177/0361198118770175): compares k-NN classifier vs Kalman filter vs ARIMA across **Surat, Mysore, Chennai**. The abstract gives no numbers — [WTR](https://www.worldtransitresearch.info/research/7355).
- Kalman-based method on MTC **route 19B**, with 45 days of GPS: evaluated with MAPE/MAE, and Kalman beat simple averaging. No headline number in the snippet (search snippet only, no URL verified beyond the IIT Madras search results).
- Dhivyabharathi, Anil Kumar, Vanajakshi, Panda (2017, *Transportation in Developing Economies*): particle filter for bus travel time under heterogeneous Indian traffic, **~20% MAPE vs ~37% for the historic average** (from search snippet; city not confirmed) — [Springer](https://link.springer.com/article/10.1007/s40890-017-0043-z).

**Bengaluru / others**
- BMTC: no peer-reviewed BMTC MAPE paper was found. An IIIT-Bangalore student report, "BMTC Bus Timing Prediction" (Grover & Gulati), uses BMTC GPS to estimate durations between coordinates — [report PDF](https://gulu42.github.io/assets/pdf/bmtc_report.pdf). BMTC released 3 weeks of live bus location data for the "Bengaluru Last Mile Challenge 2025" — [IEEE DataPort](https://ieee-dataport.org/competitions/bengaluru-multimodal-journey-challenge-2025). The CNI-22 repo has a one-day sample of about 2,000 buses — [GitHub](https://github.com/HSShashank/CNI-22).
- Mysore ITS and Surat data appear in the Jairam et al. comparison above. Hyderabad, Pune and Ahmedabad: I found no reliable sources with accuracy numbers.

### Inferences
- Realistic targets for segment-speed-based in-vehicle time: roughly **15–20% MAPE** on whole trips is "literature-competitive". Historic-average baselines are around 30–40% MAPE in Indian conditions (single source).
- The reusable design pattern from both Delhi and Chennai work is: route-projected GPS, then fixed-length sections (~500–800 m) or stop-to-stop links, then section travel time by time slot and weekday type (Mon–Sat vs Sunday). Real-time variants add the travel time of the previous bus on the same downstream sections.
- For a journey planner, a deliberate **over-estimate bias** (as in Dhingra's MSLE weighting) may beat Google on the commuter-relevant metric, since missing a bus costs more than waiting.

### Gaps
- Absolute MAPE values for Route 399 (figures only), the Vanajakshi 2009 space-discretization model, and the Jairam 2018 cross-city comparison could not be retrieved: the full texts were paywalled or returned 404.
- No published accuracy numbers were found for Hyderabad, Pune or Ahmedabad (Janmarg BRTS) bus ETA.

## Q2. What specific data quality problems do Delhi bus GPS feeds have, and how have researchers cleaned them?

### Takeaway
The Delhi feed is nominally 10 s GPS. Documented problems are GPS noise, offline or missing units (historically almost all of DTC), non-adherence to timetables (random first-stop departures), stale static GTFS, and buses missing from the system. Researchers clean the data with route projection, 50 m stop-buffer snapping, segmentation, and discarding sparse clusters. Depot noise, duplicates and ping gaps are not explicitly documented in the sources found, so expect to handle them yourself.

### Cited Findings
- OTD real-time endpoint: `/api/realtime/VehiclePositions.pb?key=...`, which needs a registered private API key — [otd.delhi.gov.in docs](https://otd.delhi.gov.in/documentation) (via search summary). The feed is described as GPS positions "every 10 seconds" — [Moovit/Medium summary via search](https://medium.com/redact/delhi-government-launches-open-transit-data-platform-for-buses-b1ed9b80e996); [Swarajya 2026](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus).
- Jain, Kumar, Balodi, Biyani (IIIT-D, arXiv 1910.08903, 2019), a benchmark dataset — [ar5iv](https://ar5iv.arxiv.org/html/1910.08903); data at bus-data.github.io:
  - Covers **543 routes and 3,464 stops**. Dynamic data comes as protobuf. GPS is sampled **every 10 s**. Fields: date, time, lat, lon, plate number, route number, direction (up/down).
  - Cleaning: raw points **within 50 m of a stop are snapped to that stop**; 50 m was chosen because fast buses may not ping near the stop. Every third stop was sampled to reduce noise.
  - Trips are split into **15-min slots**. The paper reports "significant randomness in the starting time": **the published timetable was not followed**. Start-time clusters with fewer points than ~1/3 of days were discarded as outliers.
  - Arrival-time distribution at a stop is roughly Gaussian, and its **variance grows through the day** (Route 425).
  - Missing data, depot pings and duplicates are not discussed.
- Bhutani et al. 2022 (Delhi Route 399): raw GPS needed noise filtering via **route projection** before computing 800 m section times — [arXiv PDF](https://arxiv.org/pdf/2210.01655v1.pdf).
- Pahwa, Lakhotia, Tiwari (IIT Delhi, EASTS vol. 12, 2017), "Methodology for using GPS data from buses to assess link-based travel time variation": 1 month of raw GPS from **25 Delhi routes**. The paper discusses the "various issues" in raw GPS and a sequential method to select a processing approach for link travel time and speed. The specific issues are only in the full text — [J-STAGE](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_article/-char/en); [PDF](https://www.jstage.jst.go.jp/article/easts/12/0/12_1238/_pdf/-char/en).
- EMBARQ India (2012), Route 419 GPS: analyzed **missed stops and curtailed trips**. Early-morning trips were fastest. Because of a system limitation, the **speed field was set to 10 km/h instead of 0** — [SlideShare](https://www.slideshare.net/EMBARQNetwork/embarq-india-talking-transit-august-2012-star-bus).
- **Cluster vs DTC**: at OTD launch (Nov 2018), only DIMTS cluster buses (~1,700) fed the GTFS-RT feed. The ~3,800 DTC buses were excluded because their **GPS devices were broken or missing**. On Google Maps, cluster buses showed real-time data while DTC showed schedule only — [New America, Abisla](https://www.newamerica.org/insights/anthology-working-papers-new-americas-us-india-fellows/open-transit-data-in-india-richard-abisla/).
- A 2018 Datameet user archived the Delhi RT feed as flat CSV and suspected the data came from non-DTC operators — [Datameet thread](https://groups.google.com/g/datameet/c/exEoW8aGHu0).
- An IIT Delhi paper (Tarar, Mukherjee, Rao 2021) wrote a program that pulls OTD real-time data with an API key and converts it to GTFS form, focused on DIMTS routes — [SJSUTST 2021](https://sjsutst.polsl.pl/archives/2021/vol111/169_SJSUTST111_2021_Tarar_Mukherjee_Rao.pdf).
- Current state (Swarajya, Mar/Apr 2026): GPS units **sometimes go offline**; arrival times are "frequently inaccurate"; **routes change without static data being updated**; some registered e-buses are missing from One Delhi; informal DEVI-bus stops produce no signal. One Delhi tracks **7,300+ DTC and cluster buses**. The Delhi e-bus fleet is over 4,000 (Feb 2026) — [Swarajya](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus).
- Chartr's AVLS tracks "3,500+ DTC and DIMTS buses" and publishes GTFS-RT on Transport Stack (vendor claim) — [Chartr Transport Stack](https://chartr.in/products/transport-stack/). Biyani's 2019 talk cites 5,000+ buses from 40+ depots — [IIT Madras slides](https://rbcdsai.iitm.ac.in/images/events/Pravesh.pdf).

### Inferences (practical cleaning checklist for the hackathon)
- Snap pings to the route shape (projection distance along the polyline). Drop pings more than ~50–100 m off-route. This removes depot and yard pings and off-route detours.
- Use 50 m stop buffers, or interpolate the stop crossing time between consecutive pings (10 s at ~20 km/h is about 55 m, so interpolation matters).
- Filter by speed: implied speeds above ~70–80 km/h point to GPS jumps. Treat zero-speed runs at terminals or depots as layover, not in-vehicle time.
- Trip segmentation can't trust schedule `trip_id`s, because timetables are not followed. Derive trips from direction changes and terminal arrivals.
- Expect fleet coverage gaps and different device behaviour between DTC (historically poor or no GPS, now AVLS via Chartr) and cluster (DIMTS) buses. Check the ping rate by operator and agency.
- Detect stale or duplicate positions (same timestamp, or the same lat/lon repeated while the timestamp advances).

### Gaps
- No source quantified missing-ping rates, the actual median inter-ping interval in the current Transport Stack GTFS-RT, or depot noise. These should be measured directly from the feed (FeedHeader timestamps, per-vehicle timestamp deltas).
- No source gives current DTC vs cluster GPS quality differences after the AVLS rollout.

## Q3. Does Google Maps in Delhi use real-time bus data, scheduled GTFS, or neither? How strong is the Google Maps baseline?

### Takeaway
Google Maps has consumed the Delhi live bus feed since 2021: cluster buses first, about 3,000 buses announced in July 2021, with DTC "to follow". Before that, and for DTC buses, Google showed schedule-based, essentially constant travel times. Academic authors describe these as unrealistic for Delhi traffic. Current (2025–26) coverage and quality are unverified, so the baseline should be measured empirically.

### Cited Findings
- Bhutani et al. (2022): "Any google-map based bus travel time query (in most cities in India including Delhi) has till recently mostly returned a constant prediction irrespective of the date or time of query". These fixed times "seem to be based on some pre-fixed schedules which are almost unimplementable" in Delhi traffic — [arXiv PDF](https://arxiv.org/pdf/2210.01655v1.pdf).
- July 2021: the Delhi government and Google announced real-time tracking of **~3,000 buses** on Google Maps (arrival and departure times, delays, trip duration), with more DTC buses to be integrated later. Cluster buses launched first — [Business Insider India](https://www.businessinsider.in/tech/news/google-maps-adds-real-time-bus-arrival-times-for-delhi-commuters/articleshow/84408946.cms); [Daily Pioneer 2021](https://www.dailypioneer.com/2021/technology/google-maps-to-show-real-time-info-on-delhi-s-cluster-bus-service.html); [Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fdelhi-govt-integrating-public-transit-systems-with-google-to-reduce-wait-for-buses-gahlot-1006897.html).
- At OTD launch, Google was on the advisory committee. Both DIMTS and DTC appeared on Google Maps, cluster buses with real-time data and DTC with schedule only — [New America](https://www.newamerica.org/insights/anthology-working-papers-new-americas-us-india-fellows/open-transit-data-in-india-richard-abisla/).
- As of 2022, Google Maps was one of 50+ organisations consuming the Delhi live bus feed — [Swarajya 2026](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus).
- June 2019: Google launched bus travel-time estimates **from live traffic plus public bus schedules** in 10 Indian cities (Delhi, Bengaluru, Mumbai, Hyderabad, Pune, Lucknow, Chennai, Mysore, Coimbatore, Surat) — [Business Standard](https://www.business-standard.com/article/news-ians/google-maps-now-offers-live-train-status-bus-data-119060401048_1.html); [Inc42](https://inc42.com/buzz/google-maps-gains-support-for-live-train-status-bus-travel-timings-and-auto-fares-in-india). Google's ML method for predicting bus delays from car traffic is described at [Analytics India Mag](https://www.analyticsindiamag.com/google-maps-machine-learning-bus-delays-real-time-prediction/).
- I found no source on a direct Chartr–Google partnership. Chartr's Transport Stack page does not mention Google — [Chartr](https://chartr.in/products/transport-stack/).

### Inferences
- The Google baseline for Delhi in-vehicle time is probably one of two things. For trips with live feed coverage, it is a schedule or GTFS-RT-adjusted ETA. Otherwise, it is the 2019 approach of a car-traffic-to-bus-speed model on top of the schedule. Either way, it likely does not fully capture dwell time at crowded stops or route-specific congestion. A per-segment, time-of-day empirical speed model from 10 s GPS has a plausible edge, especially at peak hours and for DTC routes.
- Practical step: collect Google Maps Directions (transit) results for the evaluation OD pairs at multiple departure times. Check whether the duration varies with time of day; constant durations mean schedule-only. Report MAE/MAPE against observed GPS trip times for both Google and your model.

### Gaps
- No 2024–2026 source confirms whether Google Maps currently shows live positions for DTC buses, or whether it uses the Chartr / Transport Stack GTFS-RT feed.
- No published quantitative evaluation of Google Maps bus ETA accuracy in Delhi was found.

## Q4. Existing open-source code/repos and prior hackathons for Delhi bus GTFS / GTFS-RT

### Takeaway
Reusable material is thin: the IIIT-D benchmark dataset (bus-data.github.io), the static DTC GTFS mirror on Transitland/MobilityDatabase, and a few academic converters. I found no well-known maintained GitHub repo for Delhi GTFS-RT processing, and no public outputs from a "2019/2020 Delhi open transit data hackathon". The current relevant precedent is the Transport Stack Open Innovation Challenge (JICA/BCG/IIT Delhi FITT).

### Cited Findings
- IIIT-D benchmark dataset of Delhi GPS (10 s, 543 routes) at bus-data.github.io, introduced in arXiv 1910.08903 — [ar5iv](https://ar5iv.arxiv.org/html/1910.08903).
- Static DTC GTFS is mirrored in `transitland/gtfs-archives-not-hosted-elsewhere` and listed on MobilityDatabase — [MobilityDatabase mdb-1262](https://mobilitydatabase.org/feeds/gtfs/mdb-1262), [mdb-3139](https://mobilitydatabase.org/feeds/gtfs/mdb-3139). TUMI hub also lists the OTD static data — [TUMI](https://hub.tumidata.org/dataset/open_transit_data_static_delhi).
- 2018 Datameet community archive of the RT feed as CSV — [Datameet](https://groups.google.com/g/datameet/c/exEoW8aGHu0).
- Chartr: "India's first open GTFS dataset for Delhi's bus network" (DTC and DIMTS routes, stops, schedules, fares) and GTFS-RT, both downloadable from the Transport Stack Open Data Catalogue. The Multimodal Journey Planner API is approval-based. The Transport Stack Open Innovation Challenge (JICA, BCG, FITT@IIT Delhi; USD 100K grants; 5 winning startups building PoCs) lists Chartr, DIMTS and iCreate as partners — [Chartr Transport Stack](https://chartr.in/products/transport-stack/).
- Chartr, founded by Pravesh Biyani and incubated at IIIT-D, is building a Delhi Transport Stack covering all metro routes, ~2,000 bus routes and ~5,000 bus stands — [Swarajya](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus). The Chartr app powers ticketing and live tracking for DTC and cluster buses (June 2025) — [The Week](https://www.theweek.in/wire-updates/national/2025/06/15/des25-dl-iiitd-chartr-app.html).
- Biyani's IIT Madras talk (2019) lists use cases for open Delhi transit data: ETA prediction, bunching mitigation, breakdown identification — [slides](https://rbcdsai.iitm.ac.in/images/events/Pravesh.pdf).
- Other IIIT-D theses under Biyani: KPIs and timetable optimisation for Delhi buses (2024); traffic analysis through GPS data (2019) — [IIIT-D repo 1737](https://repository.iiitd.edu.in/jspui/handle/123456789/1737), [791](https://repository.iiitd.edu.in/jspui/handle/123456789/791?mode=full).

### Inferences
- For tooling, generic open-source stacks are the practical choice: `gtfs-realtime-bindings` (protobuf parsing), `partridge`/`gtfs_kit` (static GTFS), map-matching (route-shape projection with shapely, or Valhalla/OSRM), and OpenTripPlanner/r5 for the planner, with segment travel times injected. No Delhi-specific repo is mature enough to depend on.
- Delhi time-of-day corridor speeds: no published km/h table was found. The IIIT-D 10 s dataset or live Transport Stack GTFS-RT data needs to be aggregated by segment × 15-min slot × weekday/Sunday.

### Gaps
- I found no record of a 2019/2020 Delhi open transit data hackathon or its outputs, and the delhi.transportstack.in hackathon page was not checked in this pass.
- No published quantitative Delhi bus speed profile by corridor and time of day. The CSE report has speed-by-time-of-day figures for Delhi traffic generally, but the values were not retrieved — [CSE](https://cseindia.org/content/downloadreports/12612).
- Pahwa et al. (2017) full text, which likely has the most detailed Delhi GPS cleaning issues, was not read.
