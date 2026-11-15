# Bus occupancy / crowding estimation from conductor-issued ticket (ETM) data — India and other developing-country systems

Research date: 2026-11-14. Scope: studies, deployments and data facts for using ETM / paper-ticket sales (boarding stop, fare stage, destination) to estimate bus load. Input to the Delhi Transport Stack Hackathon 2026 (Problem 2: crowding-aware bus journey planner; Phase 1 deadline 24 Nov 2026).

Overall finding up front: published, validated ETM-to-occupancy work for Indian city buses is thin. Most material is (a) planning/policy reports describing what ETM data contains and its errors, (b) a few academic demand/OD/forecasting papers (Trivandrum KSRTC, Bhubaneswar CRUT), and (c) agency audits. I found no paper reporting accuracy of ETM-derived occupancy against manual counts, APC or CCTV for an Indian city. Treat the methods below as "assemble from parts" rather than "copy a validated pipeline".

---

## Q1. What methods exist to convert fare-stage / zone-based tickets into alighting stop distributions (and to group tickets into vehicle trips)?

### Takeaway
Indian ETM tickets usually carry origin and destination as fare *stages* (urban average ~2 km per stage), sometimes as stops (Bhubaneswar records exact stops). Load profiles are built by treating each ticket as one boarding at its origin and one alighting at its destination, then distributing within-stage alightings over the stops in the destination stage (uniformly, by stop weights, or by a decay/prior pattern). No Indian paper I found validates the within-stage disaggregation step; the documented work stops at stage-level OD and load profiles.

