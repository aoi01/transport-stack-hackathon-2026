# Delhi bus operations and ticketing facts (2024–2026) for travel-time, waiting-time and crowding models

Notes on sources. ES 2025-26 is the *Economic Survey of Delhi 2025-26* (Planning Department, released March 2026). It is the main primary source here, and the tables were read from its PDF text. Items marked "(search summary)" come from a search-engine summary of the page, because the page itself could not be fetched (HTTP 403/402 or binary). Treat them as lower confidence. Items marked "(local data check)" are counts the researcher computed from the hackathon files in this repo. They are not published facts, but they fill gaps where no web source exists.

## 1. Fleet composition 2025–2026 (types, DTC vs cluster/DoT, capacities, registration prefixes, route assignment)

### Takeaway
In March 2026 the city fleet was 6,100 buses: 1,002 non-AC low-floor CNG, 760 AC low-floor CNG, 2,750 electric 12 m and 1,588 electric 9 m. By mid-October 2026 it had grown to about 6,988 buses, of which 5,238 were electric and about 1,750 CNG. DTC retired almost all of its own CNG buses during FY2025-26, so the remaining CNG fleet is essentially the ex-cluster (DoT/DIMTS) fleet. DIMTS was abolished after 31 March 2026 and its operations moved under DTC. No published source maps registration prefixes to bus types. The local data check below gives a usable empirical mapping.

