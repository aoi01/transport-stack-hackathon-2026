# Delhi transit-side open data for travel/waiting/journey-time prediction (status as of 17 Nov 2026)

Legend: [V] = page opened and read in this session (17 Nov 2026); [S] = known only from a search-result snippet or a secondary source; [I] = my inference.
Error components: IVT = in-vehicle time, WAIT = waiting time, XFER = transfer time, J = full journey.

## 1. Delhi Open Transit Data (otd.delhi.gov.in): feeds, archives, metro GTFS, coverage

### Takeaway
OTD documents only one realtime feed, **GTFS-RT VehiclePositions** (key required). It documents no TripUpdates or ServiceAlerts and no official historical archive. So OTD cannot provide October 2026 realtime history. The team's own recording since 15 Nov 2026 is the only VehiclePositions history after that date. OTD also hosts a separate DMRC metro static GTFS dated Aug 2023, useful for bus-metro transfers.

### Cited Findings
- [V] OTD portal sections: Static Data (`/data/static`), DMRC Static Data (`/data/staticDMRC`), Real Time Data (`/data/realtime`), Documentation. Access to the realtime data requires an API key, requested with a form (name, email, phone, institution, Commercial/Non-Commercial use, purpose including "Research"/"Student Projects", agreement to T&C). Footer reads "© 2017-2023". — [OTD realtime](https://otd.delhi.gov.in/data/realtime/)
- [V] Documented realtime endpoint: `/api/realtime/VehiclePositions.pb?key=YOUR_PRIVATE_KEY`. Only VehiclePositions is mentioned. **TripUpdates and Alerts are not referenced.** The page does not state update frequency, rate limits or historical availability. — [OTD documentation](https://otd.delhi.gov.in/documentation)
- [V] OTD documentation warns that `stop_times.txt` arrival/departure times are inaccurate, "roughly estimated by assuming constant travel speed". — [OTD documentation](https://otd.delhi.gov.in/documentation)
- [V] Bus static page: Stops 3464, Routes 543, Stop Times 378,324, Trips 16,562, all last updated **20 June 2024**. The page shows no version number and no licence name, only a link to the T&C at `/terms`. The agency file is served from `traffickarma.iiitd.edu.in:9010`. — [OTD static](https://otd.delhi.gov.in/data/static/)
- [V] DMRC static page: Stops 262 (metro stations), Routes 36, Stop Times 411,686, Trips 17,997, all last updated **10 Aug 2023**. The data downloads as a zip, and submitting the download form implies agreeing to the T&C. — [OTD DMRC static](https://otd.delhi.gov.in/data/staticDMRC/)
- [V] T&C is a PDF titled "OTD - Terms & Conditions_FINAL", created Nov 2018. Its text could not be extracted (the PDF appears image or compressed-stream only), so the licence terms are **unverified**. — [OTD terms PDF](https://otd.delhi.gov.in/terms)
- [V] Mobility Database lists the IIIT-D OTD licence as `https://opendata.iiitd.edu.in/terms` for the Delhi bus GTFS. — [MobilityDatabase mdb-1262](https://mobilitydatabase.org/feeds/gtfs/mdb-1262)
- [S] Earlier IIIT-D/OTD materials said real-time data for DTC buses would be added "when a new GPS vendor is in place". In other words, the OTD realtime feed historically covered cluster (DIMTS) buses first. A 2019 datameet post likewise suspected the feed covered "other bus services" rather than DTC. — [datameet thread](https://groups.google.com/g/datameet/c/exEoW8aGHu0); [Medium launch article](https://medium.com/redact/delhi-government-launches-open-transit-data-platform-for-buses-b1ed9b80e996)
- [V] **Historical archive (old):** Nikhil VJ archived the Delhi OTD GTFS-RT feed for 2019–2020 ("mostly 2019") as weekly 7z/zip CSVs of bus GPS points. Hosted at https://server.nikhilvj.co.in/delhirt/ with the note "Please feel free to use it as you may"; no formal licence and no stated size. Posted to datameet in Feb 2024. — [datameet post](https://groups.google.com/g/datameet/c/I3FPPsIWrl8/m/MPpeJw5HAQAJ)
- [S] The OTD feed is polled about every 30 s, the GTFS-RT minimum refresh. — [datameet thread (search snippet)](https://groups.google.com/g/datameet/c/I3FPPsIWrl8/m/3YBfnMA2FgAJ)

### Inferences
- [I] October 2026 realtime history is **not** publicly available from OTD. For Oct 2026 the team's own DTC/cluster GPS (11 s) remains the only source. The 2019–20 archive is too old for operations (pre-DEVI, pre-route rationalisation), but it can serve as a long-run prior on headway-irregularity patterns by hour and day of week if the routes are matched.
- [I] With no TripUpdates or Alerts, the team must **infer cancellations themselves**: a scheduled GTFS trip with no matching VehiclePositions `trip_id`/vehicle within ±X min means a cancelled or missing trip. This is the main lever for WAIT error. They can build an empirical per-route-hour "trip operated probability" and "headway CV" from the Oct 2026 GPS and apply it to the realtime week.
- [I] Because OTD `stop_times` are constant-speed estimates, replacing scheduled times with **GPS-derived stop-to-stop running times** (route × segment × hour × daytype) should reduce IVT error. The team likely already does this with the Oct GPS.
- [I] DMRC static GTFS (Aug 2023) lacks recent lines and extensions (e.g. Phase-4 sections opened 2024–26). Its trips/frequency can approximate metro headways for XFER, but the station list must be checked against current operations.
- [I] Redistribution: with the T&C unreadable here, the safe stance is to commit only derived aggregates (e.g. per-route headway stats) and scripts that download raw OTD files, not the raw OTD files themselves, until the team reads `/terms`.

### Gaps
- OTD T&C content (redistribution, attribution, commercial/non-commercial) could not be extracted; the team should read the PDF manually.
- I could not confirm whether the current OTD realtime feed covers DTC, cluster or both in Nov 2026. The team can check this from its own recordings, e.g. by vehicle_id prefixes and agency in route_ids.
- No evidence of any OTD TripUpdates or ServiceAlerts endpoint (absence on the docs page ≠ proof of absence).
- The "v32" GTFS the team holds does not match any version label visible on OTD (OTD shows no version). It probably comes from the Transport Stack catalogue (unverified).

## 2. Delhi Transport Stack catalogue, Chartr, Mobility Database and other catalogues (IUDX, data.gov.in, TUMI)

### Takeaway
The Delhi Transport Stack Open Data Catalogue lists Chartr's Delhi bus GTFS static and GTFS-RT feeds (DTC + DIMTS, 3,500+ buses) plus an approval-based multimodal journey-planner API. No metro, rapid-rail, alerts or cancellation datasets were found listed there. Mobility Database only mirrors an old (2022–2024 service range) Delhi bus GTFS and lists no Delhi GTFS-RT. I found no IUDX or data.gov.in Delhi transit operations dataset.

### Cited Findings
- [V] Chartr's Transport Stack page lists three items: "Delhi Buses: Open GTFS Feed" (static: routes, stops, schedules and fares for DTC and DIMTS), "Delhi Buses: GTFS-RT Live Feed" (real-time positions for 3,500+ buses), and a "Multimodal Journey Planner (Bus, Metro, Rapid Rail, last-mile)" API that is approval-based. The page states no licence and no endpoints. — [Chartr Transport Stack](https://chartr.in/products/transport-stack/)
- [V] `delhi.transportstack.in` returned only its title "Delhi Transport Stack" to the fetcher (it is a JS app), so its catalogue entries could not be enumerated. — [Delhi Transport Stack](https://delhi.transportstack.in/)
- [V] Mobility Database mdb-1262 (Delhi Transport Corporation, community feed): the producer URL is the Transitland "gtfs-archives-not-hosted-elsewhere/delhi-bus.zip"; the service range is 1 Jan 2022 – 1 Jan 2024; an older dataset covers 1–8 Nov 2018; the licence link is opendata.iiitd.edu.in/terms; **no related GTFS-RT feeds**. — [MDB 1262](https://mobilitydatabase.org/feeds/gtfs/mdb-1262)
- [V] Mobility Database mdb-3139 is the same Delhi bus feed (2,964 routes, same 2022–2024 range). Its latest snapshot is dated 11 May 2026, it shows 1 validation error, and it lists no GTFS-RT. — [MDB 3139](https://mobilitydatabase.org/feeds/gtfs/mdb-3139)
- [S] The TUMI data hub mirrors "Open Transit Data (Static)" Delhi with the licence field "No License Provided"; last update Apr 2023. — [TUMI hub](https://hub.tumidata.org/dataset/open_transit_data_static_delhi)
- [S] TUMI also hosts a "Delhi Metro Stations Data" dataset (station list). — [TUMI Delhi Metro stations](https://hub.tumidata.org/dataset/delhi_metro_stations_data_delhi)
- [S] A datameet reply notes that IUDX does not follow the GTFS standard; its data would need conversion. I found no specific IUDX Delhi bus resource. — [datameet GTFS India thread](https://groups.google.com/g/datameet/c/YzcQWcNDlV0/m/U34mwydKAAAJ)
- [S] An unofficial Codeberg repo, "india-transit-data", collects static feeds including Delhi Metro (DMRC). — [codeberg india-transit-data](https://codeberg.org/eternaltyro/india-transit-data)
- [S] OpenCity hosts "Delhi DTC Bus Operational Data 2018 to 2022", taken from the Delhi Economic Survey 2023. The fetch returned HTTP 403, so its fields are unverified. — [OpenCity DTC operational data](https://data.opencity.in/dataset/delhi-economic-survey-2023/resource/delhi-dtc-bus-operational-data-2018-to-2022)
- [S] arXiv 1910.08903, "Benchmark Dataset for Timetable Optimization of Bus Routes in the City of New Delhi", is an academic dataset built on 2019 OTD data. — [arXiv 1910.08903](https://ar5iv.arxiv.org/html/1910.08903)

### Inferences
- [I] The Mobility Database and Transitland snapshots are useful only for diffing route and stop changes over time, not for 2026 operations. The team's GTFS v32 is more current.
- [I] The Chartr/Transport Stack journey-planner API (approval-based) could give metro and rapid-rail legs and transfer walking for J/XFER benchmarking. Getting access requires an application, which the team did not want from me.
- [I] Annual operational aggregates (Economic Survey / OpenCity: fleet held vs on-road, km operated, breakdowns) can give **route-agnostic priors** for trip-operated rates, but only at year/agency level. Their value for WAIT is low compared with GPS-derived cancellation rates.

### Gaps
- Could not list delhi.transportstack.in entries (JS-rendered); the team should check it manually for any TripUpdates, alerts, metro or depot datasets.
- data.gov.in: I found no Delhi bus stop or route operations dataset in search results; I did not browse data.gov.in directly.
- IUDX Delhi: unconfirmed.

## 3. DMRC metro and NCRTC Namo Bharat data for transfers

### Takeaway
The only open metro schedule is the OTD DMRC static GTFS (Aug 2023). I found no public DMRC GTFS-RT. I found no open GTFS or GTFS-RT for NCRTC Namo Bharat.

### Cited Findings
- [V] DMRC static on OTD: 262 stations, 36 routes, 17,997 trips, 411,686 stop_times; updated 10 Aug 2023. — [OTD DMRC static](https://otd.delhi.gov.in/data/staticDMRC/)
- [S] Swarajya notes that DMRC has long had reliable real-time arrival information, but no public feed for it was found. — [Swarajya ground report](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus)
- [S] The NCRTC search returned only corporate material (82-km Delhi–Ghaziabad–Meerut corridor, Namo Bharat Connect app); **no GTFS or open-data mention**. — [NCRTC corporate folder](https://ncrtc.in/wp-content/uploads/2026/04/Corporate-Folder.pdf)
- [S] DMRC and IIIT-Delhi signed an MoU on technology collaboration; data release terms unknown. — [PSU Connect](https://www.psuconnect.in/memorandum-of-understanding/delhi-metro-and-iiit-delhi-join-hands)

### Inferences
- [I] For XFER, use the DMRC GTFS `frequencies`/trips to derive the expected metro wait (≈ half the headway by line and hour). Bus-to-metro walking time can be derived from stop-to-station distances (OTD bus stops × DMRC stations). Lines and stations added after Aug 2023 must be patched manually from OSM or DMRC announcements.
- [I] Namo Bharat legs can only be modelled from published headways (news or NCRTC website), not from a feed.

### Gaps
- No verified DMRC GTFS newer than Aug 2023; no DMRC or NCRTC realtime feed found.

## 4. Fleet deployment, schedules, cancellations, route rationalisation (2024–2026)

### Takeaway
DTC publishes **route-wise timetables as PDFs** (Oct 2025, Dec 2025, Jan 2026 DEVI and all-DTC). These are the only public "planned trips" source besides GTFS and could be parsed to check GTFS trip counts per route. 2025–26 news documents large route rationalisation and the CNG-to-electric (DEVI) fleet transition, both of which change headways. I found no public trip-level cancellation or schedule-adherence data.

### Cited Findings
- [S] DTC services page lists "Current D.T.C. Time Table-Jan-2026", a DEVI timetable for Jan 2026, and Nov 2025 night, NCR, airport and ladies-special timetables. — [DTC services](https://dtc.delhi.gov.in/dtc/services)
- [S] Timetable PDFs: [all DTC Oct 2025](https://dtc.delhi.gov.in/sites/default/files/2025-10/dtc_all_time_table_oct_2025.pdf), [DEVI Oct 2025](https://dtc.delhi.gov.in/sites/default/files/2025-10/all_dtc_devi_bus_time_table_oct_2025.pdf), [all DTC Dec 2025](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_dec_2025_0.pdf), [DEVI Jan 2026](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_devi_time_table_jan_2026_0.pdf), [night services Feb 2024](https://dtc.delhi.gov.in/sites/default/files/2025-02/time_table_of_dtc_night_bus_services-feb-2024.pdf). Not downloaded; sizes unknown.
- [S] DTC "induction plan of buses in Delhi" PDF (fleet induction schedule). — [DTC induction plan](https://dtc.delhi.gov.in/sites/default/files/DTC/induction_plan_of_buses_in_delhi.pdf)
- [S] 28 Sep 2025: CM Rekha Gupta flagged off 300 new DTC electric buses with rationalised routes. The DEVI fleet is to reach 974 buses, and the new services cover 21 fresh routes and 625 stops, focused on Yamunapar. — [ThePrint](https://theprint.in/india/rekha-gupta-flags-off-300-new-public-buses/2753130); [Swarajya](https://swarajyamag.com/news-brief/delhi-cm-flags-300-new-electric-buses-unveils-first-route-rationalisation-plan)
- [S] East Delhi pilot: DTC and DIMTS reviewed 121 routes for 12 m buses; up to 50% of DEVI deployment could go to selected 12 m routes as CNG buses are phased out; "at least one bus on each route" was to be kept despite reduced fleet. — [ThePrint pilot](https://theprint.in/india/dtcs-pilot-project-of-route-rationalisation-for-cng-buses-completed/2790170)
- [S] Nov 2025: 692 CNG buses were to go off road by year end after route rationalisation. — [Business Standard](https://www.business-standard.com/india-news/692-cng-buses-to-go-off-road-by-year-end-after-route-rationalisation-dtc-125112200598_1.html); [Pioneer](https://dailypioneer.com/delhi/692-cng-buses-to-go-off-road-by-year-end-dtc)
- [S] Dec 2025: targeted route rationalisation; new routes 192A and 212A; 18 routes rationalised to extend services. — [Pioneer Dec 2025](https://www.dailypioneer.com/2025/state-editions/govt-initiates-targeted-route-rationalisation.html); [Pioneer 18 routes](https://www.dailypioneer.com/2025/state-editions/dtc-rationalises-18-bus-routes-to-extend-services-to-uncovered-areas.html)
- [S] The transport minister directed DTC to stop two or three buses of the same route running together (bunching) and to revise timings. — [Lokmat Times](https://www.lokmattimes.com/national/delhi-transport-minister-aims-to-streamline-dtc-bus-service-focus-on-punctuality/amp)
- [S] West Delhi route rationalisation was announced in a separate rollout. — [Lokmat Times West Delhi](https://www.lokmattimes.com/national/dtc-route-rationalisation-in-west-delhi-to-kick-in-tomorrow-transport-minister/amp/)

### Inferences
- [I] **WAIT:** For each route, compare (a) GTFS v32 trips/hour, (b) DTC timetable PDF departures, and (c) observed GPS departures in Oct 2026. The ratio c/a gives a route-hour "service delivery ratio". Using effective headway = scheduled headway / delivery ratio, plus headway CV from GPS, in E[wait] = H/2·(1+CV²) directly targets the irregular-headway and cancellation error.
- [I] **Regime shifts:** Route rationalisation dates (Sep 2025, Dec 2025, and possibly further in 2026) mean GTFS route IDs and patterns may differ between Oct 2026 and the Nov 2026 held-out week if changes happened in between. The team should check route-ID overlap between the two weeks.
- [I] Fleet age and type (CNG vs DEVI 9 m e-bus) likely differ in speed and dwell; a vehicle-type feature (from vehicle_id or registration patterns) may reduce IVT error.

### Gaps
- No public trip-level cancellation, schedule-adherence, depot-wise daily trips or DIMTS cluster performance reports were found for 2026.
- No 2026 route-change list after Jan 2026 was verified.
- Bus lanes, bus-priority corridors and BRT status were not researched in depth within the tool budget. The Delhi BRT was dismantled in 2016 (from background knowledge, unverified here). I found no open bus-lane GIS dataset.
- Bus shelter or stop-accuracy datasets: only OTD stops (3,464, Jun 2024) and the OSM Delhi bus import plan were seen. — [OSM Delhi/Buses](https://wiki.openstreetmap.org/wiki/Delhi/Buses)
