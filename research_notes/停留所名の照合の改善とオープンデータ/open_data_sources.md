# Open data for Delhi bus-stop names, and gazetteers for aliases and geocoding (matching ONDC e-ticket stop names to GTFS v32)

Research date: 2026-11-16. Scope: every openly reachable source that lists Delhi (NCT + NCR towns on Delhi routes) bus-stop names, plus place/POI gazetteers usable as aliases or for geocoding. Builds on `../停留所名の照合と通過検出/transit_stop_matching.md` and `indic_name_matching.md`; their OSM bus-stop counts (2,421 stops, 228 `name:hi`, 71 `alt_name`, 51 `short_name`) and the DTC 740C circular are not repeated.

How to read this file:
- **Local check** = computed by me on 2026-11-16 on this machine, read-only, from the team's `data/` folder and from public files I downloaded (all under 5 MB, or read partially with HTTP range requests). No ticket data or ticket names were sent to any external service. Name comparisons are "verbatim after lower-casing and collapsing spaces", so they understate what a fuzzy matcher would find.
- "Unmatched ends" = ticket ends with `i == -1` or `j == -1` in `data/processed/tickets_matched.parquet` (1,058,160 of 5,119,798 ends = 20.67%; 967,716 of them on routes that exist in v32).
- Headline: **DTC publishes a machine-readable route-by-route stop master ("All Route Fair Stages", .xlsx, last modified 7 Oct 2026). 99.0% of the unmatched ticket ends on DTC routes carry a name that appears verbatim in it**, so it is very probably the same lineage as the ticketing stop list. **Two older GTFS versions (2018 OTD, 2022–24 Transport Stack/Chartr) are publicly archived on Mobility Database**; they carry coordinates for 67% of the unmatched ends' names, and the old "U…"/"DC…" stop codes.

---

## 1. GTFS lineage: which Delhi GTFS versions are publicly archived, what do they contain, and can an older version explain why ticket names differ from v32?

### Takeaway
Three Delhi bus GTFS lineages are reachable without a login:
- the 2018 OTD/IIIT-Delhi feed, still the content behind otd.delhi.gov.in, gated by a "purpose" pop-up;
- a 2022–24 Transport Stack/Chartr-style feed, archived on Mobility Database through a now-archived Transitland GitHub mirror;
- the team's v32 (Oct 2026).

None has `translations.txt` (Hindi) or `fare_attributes`/`fare_rules`. The two older feeds carry real `stop_code`s ("U…" and "DC…" codes shared across both); v32 replaced them with unrelated 8-hex codes and added `fare_stage`. Ticket names match the older feeds much better than v32 on the names v32 lacks: 61% of the ticket ends whose name is absent from v32 appear verbatim in an older feed. So yes, version drift explains a large part of the mismatch. Stop renaming in the Chartr/Transport Stack editor is the likely cause (inference).