### Cited Findings
- ETMs in Indian bus systems "record the route, time, origin, destination and fare for each trip" — [GIZ/Changing Transport, Roadmap for Data-driven Transformation of Indian Bus Systems (2021)](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Fare-stage structure: a route is divided into stages, each a group of nearby stops; fares are set between stages, not stops. "In urban settings, the average stage length is around 2 km and all stops within a given origin stage will have the same fare for all stops in a destination stage." — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Bhubaneswar (CRUT) records the exact origin and destination stop of each ticket; Trivandrum and a few other cities record only stages, "limiting its application for planning." — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Data quality: schedule-linked entries (route/shift/trip) are generally accurate because revenue is audited daily, and fare data is generally accurate, but "origin and destination information typically has significant errors as conductors don't have adequate time to enter the details in crowded buses." GPS-linked ETMs that auto-set the origin mitigate this partially, but still need manual route/shift/trip selection. Same location may be selected under different stop names by different conductors; duplicated ticket IDs occur. — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Trip/schedule matching problem: route numbers, schedules and IDs are "sometimes maintained separately by ETM and GPS vendors, who don't use the same nomenclature and unique ids"; multiple vendors produce different data structures. — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Transfers: Indian ETMs issue tickets only for the current bus/route, so each leg is a separate ticket (telescopic fares penalise transfers). Implication: ticket = single-leg boarding, no linked journey. — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Trivandrum KSRTC (Cyril, George, Mulangi, ICECDS 2017, publ. 2018): ticket transactions from 6 depots, 2010–2013; ~1 million passenger transactions per month; raw ETM text dumps processed (MATLAB / Python code) into fare-stage-level OD matrices; boarding/alighting at stops gives load rate / load profile. — [NITK IDR record](https://idr.nitk.ac.in/handle/123456789/8234); [IEEE Xplore 8390198](https://ieeexplore.ieee.org/document/8390198/); [ResearchGate](https://www.researchgate.net/publication/325983769_Electronic_ticket_machine_data_analytics_for_public_bus_transport_planning)
- Same team's time-series demand models on KSRTC ETM data: multiplicative Holt-Winters variants (with/without damping) outperformed additive ones; data mostly non-stationary. — [Open Transportation Journal 2019 (TOTJ-13-41)](https://www.benthamopen.com/contents/pdf/TOTJ/TOTJ-13-41.pdf); PhD thesis [Cyril 2019, NITK](https://idr.nitk.ac.in/handle/123456789/14484)
- Bhubaneswar: Shrivastava, Rawat, Agarwal (Public Transport 16(2), 2024) use 3 months of ticketing data to predict dynamic passenger counts (affinity propagation clustering of trip segments + LSTM per cluster). — found via search snippet; full text not read. [ResearchGate search hit](https://www.researchgate.net/publication/325983769_Electronic_ticket_machine_data_analytics_for_public_bus_transport_planning) (citation details from search summary, verify before quoting)
- Sri Lanka: method paper builds cumulative boarding/alighting by fare section from ticket information or counts under three data scenarios — (1) individual passenger records, (2) stop- or fare-section-level aggregates, (3) only total demand plus a past distribution pattern — used for revenue estimation. — [IEEE Xplore 9525713, "Methods to Estimate Bus Revenue from Passenger Boarding and Alighting Data: Case Study for Sri Lanka"](https://ieeexplore.ieee.org/document/9525713/)
- When only boardings exist (smart-card / tap-on systems), alighting must be inferred (trip-chaining heuristics, ML). — [Shenzhen alighting estimation, UCL Discovery](https://discovery.ucl.ac.uk/id/eprint/10195948/1/Alighting%20location%20estimation%20from%20public%20transit%20data%20%20a%20case%20study%20of%20Shenzhen.pdf); [AFC OD estimation](https://researchgate.net/publication/220787986_Estimating_a_Transit_Passenger_Trip_Origin-Destination_Matrix_Using_Automatic_Fare_Collection_System)
- Delhi cluster-bus ETM paper tickets capture ticket purchase time, boarding & alighting location, trip fare; the HVT framework lists ETM travel fields as "origin and destination stops, fare stage, time stamp, vehicle number, trip direction (up or down)". — [HVT/Transport-Links, Safe and Secure Public Transport in Delhi, final report (2024), Table 2 and §3.1](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)

### Inferences
- Practical pipeline for the hackathon: (1) map ticket route + direction + timestamp to a GTFS trip (nearest scheduled/observed trip whose time window covers the ticket time; use GTFS-RT vehicle positions from Problem 1 if a vehicle number is present); (2) map origin/destination stage to GTFS stop sequence ranges; (3) place boarding at the earliest plausible stop in the origin stage consistent with the ticket time (or uniform over the stage), alighting spread over the destination stage's stops (uniform or weighted by stop "attractiveness", e.g., stop-level boarding counts in the reverse direction as a symmetric-OD prior); (4) cumulative sum boardings − alightings along stop sequence = load per segment.
- Because O/D entries are error-prone when buses are crowded, the error is likely correlated with crowding itself — exactly the condition the hackathon wants to detect. Use fare amount (reliable) as a consistency check on stage distance and drop/repair tickets where fare ≠ stage-pair fare.
- If ticket time is the issue time (conductor issues after boarding), the issue stop drifts downstream in crowded buses; snapping origin to GPS position at issue time is better than trusting the conductor-entered origin.

### Gaps
- No Indian study found that validates fare-stage-to-stop alighting disaggregation against ground truth.
- Did not obtain the exact schema of the hackathon's October 2026 ETM/e-ticket CSV (README is linked from the hackathon page but not read here).
- Bhubaneswar LSTM paper accuracy metrics not obtained (full text not read).

---

## Q2. How are passholders and free riders (not in ticket data) accounted for?

### Takeaway
Most Indian ETM datasets omit concession pass users (students, elderly), who can be up to ~50% of demand; Delhi's free travel for women was historically recorded via pre-printed paper pink tickets (DTC) rather than ETM, and from 2026 is moving to a tap-on Pink Saheli NCMC card on the ETM. No published, validated expansion factor exists; any multiplier (e.g., the 1.35 used in a public hackathon repo) is an assumption.

### Cited Findings
- "Cities typically don't capture data on concessional pass travellers like students and elderly, who form up to 50% of the overall travel demand." Some cities mandate "zero value" tickets for pass users, but conductors find it hard to issue them in crowded hours. — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- Delhi: DTC buses have used pre-printed paper tickets since the ETMs (deployed 2016) were phased out in September 2022; cluster buses (DIMTS) have handheld ETMs. Pre-printed pink tickets (nominal Rs 10, issued free) are given to women. — [HVT Delhi final report 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- Delhi data by fare medium (HVT Table 2): paper ticket → route direction, fare, daily ridership by route and gender; ETM paper ticket (cluster only) → purchase time, boarding & alighting location, fare, ridership by route and gender; Metro card on bus → boarding only (one tap); One Delhi App → gender, QR ticket purchase incl. free pink ticket. — [HVT Delhi final report 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- MPD-2041 baseline: cluster bus data was not available to the authors, and "ticketing through ETM is not being enforced." — [DDA MPD 2041 Transport Baseline Report](https://online.dda.org.in/mpd2041dda/_layouts/MPD2041FINALSUGGESTION/Baseline_Transport_%20160721.pdf)
- Pink Saheli Smart Card (NCMC-based) replaces paper pink tickets; reported mandatory for free travel on DTC and cluster buses from 1 October (2026); riders tap on the ETM; eligibility Delhi residents aged 12+; ~19 lakh cards reportedly issued. Dates conflict across outlets (January 2026 projected; launch March; 18 Sept; 1 Oct mandatory). — [ThePrint](https://theprint.in/feature/delhis-free-bus-ride-scheme-address-proof-migrant-women/3060875/); [Zee Business](https://www.zeebiz.com/india/news-delhi-women-s-free-bus-travel-pink-saheli-smart-card-now-mandatory-check-new-rules-403353); [Elets eGov, Oct 2026](https://egov.eletsonline.com/2026/10/delhi-rolls-out-pink-saheli-smart-card-heres-how-to-get-one/)
- Chartr app pilot (Sept 2020, 14 days): 6% of all DTC+cluster tickets sold via the app, of which 79.4% were pink tickets. — [PMC article PMC10152222](https://pmc.ncbi.nlm.nih.gov/articles/PMC10152222)
- Fare-evasion / non-validator correction: a French method fuses AFC (ticketing) with partial APC coverage via a geostatistical model to give "unified occupancy" network-wide; abstract gives no accuracy numbers. — [arXiv 2403.05546](https://arxiv.org/abs/2403.05546)
- Sri Lanka (2010 survey): only about half of passengers normally ask for a ticket — ticket counts undercount riders. — [LIRNEasia Mobile2.0@BOP paper](https://lirneasia.net/wp-content/uploads/2010/06/Full-Paper-English.pdf)
- A public (third-party) GitHub repo for this hackathon uses a pass multiplier α_pass = 1.35 on ticket-derived load "to account for pink-ticket and student-pass riders"; its ETM data suite appears to be generated by a synthetic script (`generate_etm_5weeks_data.py`). Not an official or validated source. — [GitHub Aryanban/transport-stack-hackathon-2026](https://github.com/Aryanban/transport-stack-hackathon-2026)

### Inferences
- For the October 2026 data window, the Pink Saheli transition matters: if women's free rides were tap-recorded on ETMs from 1 Oct, they may appear in the ticket data (check a ticket-type / fare=0 field); if not, women's ridership (~33–44% of riders, see Q5) is missing and a route/time-varying expansion is needed. Inspect the data before choosing a multiplier.
- Reasonable expansion approach: expansion factor per route (or depot) and hour = official ridership (route-level daily figures from DTC/DIMTS or Economic Survey totals) / ticket count; if unavailable, a global factor bounded by published shares (women 33–44%, concession up to 50%). Be explicit that relative crowding ranking is more robust than absolute counts.
- For a journey planner, output crowding as ordinal levels (e.g., seats available / standing / crowded) rather than passenger counts — this reduces sensitivity to an unknown expansion factor.

### Gaps
- No Delhi-specific published share of pass holders (student/senior/disability passes) in bus ridership found.
- Unclear whether the hackathon's October 2026 ticket file includes Pink Saheli taps or pass validations.

---

## Q3. What accuracy has been reported vs manual counts / APC / CCTV?

### Takeaway
I found no published accuracy figure for ETM-derived bus occupancy vs ground truth in India or in the other developing-country systems searched. Only qualitative assertions (CAG says ETMs give "accurate" stop-wise load info) and upcoming APC pilots (BMTC) that plan to compare APC counts with ETM data.

### Cited Findings
- CAG performance audit of BMTC states ETMs give accurate information on stop-wise, route-wise passenger load, and that BMTC should have collected and periodically analysed ticketing data; load factors on ordinary buses 68–76.5% and premium 43.9–54.7% over 2017–20; passenger base fell 44.37 lakh (2017-18) → 33.10 lakh (2019-20). — [CAG audit report page](https://cag.gov.in/en/audit-report/details/121112); [CAG BMTC report PDF](https://d1jmc0u14z2tmp.cloudfront.net/uploads/download_audit_report/2024/BMTC-CAG-Report-English-0675eb03cefc943.49495445.pdf)
- BMTC plans an Automatic Passenger Counting pilot on 30 buses (another report: ADAS + APC on 80 buses), with APC counts to be compared against ETM data for passenger-load analysis and identifying overcrowding locations. No results found. — [Dainik Jagran English](https://english.dainikjagranmpcg.com/national/bmtc-to-introduce-automatic-passenger-counting-system-on-30-bengaluru/article-34912); [NewsFirst](https://newsfirstprime.com/bengaluru/bmtc-to-test-adas-and-passenger-counting-systems-on-80-buses-12618497)
- Bengaluru long-term bus plan uses 2019 BMTC ETM data for corridor ridership. — [Shakti Foundation Annex 3](https://shaktifoundation.in/wp-content/uploads/2022/01/Annex-3-Long-term-vision-plan-for-bus-operations-in-Bangalore.pdf)
- IoT prototypes in India (conductor handheld ETM + GPS → current/predicted occupancy) are student/conference-level with no rigorous validation; one paper argues camera/IR counting suits Indian conditions poorly. — [IJMET "Bus Track using IoT and Prediction Logic"](https://iaeme.com/MasterAdmin/Journal_uploads/IJMET/VOLUME_8_ISSUE_10/IJMET_08_10_012.pdf); [IoT PIS for Indian metros](https://www.researchgate.net/publication/321986229_IoT_based_passenger_information_system_optimized_for_Indian_metros)
- Ground-truth alternatives in developing countries are manual: Sri Lanka Western Province load factors from screen-line boarding/alighting surveys (load factor >1 most of the day on major corridors); Dhaka overcrowding study with stop-level load factors. — [Western Province, Sri Lanka (ResearchGate)](https://www.researchgate.net/publication/356296048_Analysis_of_Bus_Passenger_Demand_and_Supply_Case_Study_on_Western_Province_Sri_Lanka); [Dhaka overcrowding (ResearchGate)](https://www.researchgate.net/publication/270889809_Levels_of_Overcrowding_in_Bus_System_of_Dhaka_Bangladesh)
- Sri Lanka historic load factors (World Bank/PPIAF): public bus average load factor estimated 50% (1958) → 105% (1996); accurate loading statistics generally unavailable. — [PPIAF Urban Bus Toolkit, Sri Lanka case](https://www.ppiaf.org/sites/ppiaf.org/files/documents/toolkits/UrbanBusToolkit/assets/CaseStudies/full_case/Sri_Lanka.doc)

### Inferences
- The hackathon brief itself says estimates should be checked "against known peak and off-peak patterns" (see Q4), i.e., plausibility validation, not ground-truth accuracy. Teams can add internal validation: hold-out days, consistency between ticket-derived boardings and GTFS-RT dwell times, and sanity checks against known corridor peaks.
- Expect ETM-only occupancy to be biased low at peaks (conductors skip tickets / mis-enter stops when crowded; pass/free riders missing).

### Gaps
- No ETM-vs-APC/CCTV/manual accuracy figures found for India, Sri Lanka, Bangladesh, Kenya or Latin America. Kenya (matatu) searches returned nothing relevant; Latin American conductor-ticketing studies were not found in the searches made.
- A referenced "Bhandari et al. (2024)" ANN occupancy-at-stops paper using Delhi ETM data could not be located; existence unverified.

---

## Q4. Has IIIT Delhi or Chartr published work with Delhi ETM data? Past Delhi hackathons / open transit data events?

### Takeaway
IIIT Delhi (CSM, Pravesh Biyani) and Chartr have published mainly GPS/GTFS work (Open Transit Data portal, timetable benchmark dataset) and built contactless ticketing (Open Ticketing Framework / Chartr app); I found no published paper of theirs analysing Delhi ETM ticket data for occupancy. The 2026 Transport Stack Hackathon appears to be the first public release of Delhi ticket-level data.

### Cited Findings
- Open Transit Data (OTD) portal launched November 2018 by Delhi Govt (DDC + Transport Dept + IIIT-Delhi), publishing static and real-time GTFS. — [DDC Delhi, Open Transit Data Initiative](https://ddc.delhi.gov.in/our-work/6/open-transit-data-initiative)
- IIIT-Delhi CSM lists work with DTC on Open Transit Data and an "Open Ticketing Framework for contactless ticketing in buses". — [CSM IIIT-Delhi](https://csm.iiitd.ac.in/)
- Jain, Kumar, Balodi, Biyani (arXiv 1910.08903, 2019): benchmark dataset of real-time GPS data for 500+ Delhi bus routes collected over two months, used for timetable optimisation on two DTC routes — GPS, not tickets. — [arXiv 1910.08903](https://arxiv.org/pdf/1910.08903)
- IIIT-Delhi thesis "Applications of open transit data" (co-advised by Biyani): service breakdown detection and odd-even scheme analysis. — [IIITD repository](https://repository.iiitd.edu.in/jspui/handle/123456789/857)
- Chartr: runs AVLS tracking for 3,500+ DTC/DIMTS buses, publishes GTFS-RT and static GTFS (routes, stops, schedules, fares) via the Delhi Transport Stack. — [Chartr Transport Stack](https://chartr.in/products/transport-stack/)
- Chartr app contactless ticketing pilot 2020: 6% of tickets in a 14-day trial, 79.4% pink. — [PMC10152222](https://pmc.ncbi.nlm.nih.gov/articles/PMC10152222)
- Transport Stack Hackathon 2026: five problems on Delhi data (bus GPS, e-ticketing, ETM, metro AFC). Problem 2: crowdedness model from ~4–5 weeks of e-ticketing/ETM data ("ticket sales, routes and timestamps"), integrated into a journey planner; validate against known peak/off-peak patterns. October file: about 2.56 million tickets, 1–31 October 2026, one CSV (66 MB zip, 290 MB unpacked) with README and SHA256SUMS. Bus e-ticketing data "captures only 3–4% of bus tickets." Registration closes 20 Nov 2026; Phase 1 two weeks; finale 11 Dec 2026. — [delhi.transportstack.in/hackathon](https://delhi.transportstack.in/hackathon/)
- Earlier community/open-data activity: DataMeet threads on Delhi Open Transit Data and on bus/metro ridership data requests. — [DataMeet: Open Transit Data – Delhi](https://groups.google.com/g/datameet/c/exEoW8aGHu0); [DataMeet: Ridership of buses and metro](https://groups.google.com/g/datameet/c/4nKyIVbxz-w/m/ZyzTxieSBgAJ); a Smart India Hackathon transit repo exists ([subhamm-dmg/transit-sih](https://github.com/subhamm-dmg/transit-sih)), content not reviewed.
- Gender-disaggregated ticket data framework (HVT/Transport-Links 2024): describes how pink-ticket counts give route-level female ridership summed to system totals. — [HVT framework](https://transport-links.com/hvt-publications/framework-to-collect-and-analyse-gender-disaggregated-travel-data-from-public-transport-ticketing-systems/)

### Inferences
- 2.56 M tickets/month vs ~41 lakh daily riders (~125 M/month) ≈ 2% — consistent with the "3–4% e-ticketing" note. The released data is likely a small, app/QR/digital sample (possibly biased to smartphone users and certain routes), not the full conductor ETM stream. Crowding estimates must therefore be expanded (route × hour) and should emphasise relative patterns. Verify against the README.
- The third-party GitHub repo is not official and its data appears synthetic; do not cite its numbers as Delhi facts.

### Gaps
- No Chartr blog post or IIIT-D paper on ETM-based occupancy located. otd.delhi.gov.in pages were not fetched directly.
- Outputs/winners of earlier Delhi open-transit hackathons (e.g., 2018–2019 OTD events) not found.

---

## Q5. Known Delhi bus ridership patterns useful for validation

### Takeaway
Delhi bus ridership is ~41 lakh/day (2023) and falling; women's share rose from roughly a quarter/third to ~40%+ after free travel (Oct 2019). Reported peaks: morning ~9–11 am and evening ~5–7 pm (women on an e-bus route); students 7–8 am, 2–3 pm, 5–6 pm. Peak frequencies are poor (few routes ≤5 min headway), implying high peak loads.

### Cited Findings
- DTC+cluster daily ridership fell ~19% from 51.02 lakh (2019) to 41.41 lakh (2023). — [Scroll](https://scroll.in/article/1085059/why-the-number-of-bus-users-in-mumbai-and-delhi-has-plummeted)
- Economic Survey 2025-26 (via NewsBytes): DTC daily passengers 33.4 → 25.6 lakh; cluster 17.71 → 15.3 lakh over ~6 years. — [NewsBytes](https://www.newsbytesapp.com/news/auto/economic-survey-2025-26-finds-delhi-bus-ridership-down-nearly-20/story)
- DTC avg daily ridership ~2.5 million (2022-23); DTC fleet 4,346 (Dec 2023), cluster 2,841; e-buses 1,970 by July 2024. — [HVT Delhi final report 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- 606 bus routes: 259 DTC, 209 cluster, 138 shared. — [ICCT working paper 2025](https://theicct.org/wp-content/uploads/2025/04/ID-321-–-Neighborhood-transit-working-paper-A4-50163-WEB-v5.pdf)
- Peak service: <1% of DTC routes run every 5 min in morning peak; <25% every 15 min. — [CSE](https://www.cseindia.org/while-falling-metro-ridership-in-delhi-hogs-the-attention-massive-slide-happening-in-bus-ridership-as-well-finds-new-cse-study-8270)
- Women's share: 33% (2019) → 42% (2023) per one paper; official data cited by India Forum 25% (2020–21) → 33% (2022–23); OECD summary ~40%; Delhi Economic Survey cited as 33% → over 44%. Sources conflict (different denominators/years). — [Ideas for India](https://www.ideasforindia.in/topics/social-identity/fighting-gender-inequality-through-mobility-assessing-delhi-s-pink-ticket-scheme.html); [The India Forum](https://www.theindiaforum.in/forum/free-ticket-can-be-ticket-freedom); [OECD OPSI](https://oecd-opsi.org/?p=33567); [HVT report](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- Over 1,530 million pink tickets availed as of Feb 2024. A claim of "over 21 million pink tickets issued daily" (May 2023 DTC/DIMTS data) appears implausible vs ~41 lakh total daily riders — likely a monthly figure; treat as unverified. — [The Wire](https://thewire.in/women/what-delhis-pink-ticket-scheme-tells-us-about-womens-mobility); [Ashoka DP 105](https://dp.ashoka.edu.in/dp/RePEc/ash/wpaper/paper105_0.pdf)
- Route-level example (pilot e-bus route Inder Puri–Azadpur, Aug 2023): 7,652 passengers/day, 51% female; women's morning peak 9–11 am, off-peak use 11 am–3 pm, evening peak 5–6/7 pm; 77% of women cited peak-hour overcrowding in e-buses. Purpose peaks: students 07–08, 14–15, 17–18; work 10–11 and 17–19. — [HVT Delhi final report 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- WRI India: free travel let women save up to 8% (of income) and improved job access. — [ThePrint on WRI paper](https://theprint.in/india/governance/aaps-free-bus-ride-scheme-helped-delhi-women-save-up-to-8-get-access-to-better-jobs-wri-india-paper/2536921)

### Inferences
- Validation targets for a ticket-derived crowding model: AM peak ~8–11 and PM peak ~17–20 should dominate; weekday > weekend (no Delhi-specific weekday/weekend ratio found); women-heavy routes should show midday off-peak usage; system daily total after expansion should land near 40 lakh.
- Note October 2026 window includes festivals (Dussehra/Diwali season) which may distort weekly patterns — check calendar before using it as "typical".

### Gaps
- No published Delhi bus hourly ridership curve, busiest-corridor ranking, or weekday/weekend ratio found from ticketing/Chartr data.
- Chennai MTC, Mumbai BEST, Pune PMPML, Ahmedabad (AMTS/BRTS) ETM-based load studies were not found in the searches made (HVT notes Ahmedabad BRTS records origin/destination stops, fare stage, time, vehicle, direction and user type, but no load study). Kenya/Latin America conductor-ticket load studies not found.

---

## Practical takeaways for the hackathon (Phase 1 deadline 24 Nov 2026)
(Derived from the findings above; inferences, not cited facts.)
1. Read the official README first: confirm whether the file is e-ticket (app/QR) only or includes conductor ETM; check fields for vehicle number, trip/schedule ID, origin/destination stage vs stop, ticket type (pink/pass/zero-fare).
2. Trip assignment: route + direction + timestamp → GTFS trip; strengthen with GTFS-RT vehicle positions (Problem 1 data) when vehicle IDs are present.
3. Alighting: use the ticket destination; spread over destination-stage stops uniformly (baseline) and optionally weight by stop boarding volumes. Document as an assumption.
4. Expansion: route×hour factor to official totals (~40 lakh/day); report crowding as ordinal bands with uncertainty; don't hard-code an unsourced 1.35 pass multiplier without justification.
5. Capacity: normalise by bus type (seated vs standing capacity of DTC/cluster CNG vs e-bus) — capacity values not researched here; get them from fleet data.
6. Validation: plausibility against peak windows (AM 8–11, PM 17–20), weekday/weekend contrast, hold-out days; state clearly that no ground-truth counts exist in published literature.