### Cited Findings
**Fleet totals and type split**
- In March 2026, DTC plus the Department of Transport (DoT) had 6,100 buses: 1,002 non-AC low-floor (CNG), 760 AC low-floor (CNG), 2,750 AC low-floor electric 12 m and 1,588 AC low-floor electric 9 m. — [ES 2025-26, §3.2 DTC](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- E-bus count over time (ES Statement 12.8(A)): Apr-2021: 2; Apr-2022: 2; Apr-2023: 400; Apr-2024: 1,686; Apr-2025: 2,150; Mar-2026: 4,338. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf); the 2,150 → 4,338 rise is also reported by [The Wire](https://m.thewire.in/article/economy/service-sector-transport-water-highlights-of-delhis-economic-survey-2025-26)
- DTC's own fleet at 20 March 2026 (ES Statement 12.8) was 2,674 buses: 2 non-AC CNG, 10 AC CNG, 1,800 electric 12 m and 862 electric 9 m. A year earlier (FY2024-25) it was 3,819: 1,185 non-AC, 909 AC CNG and 1,725 electric 12 m. DTC says it "has inducted 2662 Electric Buses", all pre-fitted with ITS (IP CCTV, panic buttons, GPS). — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Average buses on road per day in FY2025-26 (to 20 March): 239 non-AC CNG, 259 AC CNG, 1,670 E-12 m and 447 E-9 m, for a total of 2,615. DTC fleet utilisation was 81.39%. — [ES 2025-26, Statements 12.7–12.8](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Cluster fleet (ES Statement 12.9): 2,910 (2019-20), 3,191 (2020-21), 3,310 (2021-22), 3,293 (2022-23), 3,147 (2023-24) and 3,147 (2024-25). Fleet utilisation was 97.24% in 2024-25. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- 20 April 2026: DTC ran about 6,300 buses, 4,538 electric and 1,759 CNG. A 200-bus flag-off included 140 buses for DEVi feeder service. Buses of 7 m, 9 m and 12 m have been inducted: 9 m first on DEVi, with 7 m added later for narrow streets. Suppliers are PMI and JBM (small buses), JBM Ecolife 12 m and Switch EiV12 12 m. The target was 7,000 e-buses by end-2026 and 14,000 by 2028-29. — [electrive, 20 Apr 2026](https://www.electrive.com/2026/04/20/india-delhi-transport-corporation-flags-off-200-electric-buses/)
- 14 October 2026: 150 more e-buses took the electric fleet to 5,238, out of a total fleet of about 6,988 that includes 1,750 CNG buses. The planned fleet is nearly 14,000 by FY2028-29. — [Asia News Network, 14 Oct 2026](https://asianews.network/?p=307871)
- July 2026: e-fleet of 4,845, with a target of 7,500 vehicles by March 2027, 5,800 of them electric (search summary). — [electrive, 9 Jul 2026](https://www.electrive.com/2026/07/09/india-delhi-adds-300-electric-buses-to-its-public-transport-fleet/)
- Older figures, now superseded: 7,683 buses (5,713 CNG + 1,970 electric) per a 2024 Tribune report quoted on Wikipedia (search summary) — [Wikipedia DTC](https://en.wikipedia.org/wiki/Delhi_Transport_Corporation). FY2024-25 combined fleet was 6,966 (DTC 3,819 + cluster 3,147). — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Planned additions: 1,610 buses (including 50 metro feeders) by 2026-27. Under PM E-DRIVE, 2,800 e-buses were demanded (1,380 for DTC, 1,420 for DoT) and a further 3,330 requested. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)

**Cluster/DIMTS wind-down and CNG retirements**
- The government proposed abolishing DIMTS after 31 March 2026, with its buses run by DTC from then. In February 2026 about 5,000 cluster staff struck across five depots (Ghazipur, Kair, Sewa Nagar, Rajghat, Dwarka), and about 2,500 buses were off the road. — [ETV Bharat, 14 Feb 2026](https://www.etvbharat.com/en/bharat/i-thought-this-was-a-permanent-job-where-will-i-go-now-delhi-bus-conductors-on-strike-as-govt-terminates-dimts-enn26021401631)
- Earlier cluster withdrawals (search summaries):
  - 550+ cluster buses withdrawn when permits lapsed on 15 July 2025 — [Millennium Post](https://www.millenniumpost.in/delhi/delhi-withdraws-550-cluster-buses-without-any-replacement-plan-619456)
  - 462 cluster buses stopped by April 2025 — [ETV Bharat, Apr 2025](https://www.etvbharat.com/en/!bharat/462-cluster-buses-removed-only-7000-buses-running-for-40-lakh-delhi-commuters-enn25042904069)
  - Reported plan to retire 2,624 DTC CNG buses by February 2026 — [The Patriot](https://thepatriot.in/reports/dtc-set-to-retire-2624-cng-buses-by-feb-26-sources-62021)
- The cluster scheme started in 2011-12 on a gross-cost (OPEX) model, initially with 657 routes in 17 clusters. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)

**Capacities**
- DEVI 9 m AC mini e-bus: 23 seats plus 13 standing. Routes are at most 12 km one-way. The first 250+ buses were due to launch on 22 April 2025 from Ghazipur, Nangloi and East Vinod Nagar depots (up to 100 buses per depot). — [IANS via SocialNews, 21 Apr 2025](https://www.socialnews.xyz/2025/04/21/delhi-govt-to-launch-250-mini-electric-mohalla-buses-named-devi-tomorrow/). One outlet reported that launch as postponed (search summary) — [ACKO Drive](https://ackodrive.com/news/launch-of-delhi-s-electric-bus-service-under-devi-scheme-postponed/)
- About 27 June 2025: 100+ DEVI buses were flagged off and a new 75-bus Narela depot opened, serving 9 routes (Old Delhi Rly Stn, Mori Gate, Delhi Secretariat, Uttam Nagar, border areas). — [Tribune, 28 Jun 2025](https://www.tribuneindia.com/news/delhi/rekha-flags-off-over-100-devi-electric-buses-inaugurates-narela-bus-depot)
- Switch EiV12 12 m low-floor e-bus: up to 39 seated plus 24 standing, 63 in total depending on layout. Delhi's order is 950 units for DoT under the CESL tender (search summary). — [Autocar Pro](https://www.autocarpro.in/news/switch-mobility-delivers-first-batch-of-eiv12-electric-buses-to-delhi-transport-department-128276?amp=1); [Bus-News](https://bus-news.com/switch-mobility-flags-off-order-of-950-switch-eiv12-buses-for-delhi/)
- Tata 12 m low-floor AC e-buses: 1,500 units on a 12-year lease. The page gives no seat count. — [91trucks, 2025](https://www.91trucks.com/news/dtc-buses-2025-complete-list-of-brands-and-models-on-delhi-roads)
- Women's reserved seats are 25%, which is 10 seats in low-floor buses and 12 in standard-floor buses. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- "Over 940 buses deployed out of 2,080 buses are DEVi buses" (ICCT, undated; search summary only). — [ICCT](https://theicct.org/?p=90828)

**Bus colours (secondary source)**
- Red = AC, green = non-AC, orange = cluster (mostly non-AC). Most electric buses are AC. — [BusPe guide, updated 9 Nov 2026](https://buspe.app/guides/delhi-bus-fares-passes)

**Registration prefixes (local data check; no published source found)**
- GPS on 15 Oct 2026 shows 6,093 distinct vehicle_ids: DL1PD 4,145; DL51EV 1,180; DL51GD 659; DL1PE 109. — (local data check) [interim GPS 2026-10-15](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/interim/bus_gps/date=2026-10-15/part.parquet)
- ONDC tickets for October 2026, broken down by vehicle_number prefix and number block (local data check, [October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv)):

  | Prefix / number block | Vehicles | `is_ac` share | Mean fare |
  |---|---:|---:|---:|
  | DL1PD 4xxx | 760 | 0.00 | ₹9.2 |
  | DL1PD 5xxx | 898 | 0.55 | ₹12.6 |
  | DL1PD 6xxx–9xxx | 3,004 | 1.00 | ₹13.9–14.9 |
  | DL1PE | 240 | 1.00 | ₹15.0 |
  | DL51EV | 1,214 | 1.00 | ₹14.6 |
  | DL51GD | 693 | 1.00 | ₹14.9 |

- Every prefix runs on both "DTC" and "DIMTS" route_ids in the static GTFS (feed v32), so route_id does not identify the bus type. — (local data check) [gtfs_static](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/gtfs_static/routes.txt)
- I found no published source that explains the DL1PD, DL1PE, DL51EV or DL51GD series. Web searches for these strings returned nothing relevant.

### Inferences
- **Who owns what.** Subtracting DTC's own fleet from the ES 6,100 total leaves about 3,426 DoT/ex-cluster buses in March 2026: about 1,750 CNG (1,000 non-AC + 750 AC), 950 E-12 m and about 726 E-9 m. The 950 E-12 m matches the Switch EiV12 DoT order, and the roughly 1,750 CNG matches the 1,750–1,759 CNG reported in April and October 2026. So, after DTC's own CNG was retired, **essentially every CNG bus still running in October 2026 is an ex-cluster bus.**
- **Likely prefix mapping (unverified).**
  - DL1PD 4xxx: non-AC CNG.
  - DL1PD 5xxx: mixed non-AC and AC CNG.
  - DL1PD 6xxx–9xxx plus DL1PE: AC, mostly 12 m electric.
  - DL51EV and DL51GD: AC, all-new series, probably e-buses including the 9 m/7 m DEVI.

  Rationale: DL1PD 4xxx–5xxx come to about 1,658 vehicles, close to the 1,750 CNG fleet. DL1PD 6xxx–9xxx come to about 3,004, close to 12 m e-bus totals. DL51EV + DL51GD come to about 1,839, near the 9 m total plus 2026 DEVI additions. However, DL51 vehicles' daily movement extent (median bounding box about 26 km) is no shorter than DL1PD's, so "DL51 = short DEVI feeders" is **not** confirmed. Verify with DTC/Vahan before using it for capacity.
- **Planning capacities.** With only the sources above, a defensible set is:
  - 9 m DEVI: 36 rated (23+13).
  - 12 m e-bus: about 63 rated (39+24, Switch EiV12).
  - 12 m CNG low-floor: about 40 seats (inferred from 10 reserved seats being 25%). No standing figure was found.

  Crush loads in Delhi exceed rated standing capacity. Treat rated capacity as a "100% load" anchor, not a maximum.

### Gaps
- No official table maps registration series (DL1PC, DL1PD, DL1PE, DL51EV, DL51GD) to model, length, AC or operator. Vahan lookups or a DTC fleet list are needed.
- No seating or standing figures were found for the Tata 12 m e-bus, JBM Ecolife 12 m, the 7 m DEVI, or the legacy Tata/Ashok Leyland CNG low-floor buses.
- No official route-by-type list exists. Only DEVI depots and some route areas are documented.
- The exact October 2026 type split is not published. Sources give only an e-bus total of 5,238 and about 1,750 CNG.

## 2. Operations: UP/DOWN pairing, layover, headways, bunching, adherence, depots/shifts, night service

### Takeaway
DTC's published timetable (January 2026) shows each bus alternating between the two terminals (UP then DOWN), on fixed and often long headways. The median route has only about 20 departures a day across both directions. There is a pronounced mid-day trough consistent with two crew shifts. The night service is small: 86 buses on 27 routes, 23:00–05:00. No official norms for layover/recovery time or on-time performance were found. Evidence on bunching is limited to a 2026 hobby analysis (1 in 8 same-route gaps under 2 minutes) and a DIMTS route case study.

### Cited Findings
- DTC published timetable, January 2026. Counts are the researcher's regex parse of pdftotext output, so approximate.
  - About 395 route timetable blocks, including STL and branch variants, with about 16,641 scheduled departures per day.
  - Departures per route block per day, both directions: median 20, mean 42, 90th percentile 108. 30% of blocks have 10 or fewer departures a day; 51% have 20 or fewer.
  - Departures by hour: 05h 438; 07h 1,039; 08h 1,145 (morning peak); 12h 817; 13h 697; 14h 667 (trough); 16h 1,146; 17h 1,123 (evening peak); 21h 714; 22h 455; 23h 147. Some departures fall 00–04h (41–95 per hour).

  — [DTC all timetable Jan 2026 (PDF)](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_jan_2026.pdf)
- **Route 8 (Badarpur Border ↔ Noida Ph-II), same PDF.**
  - Ten buses run at a 20-minute headway.
  - Badarpur departures: 05:20–08:20, 08:40–11:40, 14:00–17:00, 17:20–20:20.
  - Noida departures: 07:00–10:00, 10:40–13:40, 15:40–18:40, 19:20–22:20.
  - The interleaving implies each bus alternates Badarpur→Noida→Badarpur. Departure-to-departure time at opposite terminals is 100 min (AM) or 120 min (late morning and evening), covering one-way running plus layover.
  - Within a timetable column, the last morning Noida departure (10:40) and the first afternoon Badarpur departure (14:00) are 3 h 20 min apart. That is about 1.5 h more than a normal 100–120 min half-cycle, i.e., a mid-day break or shift change.
  - Route 3 (Sarai Kale Khan ↔ Shalimar Bagh) has only 4 departures per direction per day.

  — [DTC timetable Jan 2026](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_jan_2026.pdf)
- FY2025-26 DTC (to 20 March 2026): about 32,525 trips a day on about 517 city routes plus 15 NCR routes. Coverage is 5.01 lakh km/day, a vehicle utilisation of 191 km/bus/day. DTC has 24 depots and DoT has 22 (February 2026), plus 16 bus terminals. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Cluster in 2024-25: 195.31 km/bus/day at 97.24% fleet utilisation. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Km per bus on road per day by type, FY2025-26 (DTC): E-12 m 3.42 lakh km / 1,670 buses ≈ 205; E-9 m 0.78 / 447 ≈ 174; AC CNG 0.44 / 259 ≈ 170; non-AC 0.37 / 239 ≈ 155. — derived from [ES 2025-26 Statement 12.8](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Night service (23:00–05:00): 86 buses on 27 routes (2025-26, to 28 February 2026), against 88 buses on 27 routes in 2020-21 to 2024-25. Thirty Ladies Special buses run in peak hours on 30 routes. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- 2,983 bus marshals (Home Guards) were deployed in DTC and "FCMS" buses on 28 February 2026. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- About 70 buses break down daily, per traffic police (2025). — [91trucks](https://www.91trucks.com/news/dtc-buses-2025-complete-list-of-brands-and-models-on-delhi-roads)
- Bunching, speeds and timetable assumptions from six hours of OTD GPS (6,000+ buses, 18:23 IST on 21 October 2026 to 00:23 on 22 October 2026). This is a non-peer-reviewed GitHub project.
  - One in eight same-route gaps is under 2 minutes.
  - Median speed is 8.6 km/h at 18–19h, rising to 25 km/h after 23h. At peak, 45% of road-grid cells are below 15 km/h.
  - The 2023 timetable assumes a flat 15 km/h.

  — [how-Delhi-buses-move](https://github.com/rishabhjain9196/how-Delhi-buses-move)
- Case study of bunching on DIMTS route 78 DOWN: bunching "black spots" identified. Slack times plus dispatch regulation reduced bunching in simulation (search summary). — [Springer chapter](https://link.springer.com/chapter/10.1007/978-981-16-9925-2_6)
- An older CSE report (search summary; about 8–9 years old) found fewer than 25% of DTC routes had a headway under 15 min. — [CSE "Waiting for a bus"](https://cdn.cseindia.org/userfiles/waiting-for-bus-report.pdf)
- Static GTFS in the repo: feed_version v32, feed_start 2025-01-01. A single service_id is valid all 7 days (no weekday/weekend calendars). Route_ids are split by direction (e.g., `102AUP`, `102ADOWN`), with 1,814 route_ids under agency DTC and 760 under DIMTS. — (local data check) [gtfs_static](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/gtfs_static/calendar.txt)

### Inferences
- **Vehicle blocks.** Model a vehicle block as alternating UP/DOWN route_ids with terminal dwell. On route 8, a 200–240 min round-trip cycle at a 20-min headway implies 10–12 vehicles cycling (about 5–6 per direction at any time), matching the 10 timetable rows. A later block (14:00–) re-starts after a mid-day break, consistent with two shifts per bus. Expect GPS gaps or depot runs around 11:30–14:00 on many routes.
- **Waiting time.** Scheduled headways are long on most routes (median route block ≈ 10 departures per direction per day). Passengers on low-frequency routes probably time their arrival, so expected wait ≠ headway/2. For high-frequency routes (e.g., 211, 473, 970B, 753A, 214, 85, 33, 623, 309, 78, 429, 166, each with 165+ departures/day), random arrival plus bunching corrections are more appropriate.
- **Static GTFS has no weekday/weekend distinction.** Weekday/weekend and real frequency differences must come from GPS, not the static timetable.
- **Published trips vs timetable departures.** ES's 32,525 DTC trips/day is about twice the departures in the PDF timetable (~16.6k). The PDF may be incomplete, or ES may count differently. Use GPS-derived trip counts.

### Gaps
- No published DTC/DoT norm for terminal layover or recovery time, crew shift times, or depot pull-out/pull-in windows. These were inferred only from timetable structure.
- No published on-time performance, schedule adherence or headway-regularity KPI for 2024–2026.
- No official city-wide measurement of bunching.
- The meaning of "STL" suffixes in timetable route names is not explained in the PDF.

## 3. GPS / real-time feed facts (OTD / Transport Stack GTFS-RT)

### Takeaway
Real-time positions come through Delhi Open Transit Data (OTD), which requires an API key; the realtime page is a key-request form. No official refresh-rate or latency specification was found. Community claims range from about 10 s (feed) to 1 min (archiving cadence). In the repo's October 2026 data, consecutive pings per vehicle are almost always 11 s apart (p90 22 s). About 6,100 vehicles appear per day, which is effectively the whole fleet now that cluster operations sit under DTC. The feed is raw, so expect duplicates, gaps, noise and off-service vehicles.

### Cited Findings
- The OTD realtime data page is an API-key request form (name, institution, use type, purpose). Agency logos shown are DMRC, IIIT-Delhi, DTC and DIMTS; the copyright reads "© 2017-2023". The page gives no refresh or latency specification. — [OTD realtime](https://otd.delhi.gov.in/data/realtime/)
- The Transport Stack catalogue (undated, search summary) says "Cluster Buses GPS data is included, and DTC Buses GPS data will be made available soon." — [Delhi Transport Stack data services](https://delhi.transportstack.in/data-services). This conflicts with the hackathon README, which says the October 2026 GPS is "DTC buses only" — [README](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/README.md)
- The hackathon README describes the October 2026 GPS as "decoded GTFS-Realtime vehicle positions for DTC buses", one SQLite DB per day (124 GB unpacked). It warns "The feed is raw: expect duplicates, gaps and GPS noise." trip_id is "assigned by the Transport Stack pipeline". — [README](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/README.md)
- Community reports on update rate (search summaries):
  - About 10 s updates for DTC and cluster buses — [DTC-Tracker GitHub](https://github.com/saranshgemini18-del/DTC-Tracker)
  - An earlier archive at a 1-minute cadence; the realtime feed at one point "had gotten inflated with duplicating/redundant entries" before being fixed — [DataMeet thread](https://groups.google.com/g/datameet/c/exEoW8aGHu0)
  - The endpoint pattern is `dts-backend.transportstack.in/api/dataset/otd/get-file?agency=delhi-buses&category=realtime_gtfs&filename=VehiclePositions.pb` — [godseye PR](https://github.com/Phaviwylera/godseye/pull/28)
- Per ES 2025-26, all inducted DTC e-buses (2,662) have factory-fitted ITS (GPS, CCTV, panic buttons). — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- 15 Oct 2026 GPS, local data check on the repo's interim (pre-processed) parquet ([file](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/interim/bus_gps/date=2026-10-15/part.parquet)):
  - Volume: 18.3 M pings from 6,093 vehicles.
  - Ping interval per vehicle: p10–p75 = 11 s, p90 = 22 s (i.e., some missed pings).
  - 0.13% of pings repeat the previous timestamp (zero interval), and 2.7% report speed = 0.
  - Distinct vehicles reporting, by IST hour:

    | Hour (IST) | 00 | 02 | 05 | 08 | 10 | 14 | 18 | 22 |
    |---|---:|---:|---:|---:|---:|---:|---:|---:|
    | Vehicles | 1,388 | 772 | 2,101 | 5,556 | 5,724 | 4,869 | 5,604 | 3,750 |

### Inferences
- **Effective feed cadence is about 11 s in October 2026.** A 22 s interval appears at p90, so drop-outs exist. This is fine for link-level travel times. Stop-arrival detection should interpolate between pings (11 s at 30 km/h ≈ 90 m).
- **"Ghost" or off-service vehicles are material at night.** 772 vehicles reported positions in the 02:00 hour, against 86 official night-service buses. Depot moves, dead runs and parked buses with live trackers must be filtered before using GPS for headways or ETAs (filter by route_id/trip_id assignment, movement and depot geofences).
- **Coverage is about 87%.** About 6,093 GPS vehicles a day against a fleet of about 6,988 (14 Oct 2026) means the feed covers the bulk of the fleet. Since DIMTS was folded into DTC from April 2026, "DTC buses only" now means essentially all city buses (DL1PD 4xxx non-AC CNG units, typical of ex-cluster buses, are present).

### Gaps
- No official documentation of GTFS-RT refresh interval, end-to-end latency, or a TripUpdates feed for 2025–2026. The OTD documentation page was not retrieved.
- No published audit of ghost or stale vehicles, or of trip_id/route_id assignment accuracy.

## 4. Ticketing: conductor ETM vs ONDC/QR, e-ticket share, Pink Saheli card, pink-ticket share, passes

### Takeaway
Most fares are still paid in cash to conductors using ETMs. One Delhi and ONDC QR tickets are a small minority: 6% of tickets in 2021 trials, about 1.5 lakh/day in January 2024, and about 88.8k passengers/day in the repo's October 2026 ONDC data. Women's free rides moved in 2026 from untracked paper pink tickets to the NCMC "Pink Saheli Smart Card", which is tapped on the ETM. The card became mandatory sometime between 1 August and 4 October 2026 (sources conflict). October 2026 is therefore a transition month. Women's free trips are about 42% of boardings and never appear in ONDC data.

### Cited Findings
**Paper pink tickets (pre-2026)**
- In 2022, 95.6% of pink tickets were paper and 4.4% were bought via the One Delhi app (Planning Department 2022b). Paper tickets record neither origin-destination nor time. Two-thirds of DIMTS cluster buses had ETMs able to record location and time stamps, yet pink tickets were still issued on paper. — [WRI India working paper, Mar 2025](https://wri-india.org/sites/default/files/2025-04/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf)
- Pink tickets are reimbursed at ₹10 each. In 2022-23 the pink-ticket subsidy was ₹4.0 bn (DTC ₹2.0 bn, DIMTS ₹2.0 bn), against ₹0.5 bn for all other concessional passes. — [WRI India](https://wri-india.org/sites/default/files/2025-04/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf)
- In WRI's July 2023 survey of 2,010 women bus users, 9% said "Conductors do not issue tickets in time". — [WRI India](https://wri-india.org/sites/default/files/2025-04/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf)

**Free-ride volume and women's share**
- FY2025-26 (to February 2026): 56.21 crore free trips by women in DTC and DoT buses, with ₹562.17 crore subsidy. Free travel is "implemented … with provision of Pink Saheli Smart Card/NCMC Card. A single journey pass of face value of 10/- for both AC and Non-AC buses is being issued." — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Women's share of daily bus ridership: 33% (2019-20, from October 2019); 26% (2020-21); 27% (2021-22); 42% (2022-23). Women's daily ridership was 1.682 M in 2019-20 and 1.720 M in 2022-23. — [WRI India, Table 1, citing Planning Dept 2023a](https://wri-india.org/sites/default/files/2025-04/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf)
- An NBER paper reports women's share rose from 33% to 44% within 20 days of launch (search summary). — [NBER w32508](https://www.nber.org/system/files/working_papers/w32508/w32508.pdf)

**Pink Saheli Smart Card rollout (dates conflict across sources)**
- Card issuance was announced to start on 23 October 2025 (search summary). — [Travel and Tour World](https://www.travelandtourworld.com/news/article/delhi-government-to-launch-pink-cards-for-women-and-transgender-commuters-on-october-23-2025-offering-free-bus-travel-across-the-capital/)
- An official launch in March 2026 (one summary says 2 March 2026) is reported, but was not verified by fetch. — [Zee News](https://zeenews.india.com/india/delhi-govt-launches-pink-saheli-smart-card-for-women-transgender-facilitating-free-bus-travel-in-delhi-2979443.html); [GoodReturns](https://www.goodreturns.in/news/delhi-pink-saheli-smart-card-free-bus-travel-scheme-011-1493605.html)
- 17 July 2026 report: paper pink tickets invalid after 31 July 2026, card mandatory from 1 August 2026, valid on DTC and cluster buses. Riders "tap it on the Electronic Ticketing Machine (ETM) while boarding the bus". — [Times Today](https://www.timestoday.co/2026/07/17/pink-saheli-smart-card-mandatory-for-free-dtc-bus-travel-from-august-1-2026/)
- A DTC circular of 10 July 2026 set 31 July 2026 as the last day for paper pink tickets. The deadline was later extended, and the card became mandatory on 1 October 2026. The card is a personalised NCMC card, first issue free, for Delhi residents. — [BusPe guide](https://buspe.app/guides/delhi-bus-fares-passes)
- Other conflicting mandatory dates:
  - 1 September — [NewsX](https://www.newsx.com/india/no-more-pink-tickets-on-delhi-buses-why-women-need-the-pink-saheli-smart-card-from-september-1-266667/) (title only)
  - 4 October, under the "DTC (Free and Concessional Passes) (Second Amendment) Regulations, 2026" — [Zeebiz](https://www.zeebiz.com/india/news-delhi-women-s-free-bus-travel-pink-saheli-smart-card-now-mandatory-check-new-rules-403353) (search summary; page returned 402)
- 3 October 2026: about 19 lakh cards distributed (Transport Minister). PTI reports the paper pink ticket facility is unlikely to be extended. There are 50 authorised centres; duplicate cards cost ₹49. — [Elets eGov, 3 Oct 2026](https://egov.eletsonline.com/2026/10/delhi-rolls-out-pink-saheli-smart-card-heres-how-to-get-one/)
- The minimum eligibility age is reported as 5+ by [Elets](https://egov.eletsonline.com/2026/10/delhi-rolls-out-pink-saheli-smart-card-heres-how-to-get-one/) and as 12+ by [BusPe](https://buspe.app/guides/delhi-bus-fares-passes). These conflict.

**ONDC / One Delhi QR tickets**
- DTC QR tickets went live on ONDC in September 2024, covering both DTC and DIMTS buses, bought via the One Delhi app. — [CXOToday press release](https://cxotoday.com/press-release/digital-qr-ticketing-for-dtc-buses-now-live-on-the-ondc-network/); [ONDC on X](https://x.com/ONDC_Official/status/1830615652437991612)
- In 2021 trials, app tickets were 6% of total ticketing; the app gives a 10% fare discount (search summary). — [HT via PressReader, 18 Jul 2021](https://www.pressreader.com/india/hindustan-times-delhi/20210718/281651078120594)
- January 2024: One Delhi sold about 1.5 lakh DTC bus QR tickets a day and had about 3 lakh active users (DMRC ED Anuj Dayal). — [Business Today, 6 Jan 2024](https://www.businesstoday.in/technology/news/story/delhi-metro-introduces-seamless-travel-experience-with-one-delhi-app-integration-412136-2024-01-06)
- ONDC network-wide volume, all cities, metro plus bus: more than 3 lakh tickets a day (June 2026; search summary) — [Business Standard](https://www.business-standard.com/industry/news/ondc-enables-three-lakh-daily-bus-and-metro-ticket-bookings-126060101212_1.html). Delhi: 30+ apps and "9.2 crore+" cumulative digital journeys (September 2026; search summary) — [ONDC on X](https://x.com/ONDC_Official/status/2098683617291755755); [Orissa Diary](https://orissadiary.com/delhi-cm-highlights-ondc-enabled-metro-bus-ticketing-as-digital-journeys-cross-9-2-crore/)
- October 2026 ONDC file, local data check ([October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv)):
  - Volume: 2,559,899 ticket rows and 2,753,606 passengers over 31 days, about 82.6k tickets and 88.8k passengers a day.
  - All rows have ticket_type_id = 1.
  - 48.5% of rows have no vehicle_number.
  - Tickets by purchase hour:

    | Hour | 07 | 08 | 09 | 10 | 12 | 14 | 17 | 18 | 19 | 21 |
    |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
    | Tickets | 150k | 316k | 351k | 204k | 85k | 68k | 164k | 235k | 222k | 96k |

**Fares and passes**
- Fares: non-AC ₹5/10/15; AC ₹10/15/20/25 by distance. Daily pass ₹40 (non-AC) or ₹50 (AC). In 2024, 86% of 2,354 route patterns used the ₹5/10/15 ladder. Cash to the conductor is "the most common method". — [BusPe guide](https://buspe.app/guides/delhi-bus-fares-passes)
- GNCTD gives concession passes (students, seniors, disabled, freedom fighters, etc.) on DTC and cluster buses and reimburses them. The survey gives no counts. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)

### Inferences
- **Pink/free share of boardings.** 56.21 crore free trips over about 334 days (April 2025 to February 2026) is about 16.8 lakh a day. Against about 39–41 lakh total daily boardings (DTC 24.3 lakh + DoT/cluster about 15 lakh), that is about 41–43% of boardings, consistent with WRI's 42% for 2022-23.
- **ONDC share of ridership.** ONDC passengers (about 88.8k/day) are about 2.2% of all boardings, but about 3.5–4% of paying boardings (about 40 lakh minus about 17 lakh free, minus pass holders). This reconciles the "3–4% of all bus tickets" figure if the denominator is paid tickets.
- **Scaling ONDC to total load.** ONDC tickets are paid tickets, so they exclude women's free rides and pass holders and are male- and commuter-skewed. Expansion factors must differ by time of day:
  - ONDC shows a sharper AM peak (09h: 351k) than PM peak (18h: 235k).
  - Women's travel is concentrated in 7–18h. WRI found women mostly travel on weekdays in the morning peak (7–11) and off-peak (11–18). A pre-scheme study (search summary, [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S2213624X21001814)) found the women's share on buses falls markedly after dark.
- **October 2026 is a transition month.** Paper pink tickets were phased out between August and October 2026 (dates conflict), and free rides became ETM-recorded card taps. If the model uses any ETM/AFCS data, women's taps exist from roughly October 2026 onward. The ONDC file contains none (single ticket_type_id).

### Gaps
- No official 2025–2026 split of tickets by channel (cash/ETM, NCMC card, ONDC/QR) or by pass type. The pass-holder share of boardings is unknown.
- No post-scheme time-of-day profile of pink tickets or Pink Saheli taps. Paper pink tickets carried no time stamp.
- The exact date paper pink tickets ended conflicts across sources (1 August, 1 September, 1 October, 4 October 2026). An official DTC notice was not retrieved.
- It is unconfirmed whether Pink Saheli taps are recorded with stop-level origin (ETM GPS stamp) or only the route.

## 5. Ridership (2024, 2025, 2026), by agency; busiest corridors and peak hours

### Takeaway
Official daily ridership: DTC 25.58 lakh plus cluster 15.25 lakh, about 40.8 lakh in FY2024-25, against 51.1 lakh in FY2019-20. FY2025-26 (to 20 March 2026) has DTC at 24.29 lakh/day. The FY2025-26 cluster/DoT figure is not published. No route-level ridership was found. Timetable, GPS and ONDC data all show an 08–10h morning peak and a 17–19h evening peak, with a 13–15h trough.

### Cited Findings
- DTC daily average passengers in lakh (ES Statement 12.7): 2013-14: 43.47; 2019-20: 33.39; 2020-21: 12.24; 2021-22: 15.62; 2022-23: 25.02; 2023-24: 25.99; 2024-25: 25.58; 2025-26 (to 20 March 2026): 24.28/24.29. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- DTC operating ratios (ES Statement 12.7):

  | Year | Load factor | Passengers per bus on road per day |
  |---|---:|---:|
  | 2024-25 | 88.77% | 731 |
  | 2025-26 | 88.33% | 929 |

  — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- DTC daily passengers by bus type, FY2025-26, in lakh: non-AC 5.11, AC CNG 1.91, E-12 m 14.41, E-9 m 2.86. The FY2024-25 split was 11.03 / 4.48 / 10.06 / 0.01. — [ES 2025-26, Statement 12.8](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Cluster daily passengers in lakh (ES Statement 12.9): 2019-20: 17.71; 2022-23: 16.39; 2023-24: 16.01; 2024-25: 15.25. Cluster load factor was 78% (CIRT formula) and passengers per bus per day 511 in 2024-25. — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)
- Combined total of about 51 lakh (2019-20) falling to about 40.8 lakh (2024-25), a drop of nearly 20% (search summary of a report on the same survey). — [NewsBytes](https://www.newsbytesapp.com/news/auto/economic-survey-2025-26-finds-delhi-bus-ridership-down-nearly-20/story)
- Total daily ridership in millions (Planning Dept, via WRI): 4.524 (2018-19); 5.102 (2019-20); 2.077 (2020-21); 2.549 (2021-22); 4.055 (2022-23). — [WRI India](https://wri-india.org/sites/default/files/2025-04/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf)
- Conflicting figures (search summaries):
  - ThePrint: "33 lakh in 2019 to 14.5 lakh in 2025" — scope unclear, inconsistent with ES — [ThePrint](https://theprint.in/ground-reports/dtcs-lost-decade-model-fleet-to-mess-electric-overhaul-is-the-new-hope/2696678/)
  - January–June 2025 average of 1.43 M male plus 1.48 M female passengers a day, excluding monthly pass holders (about 2.9 M) — [Travel and Tour World](https://www.travelandtourworld.com/news/article/delhi-government-to-launch-pink-cards-for-women-and-transgender-commuters-on-october-23-2025-offering-free-bus-travel-across-the-capital/)
  - 3.6 M DTC+DIMTS combined (February 2023) — [Wikipedia DTC](https://en.wikipedia.org/wiki/Delhi_Transport_Corporation)
- Anand Vihar ISBT handles about 2,300 buses and about 1.25 lakh commuters a day (October 2026). — [Asia News Network](https://asianews.network/?p=307871)
- Busiest routes or stops, popularity proxies only (search summaries):
  - Moovit lists 729 and 615 as "most popular" DTC lines, undefined — [Moovit](https://moovitapp.com/index/en/public_transit-lines-Delhi-3801-859237)
  - BusPe lists top stops ISBT Nityanand Marg, GPO and Super Bazar, by stop-level route counts — [BusPe](https://buspe.app/)
- Most scheduled departures per day in the January 2026 timetable (researcher's parse): 211 STL (316), Airport STL (300), 211 (284), 473 (275), 970B (260), 753A (232), 214 (228), 85 (204), 460 STL (201), 33 (192). — [DTC timetable Jan 2026](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_jan_2026.pdf)
- Peak-hour indicators:
  - Timetable departures peak at 08h (1,145) and 16h (1,146), with a trough at 13–14h (about 670–700). — [DTC timetable Jan 2026](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_jan_2026.pdf)
  - Active GPS vehicles plateau 08–12h (about 5,500–5,700) and 17–20h (about 5,400–5,600). — (local data check) [GPS 15 Oct 2026](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/interim/bus_gps/date=2026-10-15/part.parquet)
  - ONDC tickets peak at 09h, with a secondary peak at 18h. — (local data check) [October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv)

### Inferences
- **Average boardings per trip.** DTC FY2025-26 averages about 75 boardings per one-way trip (24.29 lakh / 32,525 trips) and about 4.85 boardings per bus-km (24.29 lakh / 5.01 lakh km).
  - By type: E-12 m about 863 passengers per bus per day (about 4.2 per km); E-9 m about 640 per bus per day (about 3.7 per km).

  These are useful calibration targets for scaling ONDC to total load. Boardings per trip exceed 9 m rated capacity (36), so turnover along the route matters for peak-load estimation.
- **A 2026 total for calibration.** Using FY2025-26 DTC (24.3 lakh) plus the last cluster value (15.25 lakh, FY2024-25) gives about 39–40 lakh/day. The October 2026 total is unpublished. With fleet growth back to about 6,988 by October 2026, ridership may have recovered somewhat, but there is no source for that.

### Gaps
- No official 2026 (calendar or FY2026-27) ridership figure, and no FY2025-26 DoT/cluster ridership.
- No route-level or corridor-level ridership or peak-load (PHPDT) data for 2024–2026 was found.
- No official source for the day-of-week pattern.

## 6. Deployed Delhi apps (One Delhi, Chartr, Google Maps) and published ETA/crowding accuracy claims

### Takeaway
One Delhi (government; QR tickets plus live tracking), Chartr (QR tickets, live tracking and ETAs from OTD) and Google Maps (live bus status since a 2021 partnership) all consume the same OTD GPS. None publishes a quantitative ETA accuracy figure. The only accuracy number found is Chartr's "≥ 90%" claim for camera-based automatic passenger counting, labelled a "live pilot", with an inconsistent on-page stat. The only quantitative ETA result is a non-peer-reviewed GitHub model (LightGBM 14–24% better than the historical median).

### Cited Findings
- **Chartr.**
  - App listing: "Track buses in real time and get accurate ETAs", including bus type (AC/non-AC). Source of live bus data and ETAs: "Delhi Open Transit Data Platform" (search summary). — [Chartr on Google Play](https://play.google.com/store/apps/details?id=in.chartr.transit&hl=en_IN)
  - Website claims 3,500+ buses live in Delhi (search summary). — [chartr.in](https://chartr.in/)
  - Chartr APCS (camera passenger counting): badge "≥ 90% Accuracy", labelled "Live Pilot", while the page's stat reads "≥ 0%". There is no stated method and no Delhi deployment count. Stop arrivals in the staff app update "every minute"; the passenger dashboard updates "every few minutes". Example per-bus count: front 10, back 18, total 28. — [Chartr APCS](https://chartr.in/products/apcs/)
- **One Delhi.** Sells DTC (and, via ONDC, DIMTS) QR tickets with a 10% discount. It had about 3 lakh active users in January 2024 and also locates EV chargers. — [Business Today](https://www.businesstoday.in/technology/news/story/delhi-metro-introduces-seamless-travel-experience-with-one-delhi-app-integration-412136-2024-01-06); [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf); [Play listing](https://play.google.com/store/apps/details?id=com.delhitransport.onedelhi&hl=en_IN)
- **Google Maps.** The Delhi Govt–Google partnership (2021) made about 3,000 buses trackable in real time, with trip-time and delay estimates (search summaries). — [Zee News](https://zeenews.india.com/india/passengers-in-delhi-will-now-be-able-to-track-dtc-buses-on-google-maps-2376489.html); [Zee Biz](https://www.zeebiz.com/technology/apps/news-google-maps-to-show-real-time-info-on-delhis-cluster-bus-service-160683); [Maps of India](https://www.mapsofindia.com/my-india/india/delhi-government-and-google-partner-to-provide-real-time-data-bus-tracking-service-on-maps)
- **Independent ETA benchmark.** A LightGBM arrival model beats the historical median by 14% on familiar routes and 24% on unseen routes, on one evening of data (21–22 October 2026). No MAE is reported. — [how-Delhi-buses-move](https://github.com/rishabhjain9196/how-Delhi-buses-move)
- **Older academic work.** ANN travel-time prediction with GPS on DTC route 832, and a GPS-based timetabling algorithm deployed on 100+ buses in New Delhi (search summaries). — [ResearchGate](https://www.researchgate.net/publication/312464645_Prediction_of_Bus_Travel_Time_Using_ANN_A_Case_Study_in_Delhi); [arXiv 1910.08903](https://arxiv.org/pdf/1910.08903)

### Inferences
- **Benchmarks for an ETA model.** Because no app publishes ETA accuracy, a defensible benchmark is "historical median by route-segment and hour". Results can be framed as % improvement over that baseline, as the GitHub project does, plus absolute MAE at several horizons.
- **Crowding claims are untested.** No deployed app in Delhi publishes validated crowding levels. Chartr's APCS is a pilot with unclear metrics. A crowding model calibrated against ES boardings/bus/day and ONDC is novel rather than a replication.

### Gaps
- No published ETA accuracy (MAE, % within ±X min) for One Delhi, Chartr or Google Maps in Delhi.
- No published accuracy for crowding indicators in any Delhi app. Chartr APCS accuracy method and fleet coverage are unknown.
- Google Maps' current (2025–2026) Delhi live-bus coverage was not confirmed beyond 2021 launch coverage.