### Cited Findings
**Official OTD portal (Transport Dept GNCTD + IIIT-Delhi)**
- **Static bus data page.** Four datasets, each "Last Updated: June 20, 2024":
  - Stops 3,464 ("all the active stops and terminals")
  - Routes 543
  - Stop Times 378,324
  - Trips 16,562
  - "Download Data" gives all files as one .zip, after a modal asks for Usage Type (Commercial/Non-Commercial) and Purpose; "By clicking this, you agree to our Terms and Conditions". No login or key is required for static data.
  - Source: [OTD static data](https://otd.delhi.gov.in/data/static/)
- **DMRC static data on the same portal.** Stops 262 ("active metro stations and terminals"), Routes 36, Stop Times 411,686, Trips 17,997, all "Last Updated: Aug. 10, 2023". — [OTD DMRC static](https://otd.delhi.gov.in/data/staticDMRC/)
- **Documentation.** Static files are agency, calendar, stops, routes, trips, stop_times. Real-time data is at `/api/realtime/VehiclePositions.pb?key=…`. — [OTD documentation](https://otd.delhi.gov.in/documentation)
- **Announcements.** The last entry is dated 3 April 2019 (real-time server maintenance). — [OTD announcements](https://otd.delhi.gov.in/announcements/)
- **Terms (PDF) — not an open licence.**
  - The site is "owned and operated by the Department of Transport (DoT), GNCTD".
  - "OTD Platform requires you to provide basic information to access static data and requires a user account to access real time data."
  - "Modification of any of the Contents or use of the Contents for any other purpose will be a violation of DoT's copyright".
  - Source: [OTD terms](https://otd.delhi.gov.in/terms/)

**Mobility Database (MDB) archive** (catalogue CSV last modified 13 Nov 2026; 6,698 rows; 21 India feeds; Delhi bus feeds: only mdb-1262 and mdb-3139, both "inactive", no features recorded) — [MDB catalogue CSV](https://files.mobilitydatabase.org/feeds_v2.csv)
- **mdb-1262 "Delhi Transport Corporation"** (community feed).
  - Source URL: `transitland/gtfs-archives-not-hosted-elsewhere/raw/master/delhi-bus.zip`. Licence URL: `https://opendata.iiitd.edu.in/terms`.
  - Two archived datasets:
    - downloaded 7 Jun 2024, service window 2018-11-01 to 2018-11-08;
    - downloaded 17 Jun 2025, service window 2022-01-01 to 2024-01-01; 18.86 MB zipped / 114.72 MB unzipped; 2,964 routes.
  - Source: [mdb-1262](https://mobilitydatabase.org/feeds/gtfs/mdb-1262)
- **mdb-3139.** The same zip pinned to a commit SHA; one dataset, downloaded 11 May 2026, same counts and service window. — [mdb-3139](https://mobilitydatabase.org/feeds/gtfs/mdb-3139)
- **Direct, login-free dataset files:**
  - [2018 zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202406071502/mdb-1262-202406071502.zip), 2,883,733 bytes
  - [2022–24 zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202506170152/mdb-1262-202506170152.zip), 19,777,166 bytes
  - mdb-3139's copy: identical size
- **Validator report for the 2018 dataset.**
  - Files: agency, calendar, routes, stop_times, stops, trips. Counts: Stops 8,374, Routes 543, Trips 16,562, Shapes 0.
  - Agency name spelled "Delhi Transport Coporation". `gtfsFeatures: []`.
  - Notices include `stop_without_stop_time` 5,172.
  - Source: [report_7.1.0.json](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202406071502/report_7.1.0.json)
- **Validator report for the 2022–24 dataset.**
  - Agencies: "Delhi Integrated Multi-Modal Transit System Ltd." and "Delhi Transport Corporation". The same names and URLs as v32's `agency.txt`.
  - Same 6 files: no shapes, feed_info, fares or translations. Counts: Stops 6,342, Routes 2,964, Trips 78,507.
  - Notices: 8 `duplicate_key` errors.
  - Source: [report_8.0.0.json](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202506170152/report_8.0.0.json)
- **Transitland mirror history.** Commits touching `delhi-bus.zip`:
  - 6 Apr 2022 "Delhi Bus"
  - 25 Feb 2023 "latest Delhi feed downloaded manually"
  - 19 Mar 2026 "deprecating this repo"; the repo is archived read-only
  - So the 2022–24 dataset is most likely the Feb 2023 manual download. The service window and the 2,964 routes fit; the exact timing is an inference.
  - Source: [commit history](https://github.com/transitland/gtfs-archives-not-hosted-elsewhere/commits/master/delhi-bus.zip)

**Other copies found only in search results (pages unreachable when tried)**
- **India Data Platform (CivicDataLab CKAN) "delhi gtfs static"**: "Last Updated August 16, 2022" (search snippet; HTTP 503 on fetch). — [CKAN](https://ndp.ckan.civicdatalab.in/dataset/delhi-gtfs-static)
- **TUMI Data Hub "Open Transit Data (Static)"**, pointing to opendata.iiitd.edu.in. Its GTFS file is dated April 2023 and the licence note says "might be outdated" (search snippet; connection refused on fetch). — [TUMI hub](https://hub.tumidata.org/dataset/open_transit_data_static_delhi)
- **transitfeeds.com / OpenMobilityData** returned HTTP 403, and no Delhi listing surfaced in search. — [transitfeeds search](https://transitfeeds.com/search?q=delhi)

**Transport Stack and the ONDC seller**
- **Transport Stack catalogue.** delhi.transportstack.in is a single-page app whose catalogue loads from a backend API. I could not list its static GTFS versions, so I found no public archive of v1–v31. The earlier sibling note quoted the catalogue as saying cluster GPS is included — [Transport Stack data services](https://delhi.transportstack.in/data-services)
- **ONDC seller code.** It reads stops and fares from a database `transit_db`, not from GTFS:
  - table `stops_pair_new`: `start_stop_code`, `end_stop_code`, `start_stop_name`, `end_stop_name`, `route_id`, `start_sequence`, `end_sequence`, `fare_details` JSON (`bf` base fare, `tl` toll);
  - table `stops_new`: `code`, `name`, `route_id`;
  - GPS coordinates are hard-coded `0.0` placeholders.
  - The code does not show how the tables are filled.
  - Source: [modules/fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py)

**Local checks: what each feed contains**
- **v32 (team copy).**
  - `stops.txt` = stop_id, **stop_code**, stop_name, lat, lon. All 6,862 stops have a distinct 8-character hex code (e.g. `9CE15308`).
  - `stop_times.txt` adds non-standard `fare_stage` and `stop_dist` columns.
  - Also has `shapes.txt` and `feed_info.txt` (`feed_version v32`, start 2025-01-01).
  - No `translations.txt`, no `fare_attributes.txt`/`fare_rules.txt`.
  - The zip members are dated 2026-10-07, although the zip is named `delhi_buses_static_gtfs_v1.zip`.
  - Source: [Local check](../../data/raw/gtfs_static/stops.txt)
- **2018 OTD feed** (downloaded from MDB).
  - `stops.txt` = stop_id, **stop_code**, stop_name, lat, lon. Code prefixes: `U` 4,031 (e.g. U03915), `DC` 3,712, `NS` 108, `CWG` 16.
  - Only 3,202 of 8,374 stops are used in stop_times; 3,464 "active" on the OTD page.
  - Route names look like "108DOWN". Files were written 26 Oct–28 Nov 2018.
  - The counts (543 routes, 16,562 trips) equal the OTD page, so the OTD download dated "June 20, 2024" still serves this 2018 content (inference from equal counts).
  - Source: [Local check of MDB 2018 zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202406071502/mdb-1262-202406071502.zip)
- **2022–24 feed** (stops/routes read via range requests, about 156 KB fetched).
  - `stops.txt` = stop_id, **stop_code**, stop_name, lat, lon, zone_id. Codes: `U` 2,324, `DC` 2,092, empty 1,768, `NS` 26.
  - `zone_id` holds 4,556 distinct float values (0.0, 1.0, …), so it is not a usable fare zone.
  - routes: DIMTS 1,964, DTC 1,000.
  - Source: [Local check of MDB 2022–24 zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202506170152/mdb-1262-202506170152.zip)
- **Stop-code continuity.**
  - 3,577 stop_codes are shared by the 2018 and 2022–24 feeds.
  - **0** are shared between 2022–24 and v32.
  - The v32 hex code is not CRC32 / MD5[:8] / SHA1[:8] / SHA256[:8] of the old code, the old or new stop_id, the name, or the coordinates (tested on 300 stops).
  - 3,079 v32 stops have a same-name 2022–24 stop within 50 m, and 2,675 of those carry a U/DC code. So **39% of v32 stops can inherit an old code** by exact name + 50 m alone.
  - Source: [Local check](../../data/raw/gtfs_static/stops.txt)

**Local checks: do older feeds explain the ticket names?**
- **Exact name anywhere in the feed**, share of all ticket ends: v32 **72.98%**, 2022–24 feed **62.91%**, 2018 feed **59.10%**.
- **Ends whose name is not in v32** (27.0% of ends): 29.4% are in the 2022–24 feed, 50.1% in the 2018 feed, **61.0% in either**. Largest such names: "Mahipal Pur" 23,401 ends, "Badarpur Border" 20,533, "West Patel Nagar" 17,044, "Hamdard Nagar" 16,145, "Ashram" 13,377, "Laxmi Nagar" 12,024, "S J Hospital" 7,145.
- **Unmatched ends on routes present in v32** (967,716):
  - **67.25%** have a verbatim name in the 2018 or 2022–24 feed.
  - For those, the nearest older-feed coordinate lies within 100 m of the ticket route's v32 pattern for 79.0% of ends; within 200 m for 87.9%, 400 m for 94.0%, 1 km for 97.9%.
  - So **611,698 ends (63.2% of these unmatched ends) can be placed within 400 m of their route** from older-feed coordinates.
  - Caveat: I took the nearest of possibly several same-name copies. 230 of 6,971 older names have copies more than 1 km apart, e.g. generic names, so this is optimistic for such names.
- **Unmatched ends by route agency:**

  | v32 agency of the ticket route | Unmatched ends | In 2022–24 feed | In 2018 feed | In either older feed |
  |---|---|---|---|---|
  | DTC | 864,140 | 43.2% | 60.7% | 68.2% |
  | DIMTS | 103,576 | 57.4% | 31.7% | 59.1% |
  | Route not in v32 | 90,444 | 64.9% | 43.0% | 69.4% |

- **Routes.**
  - Ticket routes present in v32: 98.2% of tickets. In the 2022–24 feed: 85.1%. In the 2018 feed: 26.3%.
  - 279 ticket routes (45,222 tickets) are absent from v32; 106 of them (24,824 tickets) exist in the 2022–24 feed.
  - Only 7.8% of unmatched ends have their name on the *same* route in the 2018 feed, which has just 543 routes.
- Source for all of the above: [Local check](../../data/processed/tickets_matched.parquet)

### Inferences
- **The ticketing stop master predates v32's names.** The ONDC seller schema got route and stop codes on 20 May 2024 (sibling note `ondc_data_semantics.md`). Ticket names match the ITS-era names, the ones carried with U/DC codes in 2018–2023, and the DTC fare-stage master (Section 2), far better than v32. The most plausible story: the seller's `stops_new` was loaded from DTC/DIMTS route masters, and v32's stop names were later edited (cleaned, merged, re-spelled) in the GTFS editor. This is inference; the seller tables are not public.
- **What each lineage is best for.**
  - The 2018 feed holds the old DIMTS/ITS spellings ("U" = cluster/ITS codes, "DC" = DTC codes), which matter for DTC routes.
  - The 2022–24 feed is better for DIMTS routes and for routes missing from v32.
  - Use both as **alias-with-coordinates tables**. Take an old name, take its coordinate(s) near the ticket's route, snap to the nearest v32 stop on that route, and record (route_dir, ticket name) → v32 stop_id with provenance `old_gtfs_2018/2023`.
- **Codes.** The U/DC codes look like stable operator codes (shared 2018 → 2023). They are the best public candidate for whatever `start_stop_code` / `end_stop_code` the seller stores, but nothing public confirms the seller uses them.
- **No version of any feed** gives Hindi names, fare tables or stage numbers. Only v32 has `fare_stage` flags, and none has `stop_code`s that match the seller's (unknown) codes.

### Gaps
- **Transport Stack versions.** I could not list Transport Stack's static GTFS versions. Its catalogue is a JavaScript app, and I did not query its backend API. Whether v1–v31 are downloadable there is unknown; ask the organisers.
- **The full 2022–24 zip** (19.8 MB) was not downloaded, so its `stop_times.txt` was not checked: no route-level name comparison and no check for fare columns. Only stops/routes/agency/calendar were read.
- **Unreachable or empty copies.** The OTD bulk zip itself was not downloaded, because that needs submitting the purpose form; its counts equal the 2018 feed. The CivicDataLab (Aug 2022) and TUMI (Apr 2023) copies could not be opened, so I cannot say which lineage they hold. No Kaggle or other GitHub mirror of Delhi GTFS was found.
- **v32 stop_code scheme.** How the v32 8-hex stop_code is generated is unknown. A simple-hash test was negative.

---

## 2. Official lists from DTC, DIMTS, the Transport Department, PWD/DTIDC and data.gov.in: route-wise stop/stage lists, bus queue shelters, Hindi names, and DTC circulars

### Takeaway
The single most valuable source is DTC's **"All Route Fair Stages" master workbook** on its "Services & Time-Table" page:
- .xlsx, 2.77 MB, last modified 7 Oct 2026, no login;
- every stop of 733 routes in order (UP/DN), with fare-stage markers;
- no coordinates, codes or Hindi;
- its spellings are the ticket spellings: 82.1% of all ticket ends and 91.6% of unmatched ends have a verbatim name in it.

DTC's circular listings hold about 1,500 files, of which roughly 200+ are fare-stage circulars, mostly 2012–2015. Recent 2026 route circulars are sparse PDFs whose English tables extract cleanly but whose Hindi uses non-Unicode fonts. No public route-stop list for cluster (DIMTS) routes survives: businfo.dimts.in is offline. No bus-queue-shelter (BQS) location list is published. No Hindi stop list was found anywhere official.

### Cited Findings
**DTC "Services and Time-Table" page** (checked 16 Nov 2026) — [DTC services & time table](https://dtc.delhi.gov.in/dtc/services-and-time-table)
- **Files listed**, with sizes and Last-Modified from HTTP headers:
  - **"All Route Fair Stages"**: [`master_data_all_route_fair_stages_1.xlsx`](https://dtc.delhi.gov.in/sites/default/files/DTC/master_data_all_route_fair_stages_1.xlsx), 2,768,980 bytes, 7 Oct 2026.
  - "Current D.T.C. Time Table Nov-2026": [PDF](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_nov_2026.pdf), 1,345,071 bytes, 10 Nov 2026.
  - "DEVI Bus Routes and Time Table Nov-2026": [PDF](https://dtc.delhi.gov.in/sites/default/files/DTC/devi_dtc_all_time_table_nov_2026.pdf), 256,407 bytes, 10 Nov 2026.
  - "DEVI Buses Route Via & Fare Stage": [PDF](https://dtc.delhi.gov.in/sites/default/files/DTC/all_devi_bus_new_route_fare_stage.pdf), 215,044 bytes, 2 Dec 2025. 37 pages with a text layer, in the same UP/DN layout as the workbook.
  - "New 25 U-Special Fare Stage": [xlsx](https://dtc.delhi.gov.in/sites/default/files/2025-08/new_25_u-special_fare_stage.xlsx), 61,350 bytes, 30 Aug 2025.
  - "Express Bus Service Route": [xlsx](https://dtc.delhi.gov.in/sites/default/files/express_route_service_1.xlsx), 16,900 bytes, 13 Dec 2022.
  - Night, NCR, Destination (non-stop), Ladies Special and IGI Airport timetables.
  - Single-route PDFs: D-7701A, route 957, NCR Maharana Pratap ISBT–Baraut.
- **Workbook structure (local parse).**
  - 14 sheets: DTC Routes, Devi Routes, GPRA, U SPL, SPL, Diversion, RL, L SPL, LTD & STL, NCR, U-SPL, DAF, DS, NS.
  - Each route has side-by-side UP and DN blocks: "Fare Stage Sr No" | route | "Fare Stage" marker | stop name. All stops are listed, not just stages.
  - Parsed from 12 sheets: **93,613 stop rows, 1,415 route-directions, 733 routes, 7,966 distinct names, 29,577 fare-stage rows**. By sheet: DTC Routes 523 routes, Devi Routes 96, Diversion 161, NCR 20, NS 28.
  - No Devanagari, no coordinates, no stop codes.
  - The "DS" (destination services) sheet adds "Meter Reading", "UP Direction Distance" and "Fare Stage Distance" in km. "U-SPL" and "DS" use a different layout that my parser skipped.
  - Typos are kept, e.g. "Laxmi Bai Collage", "Paharganj Dispenasary", "L.N.J.P, Hospital", "P. S. Paharganj".
  - Source: [Local check of the DTC workbook](https://dtc.delhi.gov.in/sites/default/files/DTC/master_data_all_route_fair_stages_1.xlsx)
- **Ticket names vs the workbook** (local, exact after case-folding):
  - **Coverage.**
    - All ticket ends: name exists in the workbook 82.14%, in v32 72.98%, in either **97.34%**.
    - Unmatched ends: in the workbook 91.6%; on the *same* route-direction 76.7%.
    - Workbook coverage of ticket routes: 91.2% of tickets on DTC routes, 20.4% on DIMTS routes.
    - By agency, unmatched ends with the name in the workbook: DTC routes **99.04%** (864,140 ends); DIMTS routes 52.6%; routes absent from v32 65.1%.
  - **Every failure example from the brief is in the workbook verbatim:**
    - "S.J. Hospital" on 27 route-directions, including 502 UP/DN
    - "Sagar Pur Vashishth Park" on 24, including 711, 721 and 753 (the ticket key is 778 DN)
    - "Aerocity" on D-9101 DN and D-1104 DN
    - "Health Center" on 63, including 578 DN
    - "Telephone Exchange" on 172
    - "Badarpur" on 23, including routes 8 and 34
  - **Positioning by stop order.** For unmatched ends on routes in v32, I located the nearest workbook neighbours before and after the name that match a stop on the ticket route's v32 pattern exactly. The name then falls between two v32 stops:

    | Result | Share of these unmatched ends |
    |---|---|
    | Adjacent v32 stops (0 between) | 1.1% |
    | 1–2 v32 stops in between | 20.4% |
    | 3–5 in between | 27.2% |
    | More than 5 in between | 17.7% |
    | Only one anchor found | 14.5% |
    | Anchors out of order | 1.3% |
    | No anchor | 0.5% |
    | Name not on that route in the workbook | 17.3% |

    "Diversion" sheet excluded; exact anchors only.
  - Source: [Local check](../../data/processed/tickets_matched.parquet)

**DTC circulars: how many, how to find them, how machine-readable**
- **Listing endpoints.** Nine public Drupal listings, each paginated with `?page=N`: `/circulars-orders`, `/dtc-circulars`, `/dtc-circulars/archive`, `/circulars`, `/circulars/archive`, `/general-circulars`, `/news`, `/notice-board`, `/orders`. Each item has a title, an ISO date (often missing), a file size and a link. The homepage's "important news" block links further route PDFs under `/sites/default/files/DTC/important-news/`, e.g. `route_no_410_circular.pdf`, `circular_for_route_no_740c.pdf`, `circular_of_dhaula_kuan_to_rewari_route.pdf`, `via_change_circular_0.pdf` and `devi_buses_circular.pdf`. — [DTC home](https://dtc.delhi.gov.in/); [archive example](https://dtc.delhi.gov.in/dtc-circulars/archive)
- **My crawl** (16 Nov 2026, titles only, 1 request/s): 1,948 entries, **1,518 unique files**.
  - Route-related titles (route / fare stage / रूट / वाया / bus service): **394**, an upper bound, since it includes e.g. "cable route".
  - Titles with fare-stage wording: **218**, including some duplicate uploads (`_1.pdf`, `_2.pdf`).
  - Dated fare-stage circulars by year: 2012 26, 2013 40, 2014 13, 2015 4, 2017 1; 134 undated.
  - 2026 route circulars appear only as a handful of Hindi-titled entries "सं0-टी.आर./2/अनु.सू./…":
    - route D-9923
    - via extension of route 123
    - temporary via change at Malka Ganj Chowk for routes 19/19B/100A/…
    - NCR routes Nanaksar–Ghaziabad and Maharana Pratap ISBT–Panipat
    - DEVI new routes
  - Source: [Local check, crawl of DTC listings](https://dtc.delhi.gov.in/general-circulars)
- **Machine-readability, from samples I downloaded:**
  - D-9923 circular (2026, 2 pages): a clean English text layer with "Fare Stage" markers. It even varies spellings inside one document: "Bijwasan X-ing" vs "Bijwason Flyover", "Pushpanjali" vs "Puspanjali G-Block", "Samalka Village" vs "Samalkha X-ing", "Bharat Petrolium". — [2664.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/circulars-orders/2664.pdf)
  - Route 410 circular (2025): Hindi in a non-Unicode legacy font, so extraction gives garbage. It needs font conversion (e.g. Kruti Dev→Unicode) or OCR. — [route_no_410_circular.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/important-news/route_no_410_circular.pdf)
  - DEVI buses circular (28 pages): no usable text, so OCR is needed. — [devi_buses_circular.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/important-news/devi_buses_circular.pdf)
  - 2014 route 26 circular: clean English text with a numbered fare-stage list. — [cir20143248.1814.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/circulars-orders/cir20143248.1814.pdf)
- **How new routes reach the ticket machines** (DTC IT circular, 8 May 2017).
  - New-route details go from the Traffic Dept to depots, then to the AFCS Implementing Agency, which enters them in the AFCS. "The new route becomes operable using ETMs only after that".
  - The Traffic Dept must give "Stop to Stop Kilometers" for all new routes.
  - Source: [585-636_1.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/circulars-orders/585-636_1.pdf)
- **Earlier timetable PDFs** (Oct 2025, Feb 2024, Dec 2025 versions) appear in search. — [destination bus services Oct 2025](https://dtc.delhi.gov.in/sites/default/files/2025-10/destination_bus_services_oct_2025.pdf); [all DTC time table Dec 2025](https://dtc.delhi.gov.in/sites/default/files/DTC/dtc_all_time_table_dec_2025_0.pdf)

**Transport Department**
- **Public notice "Introducing New Bus Routes (Public Transport)"** (STA Branch).
  - It is the DIMTS route-rationalisation study, commissioned by Cabinet Decision 2534 of 19.12.2017.
  - New routes were to run "on trial run with 50% deployment of buses from 2nd October, 2022".
  - 25 pages; table columns: Route No., Origin, Destination, Via Stops (major stops only); English only.
  - Source: [public_notice_route_rationalization.pdf](https://transport.delhi.gov.in/sites/default/files/Transport/circulars-orders/public_notice_route_rationalization.pdf)

**DIMTS (cluster buses)**
- **OSM import plan.** The planned OSM import of DIMTS stops and routes names businfo.dimts.in (stops per route) and dimts.in (route list) as sources.
  - DIMTS's RTI reply says "The aforementioned information is available in public domain".
  - The fields requested were name, coordinates and shelter/bench/wheelchair/tactile status.
  - The plan was at "planning stage" on 10 July 2025; the page was last edited 11 July 2025.
  - Source: [OSM wiki Delhi/Buses/Import/Plan](https://wiki.openstreetmap.org/wiki/Delhi/Buses/Import/Plan)
- **Site status on 16 Nov 2026** (local check): businfo.dimts.in did not respond (no HTTP status), while www.dimts.in answered 200. DIMTS was being wound into DTC from April 2026 (sibling note `delhi_ops.md`).

**Bus queue shelters (DTIDC / Transport Dept)**
- **Counts.** "4,627 notified bus queue shelter locations according to a 2007 Gazette notification, but only 2,021 are operational". These are 250 old DTC shelters, 1,580 stainless-steel and 191 mild-steel shelters (MP/MLA LAD-funded).
- **Plan.** 2,856 new shelters under PPP: 1,397 surveyed and 1,459 proposed for a later phase. Figures from a DTIDC proposal.
- No location list is mentioned.
- Source: [The Week/PTI, 23 Jul 2025](https://www.theweek.in/wire-updates/national/2025/07/23/des81-dl-bus-shelter.html)
- A 2019 report says there was "no data" on how many such stops exist. — [Daily Pioneer 2019](https://www.dailypioneer.com/2019/state-editions/bus-commuters-fear-physical-risk--courtesy-undesignated-bus-shelters.html)

**data.gov.in and OpenCity**
- **data.gov.in.** Searches found no Delhi bus-stop, route-stop or BQS dataset. The relevant OGD resources are the pincode directory and the LGD village lists (Section 3).
- **OpenCity.** Hosts "Delhi DTC Bus Operational Data 2018 to 2022" (operational statistics from the Economic Survey, no stops). — [OpenCity](https://data.opencity.in/dataset/delhi-economic-survey-2023/resource/delhi-dtc-bus-operational-data-2018-to-2022)

**Hindi names**
- The DTC workbook, the DEVI fare-stage PDF and the English circulars contain no Devanagari [local check].
- Hindi circulars exist but use legacy fonts, as the route 410 sample above shows.
- English and Hindi searches in the sibling note found no bilingual DTC stop list. — `../停留所名の照合と通過検出/indic_name_matching.md`

### Inferences
- **The DTC workbook is effectively the ticketing vocabulary for DTC routes.** 99% of the unmatched DTC-route ends are in it verbatim. It shares typos with the tickets: the workbook's "Laxmi Bai Collage" and the ticket "L.S.R. Collage" from the sibling note. And the 2017 circular shows the ETM/AFCS route master is keyed in from Traffic Dept route sheets.
- **Recommended use: align, then join.** Align each workbook route-direction with the v32 pattern (Needleman–Wunsch on normalised names, anchored by exact matches; see `transit_stop_matching.md` §1). Every ticket name then gets a v32 stop_id, or a bracket of 1–5 candidate stops for about half of today's unmatched ends.
- **Use its fare-stage markers too.** They give the stage count between boarding and alighting, which can be checked against the fare slab.
- **Watch the "Diversion" sheet.** It holds alternative sequences; keep them as additional patterns.
- **Version it.** The workbook's Last-Modified (7 Oct 2026) is days before the October 2026 ticket month, and v32's zip members are dated the same day. Treat the workbook as time-varying and keep a dated copy.
- **Cluster routes are the residual problem.** The workbook covers few DIMTS routes, and businfo.dimts.in is gone. For them, use the 2022–24 GTFS (57% of their unmatched names) plus OSM and the GPS-alias method.
- **Circulars are a secondary, manual source.** Apart from the workbook, they are useful for routes changed after Oct 2026 and for harvesting variant spellings. Fare-stage circulars from 2012–2015 are mostly obsolete.

### Gaps
- **No public cluster route master.** No public route-wise stop list for DIMTS cluster routes after businfo.dimts.in went offline. The DIMTS "operational routes PDF" mentioned in the RTI reply was not located.
- **No BQS list.** No published list of BQS locations (PWD, DTIDC or Transport Dept), and no DTIDC dataset was found. The 2007 Gazette notification of 4,627 locations was not located.
- **No official Hindi stop list** found.
- **Two workbook sheets not parsed.** "U-SPL" and "DS" use a different layout, so their counts are not in the totals above.
- **Remaining unmatched ends.** Why 17% of unmatched ends are not on the workbook's route of the same name was not investigated. Likely causes: route-name formatting ("No.922", "STL", "+/−"), DIMTS routes, diversions.

---

## 3. Gazetteers for aliases and geocoding: OpenStreetMap, Wikidata, GeoNames, India Post, Census 2011 / LGD, DMRC

### Takeaway
- **OSM** is the richest open gazetteer for Delhi: 47,409 named features, 4,805 with `name:hi`, 2,354 `alt_name`, 906 `short_name`, 333 `old_name`, 201 `official_name`; ODbL; queryable without login. It is the best general-purpose source for landmark aliases and coordinates.
- **Wikidata** adds Hindi labels and English aliases for about 1,300 and 1,900 items in the Delhi box, CC0. Its coverage is mostly hotels, fuel stations, bank branches, settlements and metro stations (235/236 metro stations have Hindi labels); there are no bus stops.
- **GeoNames** (CC BY 4.0) and **India Post** (GODL, PO-level coordinates of unknown quality) are coarse.
- **Census 2011 / LGD** give authoritative village names (about 112 Delhi villages, including Kalan/Khurd pairs) but no coordinates or local-script names that I could confirm.
- **For metro-station names in English and Hindi**, OSM and Wikidata are better than the OTD DMRC download.

### Cited Findings
**OpenStreetMap**
- **Overpass counts for the Delhi admin area** (`ISO3166-2=IN-DL`; OSM data as of 2026-11-16T06:13:16Z):

  | Elements (nodes + ways + relations) | Count |
  |---|---|
  | with `name` | 47,409 |
  | with `name:hi` | 4,805 |
  | with `name:en` | 1,243 |
  | with `alt_name` | 2,354 |
  | with `old_name` | 333 |
  | with `official_name` | 201 |
  | with `short_name` | 906 |
  | with `loc_name` | 28 |
  | `place=*` with name | 1,120 (303 with `name:hi`, 137 with `alt_name`) |
  | `amenity=*` with name | 9,378 (546 with `name:hi`) |
  | `railway=station` with name | 267 (249 with `name:hi`) |
  | with `wikidata` | 1,247 |

  Data © OpenStreetMap contributors, ODbL. — [Overpass API](https://overpass-api.de/); [OSM copyright](https://www.openstreetmap.org/copyright)
- **taginfo for all India** (Geofabrik, data until 2026-11-15T21:10:59Z): `highway=bus_stop` 38,611; `public_transport=platform` 39,224; `name:hi` 71,773 (last edited by 2,412 users); `alt_name` 37,817; `short_name` 12,359; `old_name` 5,373. — [taginfo India](https://taginfo.geofabrik.de/asia:india/keys/name:hi)
- **Bulk download.** Geofabrik's India Northern Zone extract is 214 MB PBF, with data up to 2026-11-15T21:22:28Z (not downloaded). — [Geofabrik northern zone](https://download.geofabrik.de/asia/india/northern-zone.html)
- **Bus-route mapping on OSM.** It is still partial: 83 DTC routes are tracked, last edited 4 Jun 2024 (sibling note). — [OSM wiki Delhi/Buses](https://wiki.openstreetmap.org/wiki/Delhi/Buses)

**Wikidata** (my WDQS queries, 16 Nov 2026; CC0 — [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing); [WDQS](https://query.wikidata.org/))
- **Items located in Delhi (P131+ of Q1353)**: 3,045. Of these, 334 have a Hindi label, 237 an English alias, 65 a Hindi alias, 744 coordinates. Only 8 are "village in India" (Q56436498), 2 of them with Hindi labels.
- **Items with coordinates in the box 28.40–28.89 N, 76.83–77.35 E** (includes inner NCR):
  - 4,588 items; 1,279 with a Hindi label; 1,933 with English aliases; 175 with Hindi aliases.
  - Metro stations (Q928830): 236, of which 235 have Hindi labels. "Village in India": 74 (33 Hindi). Bus stops (Q953806): 0.
  - Top classes: hotel 955, gas station 614, HDFC Bank branch 397, human settlement 371, metro station 236, elevated station 176, school 120, college 102.
- **Two queries timed out** (metro/bus-stop counts via P131+); the box queries above replaced them.

**GeoNames** (CC BY 4.0: "This work is licensed under a Creative Commons Attribution 4.0 License") — [GeoNames dump readme](https://download.geonames.org/export/dump/readme.txt)
- **IN.zip** is 15,755,152 bytes, last modified 16 Nov 2026 03:50 GMT. It contains the `geoname` table with an `alternatenames` column (comma-separated) and `admin1 code`.
- **alternateNamesV2.zip** is 205,203,420 bytes, 16 Nov 2026. It carries per-name `isolanguage`, including `hi`, `abbr`, `wkdt` (Wikidata id) and `link`.
- Neither was downloaded (over 5 MB). — [IN.zip](https://download.geonames.org/export/dump/IN.zip); [alternateNamesV2.zip](https://download.geonames.org/export/dump/alternateNamesV2.zip)

**India Post pincode / post-office directory** (Department of Posts, data.gov.in, GODL-India)
- **Size and fields.** 157,087 rows for all India. Latitude/longitude are "source-provided" and blanked where the source held placeholders such as (1.0, 1.0) or "NA". The `accuracy` field is "Not populated".
- **Availability.** "data.gov.in itself was unreachable on 2026-10-03". A GitHub republication was used instead.
- Source: [datahub.io migration notes](https://datahub.io/logistics/postal-codes-in/.migration-notes)
- **Mirrors.** AIKosh and the CivicDataLab CKAN list the same "All India Pincode Directory"; a 2015 Open Data Index entry said early versions had no coordinates. — [AIKosh](https://aikosh.indiaai.gov.in/home/datasets/details/all_india_pincode_directory_till_last_month_1.html); [OKFN 2015 index](https://2015.index.okfn.org/place/india/postcodes)
- **Access.** The data.gov.in API itself needs a registered API key (the OGD platform's normal access model, described in a community.data.gov.in post on the `datagovindia` package, search excerpt). — [community.data.gov.in](https://community.data.gov.in/?p=113873)

**Census 2011 / LGD (villages and towns)**
- **Village count.** "112 villages for Census 2011 out of which 105 are inhabited" (Delhi Economic Survey, search excerpt). — [Delhi Planning Dept, ESD 2014-15 ch.17](https://delhiplanning.delhi.gov.in/sites/default/files/Planning/2016-17/2014-15/esd_2014-15_tb-ch-17.pdf)
- **Census tables.** ORGI Census 2011 tables list villages with codes, e.g. "Mundhela Kalan | 07 097 0006 064007 | VILLAGE" (search excerpt). — [Census NADA catalog 40776](https://new.census.gov.in/nada/index.php/catalog/40776)
- **OpenCity copy.** "Delhi Villages Census Data With Amenities – 2011". — [OpenCity](https://data.opencity.in/dataset/delhi-census-2011-data/resource/delhi-villages-census-data-with-amenities---2011)
- **LGD official downloads.** "All Villages of a State" and similar, as PDF/HTML/XLS/ODT, behind a captcha. data.gov.in also has an "LGD – Villages" resource, and a third-party full dump exists. Local-language name fields were not confirmed. — [LGD download page](https://lgdirectory.gov.in/downloadDirectory.do); [data.gov.in LGD villages](https://www.data.gov.in/resource/local-government-directory-lgd-villages); [planemad/india-local-government-directory](https://github.com/planemad/india-local-government-directory)

**DMRC station names**
- **OTD DMRC static.** 262 stops, 2023-08-10; same purpose-form gate as the bus data. — [OTD DMRC static](https://otd.delhi.gov.in/data/staticDMRC/)
- **Hindi coverage elsewhere.** Wikidata: 235 of 236 metro stations in the Delhi box have Hindi labels. OSM: 249 of 267 named railway stations in Delhi have `name:hi` (counts above).

### Inferences
- **Alias harvesting from OSM.** Pull all Delhi features with any of `alt_name`/`short_name`/`old_name`/`official_name`/`name:en`: up to about 5,000 features (2,354 + 906 + 333 + 201 + 1,243 tag instances, some on the same feature). Index every variant to the feature's coordinate. Then use only those within about 300–600 m of the ticket's route (the sibling note measured 78–93% of same-key cases within 400–600 m).
- **Hindi-pivot matching.** OSM `name:hi` (4,805) + Wikidata Hindi labels (1,279) + metro Hindi names could support it, but only for landmarks. Delhi bus stops themselves rarely have Hindi names (228 of 2,421, sibling note).
- **Wikidata.** Helps mostly with institution acronyms (hospitals, colleges) and metro stations; its aliases need checking because many items are commercial POIs.
- **GeoNames and India Post.** Low priority for stop-level location. Typical precision is locality/PO level, India Post coordinates have known placeholders, and the full files exceed what is needed. Use them only for village/colony names that no stop source covers, as a coarse "which part of the route" hint.
- **Census/LGD.** Useful as a canonical spelling list for village tokens (Kalan/Khurd, Gaon/Village), not for coordinates.

### Gaps
- **GeoNames** feature and alternate-name counts for Delhi (admin1 07) were not measured: IN.zip is 15.8 MB, and the web search page needs interaction.
- **India Post** row count and coordinate quality for Delhi POs were not measured, because data.gov.in was down in October 2026 per the mirror.
- **LGD** local-language name fields and Delhi village/town counts were not verified, since the download needs a captcha.
- **OSM `ref`/`ref:dtc` tags** on Delhi bus stops were not counted. Such codes, if present, could link to operator codes.
- **NCR towns** (Gurugram, Noida, Ghaziabad, Faridabad, Bahadurgarh, Sonipat) were not counted separately in OSM; the Overpass area was NCT Delhi only.

---

## 4. Community and academic datasets: GitHub, Kaggle, IIIT-Delhi, Chartr / One Delhi, IUDX, and other Indian GTFS feeds

### Takeaway
Community datasets add little beyond the archived GTFS:
- IIIT-Delhi's benchmark (bus-data.github.io, 2019) is the 2018 OTD lineage (543 routes, 3,464 stops) plus 10-second GPS;
- the Transitland mirror is archived;
- no Kaggle or scraped DTC stop list was found;
- Chartr and One Delhi publish nothing beyond what Transport Stack lists;
- IUDX has no Delhi bus data;
- no other Indian GTFS has Hindi translations. BMTC (Kannada) and Kochi Metro (Malayalam) have `translations.txt`, useful only as models.

### Cited Findings
- **IIIT-Delhi benchmark** (arXiv 1910.08903, 2019). "Static and Dynamic data for buses operating in Delhi". The dynamic data covers 543 routes and 3,464 stops, GPS "sampled every 10s"; three months of dynamic data were stored separately. Database at bus-data.github.io. — [arXiv 1910.08903](https://arxiv.org/abs/1910.08903)
- **GitHub.**
  - transitland/gtfs-archives-not-hosted-elsewhere (Delhi zip, archived 19 Mar 2026; Section 1).
  - transport-stack/ondc-buses-seller (code only, no stop data).
  - A notebook project "Delhi-Transport-Analysis" reads OTD GTFS (search excerpt). — [uithub mirror](https://uithub.com/Ali1Azam/Delhi-Transport-Analysis)
  - No scraped DTC stop or route CSV was found in GitHub or Kaggle searches.
- **DataMeet.** A mailing-list thread on OTD Delhi exists (not opened). — [DataMeet group](https://groups.google.com/g/datameet/c/exEoW8aGHu0)
- **Chartr.** Says its GTFS editor covers "6,800+" Delhi stops, and that it built India's first open GTFS for Delhi buses (DTC and DIMTS). These are vendor claims, from the sibling notes. — [Chartr GTFS](https://chartr.in/products/gtfs/); [Chartr Transport Stack](https://chartr.in/products/transport-stack/)
- **IUDX** (MoHUA/IISc). Its 2021 deployment deck lists bus occupancy/ETA use cases in Surat and Bhopal; no Delhi bus dataset was found. — [IUDX deployment deck, Apr 2021](https://iudx.org.in/wp-content/uploads/2021/05/IUDX-Deployment-April21-TSC.pdf)
- **Other Indian GTFS in the MDB catalogue** (13 Nov 2026), feeds with a "Translations" feature:
  - BMTC unofficial (mdb-2595, Vonter/bmtc-gtfs)
  - Kochi Metro (tld-1031)
  - None have Hindi.
  - Other Indian feeds, e.g. Indian Railways (unofficial, mdb-2867) and Chennai (mdb-3360), list no translations.
  - Source: [MDB catalogue CSV](https://files.mobilitydatabase.org/feeds_v2.csv)

### Inferences
- **IIIT-Delhi benchmark.** It is a copy of the 2018 lineage, so it adds nothing for names beyond the MDB 2018 zip. Its GPS could help only for historical DIMTS routes.
- **Other cities' feeds.** For a Hindi normalisation dictionary, they add nothing; Delhi's own Hindi sources are OSM `name:hi`, Wikidata and DMRC. BMTC's `translations.txt` is a good template if the team publishes Hindi names back into GTFS.

### Gaps
- **bus-data.github.io** was not opened, so its licence and current availability are unverified.
- **Kaggle** was searched only through a web search engine, not Kaggle's own search, which needs an account for some features.
- **IUDX's live catalogue** was not browsed. The finding rests on its 2021 deck and search results.

---

## 5. Ranking the sources for (a) aliases and variant spellings, (b) locating names that are not in GTFS, (c) recovering stop codes; consolidated inventory

### Takeaway
- **(a) Aliases and variant spellings:** the DTC fare-stage workbook first, by far, because it *is* the ticket vocabulary and gives route order. Then the 2018 and 2022–24 GTFS (old spellings with coordinates), then OSM name variants, DTC circulars and Wikidata.
- **(b) Locating names not in GTFS:** older-GTFS coordinates first (63% of unmatched ends placed within 400 m of their route). Then the workbook's stop order (about 49% bracketed to at most 5 candidate stops), then OSM POIs. GeoNames, India Post and Census are coarse fallbacks.
- **(c) Recovering stop codes:** only the archived 2018/2022–24 GTFS have operator-style codes (U…/DC…), and they can be attached to 39% of v32 stops by name + 50 m. The ticket codes (`start_stop_code` / `end_stop_code`) live only in the ONDC seller database and must be requested.

### Cited Findings
**Ranking table.** Evidence is in Sections 1–4; "local" figures are my checks on the team data.

| Rank | (a) Aliases / variant spellings | (b) Locating names not in GTFS | (c) Stop codes |
|---|---|---|---|
| 1 | **DTC "All Route Fair Stages" xlsx**: 91.6% of unmatched ends' names in it; 99.0% on DTC routes ([DTC](https://dtc.delhi.gov.in/sites/default/files/DTC/master_data_all_route_fair_stages_1.xlsx); local) | **Older GTFS 2018 + 2022–24** (coordinates): 63.2% of unmatched ends on v32 routes placed within 400 m of the route ([MDB mdb-1262](https://mobilitydatabase.org/feeds/gtfs/mdb-1262); local) | **Older GTFS 2018 + 2022–24**: U/DC codes; 3,577 shared 2018→2023; inheritable by 39% of v32 stops by exact name within 50 m (local) |
| 2 | **Older GTFS** (old spellings + coordinates): names present for 61% of the ticket ends whose name is absent from v32 (local) | **DTC workbook stop order** + v32 anchors: 48.7% of unmatched ends bracketed to ≤5 v32 stops, 21.5% to ≤2 (local) | **Ask the organisers / Chartr for the ONDC seller's `stops_new` (code, name, route_id)**: the only source of the ticket codes ([seller code](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py)) |
| 3 | **OSM** `alt_name` 2,354 / `short_name` 906 / `old_name` 333 / `official_name` 201 / `name:en` 1,243 (overlapping, up to about 5k features), `name:hi` 4,805 ([Overpass](https://overpass-api.de/)) | **OSM named POIs** (47k named, 9.4k named amenities) filtered to about 600 m of the route | v32 `stop_code` (8-hex, unique per stop, but not linked to older or seller codes) (local) |
| 4 | **DTC circular PDFs**: within-document variants; 2026 English tables extract cleanly ([2664.pdf](https://dtc.delhi.gov.in/sites/default/files/DTC/circulars-orders/2664.pdf)) | **DTC "DS" sheet km readings** (destination services only) and circular "stop to stop km": distance along route ([2017 IT circular](https://dtc.delhi.gov.in/sites/default/files/DTC/circulars-orders/585-636_1.pdf)) | — (no other public code source found) |
| 5 | **Wikidata** labels/aliases (1,933 items with English alias, 1,279 Hindi labels in the Delhi box) ([WDQS](https://query.wikidata.org/)) | **Wikidata coordinates** (4,588 items in the box; few stops) | — |
| 6 | **GeoNames** alternatenames; **Census/LGD** village spellings; **India Post** PO names | **GeoNames / India Post / Census** (coarse; India Post coordinates have placeholders) ([datahub notes](https://datahub.io/logistics/postal-codes-in/.migration-notes)) | — |

**Consolidated inventory** (state on 16 Nov 2026). "Code / EN / HI / Alt / XY / Route-stage" = stop code, English name, Hindi name, alternate names, coordinates, route or fare-stage membership.

| Source (publisher) | URL | Fields: Code / EN / HI / Alt / XY / Route-stage | Size & coverage | Licence; login/key | Last update |
|---|---|---|---|---|---|
| GTFS v32 (Transport Stack / Chartr; team copy) | [delhi.transportstack.in](https://delhi.transportstack.in/data-services) | 8-hex code / yes / no / "A / B" joined names / yes / routes + `fare_stage` on 1,214 routes | 6,862 stops, 2,574 route-dirs; zip 30.1 MB | Transport Stack terms (not checked); catalogue access not verified | zip members 2026-10-07 |
| OTD static bus GTFS (Transport Dept + IIIT-D) | [otd.delhi.gov.in/data/static](https://otd.delhi.gov.in/data/static/) | U/DC codes / yes / no / no / yes / routes, no stages | 3,464 active stops, 543 routes (= 2018 content) | Proprietary DoT terms; purpose pop-up, no login | page says 2024-06-20; content 2018 |
| MDB mdb-1262 2018 dataset (mirror of OTD) | [zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202406071502/mdb-1262-202406071502.zip) | same as above | 8,374 stops (3,202 used), 543 routes; 2.9 MB | Licence URL given as opendata.iiitd.edu.in/terms; no login | service window Nov 2018 |
| MDB mdb-1262 / mdb-3139 2022–24 dataset (Transitland mirror) | [zip](https://files.mobilitydatabase.org/mdb-1262/mdb-1262-202506170152/mdb-1262-202506170152.zip) | U/DC codes (1,768 blank) / yes / no / no / yes / routes, no stages | 6,342 stops, 2,964 routes, 78,507 trips; 19.8 MB | as above; no login | service 2022-01-01 to 2024-01-01 (Feb 2023 download) |
| DTC "All Route Fair Stages" workbook | [xlsx](https://dtc.delhi.gov.in/sites/default/files/DTC/master_data_all_route_fair_stages_1.xlsx) | no / yes / no / spelling variants across routes / no / full stop order + fare stages; km in DS sheet | 733 routes, 1,415 route-dirs, 93,613 rows, 7,966 names; 2.8 MB | DTC website (no licence stated); no login | 2026-10-07 |
| DTC timetables, DEVI fare-stage PDF, U-Special & Express xlsx | [services page](https://dtc.delhi.gov.in/dtc/services-and-time-table) | no / yes / no / – / no / route termini, some stages | 0.02–1.3 MB each | DTC website; no login | Dec 2022 – 10 Nov 2026 |
| DTC circulars (9 listings) | [general-circulars](https://dtc.delhi.gov.in/general-circulars) | no / yes (EN PDFs) / Hindi in legacy fonts / variants / no / fare stages per route | 1,518 files; about 200+ fare-stage circulars, mostly 2012–15 | DTC website; no login | to 2026 |
| Transport Dept route-rationalisation notice | [PDF](https://transport.delhi.gov.in/sites/default/files/Transport/circulars-orders/public_notice_route_rationalization.pdf) | no / yes / no / – / no / origin, destination, via stops | 25 pages | Govt notice; no login | 2022 (trial from 2 Oct 2022) |
| DIMTS businfo (cluster stops per route) | [businfo.dimts.in](https://businfo.dimts.in/) | unknown | unknown | RTI: "public domain" | offline on 2026-11-16 |
| BQS (DTIDC / Transport Dept) | [The Week](https://www.theweek.in/wire-updates/national/2025/07/23/des81-dl-bus-shelter.html) | no public list | 4,627 notified / 2,021 operational | – | Jul 2025 article |
| ONDC seller stop tables (Transport Stack / Chartr) | [code](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py) | seller codes / yes / ? / ? / no (0.0) / route + sequence + fares | not public | Apache-2.0 code only | repo pushed 13 Aug 2026 |
| OpenStreetMap | [Overpass](https://overpass-api.de/) | `ref` not checked / yes / 4,805 `name:hi` / 2,354 alt, 906 short, 333 old, 201 official / yes / bus route relations partial | 47,409 named features in NCT; Northern Zone PBF 214 MB | ODbL; no login | live (2026-11-16) |
| Wikidata | [WDQS](https://query.wikidata.org/) | QIDs / yes / 1,279 Hindi labels in box / 1,933 with English aliases / 4,588 with XY in box / no | 3,045 items P131+ Delhi | CC0; no login | live |
| GeoNames | [IN.zip](https://download.geonames.org/export/dump/IN.zip) | geonameid / yes / via alternateNamesV2 `hi` / alternatenames / yes / no | IN.zip 15.8 MB; alternateNamesV2 205 MB | CC BY 4.0; dumps free (API needs a username) | 2026-11-16 |
| India Post pincode directory (Dept of Posts) | [datahub notes](https://datahub.io/logistics/postal-codes-in/.migration-notes) | pincode / PO names / no / no / PO-level lat/lon (placeholders blanked) / no | 157,087 rows all-India | GODL-India; data.gov.in API needs a key | 2026-10-03 mirror |
| Census 2011 village directory / LGD | [LGD download](https://lgdirectory.gov.in/downloadDirectory.do) | census/LGD codes / yes / not confirmed / no / no / no | 112 Delhi villages (105 inhabited) | GODL (OGD); LGD download behind a captcha | 2011 / live |
| OTD DMRC static | [OTD DMRC](https://otd.delhi.gov.in/data/staticDMRC/) | ? / yes / ? / no / yes / routes | 262 stations, 36 routes | DoT terms; purpose pop-up | 2023-08-10 |
| IIIT-D bus-data benchmark | [arXiv](https://arxiv.org/abs/1910.08903) | 2018 lineage | 543 routes, 3,464 stops + GPS | not verified | 2019 |
| BMTC (Kannada) / Kochi Metro (Malayalam) GTFS with translations | [MDB catalogue](https://files.mobilitydatabase.org/feeds_v2.csv) | translations.txt (not Hindi) | – | various | 2025–26 |

### Inferences
**Practical order of work, highest gain first:**
1. **Parse the DTC workbook and align it per route-direction to v32 patterns.** This yields a (route_dir, ticket-style name) → v32 stop_id crosswalk for DTC routes, which carry 89% of unmatched ends: 864,140 of 967,716.
   - Exact anchors already bracket half of today's unmatched ends to at most 5 stops.
   - With the sibling note's normalisation cascade as the similarity function, more anchors and tighter brackets are expected; this is not measured.
2. **Join older-GTFS names with coordinates.** Use them to place bracketed names on a specific stop, and to cover DIMTS routes and routes missing from v32.
   - Keep only coordinates within about 400 m of the ticket route.
   - Flag names whose old copies are more than 1 km apart (230 names) for review.
3. **Harvest OSM variants for the residual landmarks and acronyms.** Use Wikidata only for metro stations and institutions.
4. **Request the seller's `stops_new` / `stops_pair_new` export.** With codes, the problem becomes a key join; without it, U/DC codes from older GTFS are the best public code surrogate.

**Licensing caution.** The OTD terms prohibit modification or reuse "for any other purpose" without DoT permission. The DTC website files carry no licence statement. For a hackathon prototype this is normally tolerated, but say so in the deliverable. OSM (ODbL) needs attribution and share-alike for derived databases. Wikidata (CC0) and GeoNames (CC BY) are unproblematic.

### Gaps
- **Untested end-to-end gain.** The improvement from steps 1–2 to the team's exact/fuzzy/nearby/unmatched split was not measured. My numbers are coverage and bracketing rates with exact anchors, not verified matches.
- **Seller codes.** No public evidence links ONDC seller codes to U/DC codes or to v32 hex codes.
- **Workbook vs v32 dates.** Whether the 7 Oct 2026 workbook and the 7 Oct 2026 v32 zip came from one refresh is unknown.
- **Method note (reproduction).** Scripts live in the session scratchpad (`scripts/lineage_check*.py`, `parse_dtc_master.py`, `master_vs_tickets.py`, `master_bracket.py`, `agency_split.py`, `dtc_crawl.py`) and may be cleared. The public inputs can be re-downloaded from the URLs above.
