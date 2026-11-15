# Deployed crowding information services, crowding-aware journey planners, crowding prediction accuracy and crowding-aware routing

Scope: (a) deployed products, (b) academic prediction models, (c) crowding-aware routing and crowding multipliers, (d) communicating uncertainty. For a Delhi bus-only prototype built from ticket records and GTFS.
Research date: 2026-11-14. Note: most deployed-product evidence comes from 2019–2021 press releases and company blogs. There are very few independent accuracy audits.

---

## Q1. What accuracy do deployed crowding predictions achieve?

### Takeaway
Only a few deployed systems publish accuracy figures, and the companies report them themselves. They put category accuracy at roughly 80–88% against APC (automatic passenger counter) ground truth: Transit app with LA Metro about 88%, Transit app with Big Blue Bus about 80%. Google gives no number ("fairly high") and says accuracy drops when service runs off schedule. No independent audit of a consumer crowding product was found.

### Cited Findings
**Product inventory (data source / method / display / accuracy)**
- **Google Maps (2019 launch, about 200 cities).** It started from voluntary, anonymous rider ratings collected Oct 2018–Jun 2019. Riders rated trips on 4 levels, from "many empty seats" to "cramped, standing room only". Predictions later combined AI, rider contributions and historical Location History trends, with anonymization and differential privacy. Google's PM described accuracy as "fairly high" but gave no number. She noted that user-generated ratings are subjective ("everyone's idea of crowdedness could be different"). A spokesperson said predictions work best when vehicles run to schedule. — [PYMNTS 2019](https://www.pymnts.com/news/2019/transit-feature-crowded-trains/); [Techspot](https://www.techspot.com/news/80708-google-rolling-out-public-transit-crowdedness-predictions-google.html); [Techlicious](https://techlicious.com/blog/google-maps-public-transit-crowds)
- **Google Maps expansion (2020).** Crowdedness predictions were expanded to more than 10,000 transit agencies in 100 countries. Live, car-level crowdedness was piloted with agency data (LIRR, Transport for NSW) in New York and Sydney. — [Google blog "Navigate new normals"](https://blog.google/products/maps/new-normals-with-google-maps/)
- **Transit app (Montreal) with LA Metro.** Predictive crowding comes from historical APC/ridership trends processed by Transit's engineers. It was reported as **88% accurate compared with actual APC counts**. A second trade-press piece instead says "88% as accurate as real-time crowd counters", so the comparison baseline is ambiguous. — [Mass Transit "Occupancy Data: A Real Crowd Pleaser"](https://www.masstransitmag.com/technology/passenger-info/article/21154973/occupancy-data-a-real-crowd-pleaser)
- **Transit app with Big Blue Bus (Santa Monica, 2021).** Big Blue Bus shares stop-by-stop ridership statistics. Transit predicts each vehicle's capacity level along the route by time of day. "Four of every five capacity predictions … proven accurate when compared with actual ridership data" (about 80%). — [City of Santa Monica press release 2021-03-11](https://santamonica.gov/press/2021/03/11/big-blue-bus-pilots-predictive-crowding-levels-for-all-lines-in-transit-app); [Mass Transit](https://www.masstransitmag.com/technology/passenger-info/mobile-applications/press-release/21214519/big-blue-bus-big-blue-bus-pilots-predictive-crowding-levels-for-all-lines-in-transit-app)
- **Transit app crowdsourcing.** Riders using the "GO" navigator self-report crowding. A report appears for 10 minutes and temporarily overrides the trend-based prediction. It launched with 35 agency partners in 2020. — [Mass Transit press release](https://masstransitmag.com/home/press-release/21160934/transit-app-public-transit-riders-help-one-another-avoid-crowds-with-the-transit-app)
- **Moovit.** It combines crowdsourced self-reports with agency real-time feeds (more than 70 agencies). Where an agency feed exists, Moovit shows it instead of user reports. Android users can confirm or update other users' station crowding reports. VoiceOver and TalkBack read occupancy aloud. — [Moovit blog: How crowded is your bus](https://moovit.com/blog/how-crowded-is-your-bus-know-in-real-time-and-help-others-by-self-reporting/); [Moovit blog: Avoiding the crowd](https://moovit.com/blog/avoiding-the-crowd-know-before-you-go-with-the-moovit-apps-crowdedness-feature/)
- **TfL Go (London).** Station "busyness" originally came from Oyster/contactless entry and exit taps. In 2021 it switched to depersonalised **Wi-Fi** data, giving live busyness for stations, platforms and interchanges. London TravelWatch noted it does not cover individual trains. Bus crowding was a separate APC tender asking for boardings, alightings, onboard count and "loading as a percentage of capacity". No source confirms live bus occupancy in TfL Go. — [TfL press release June 2021](https://tigris.tfl.gov.uk/info-for/media/press-releases/2021/june/improved-real-time-tube-station-information-added-to-tfl-go); [Railway Gazette, Wi-Fi](https://www.railwaygazette.com/urban-rail/wi-fi-used-to-estimate-station-usage/59481.article); [London TravelWatch](https://www.londontravelwatch.org.uk/?p=31712); [UKAuthority, TfL APC plans](https://ukauthority.com/articles/tfl-plans-for-automated-bus-passenger-counting); [Route One, tender](https://www.route-one.net/bus/tfl-seeks-tenders-for-passenger-counting-solutions/)
- **Seoul (TOPIS / BIT).** **Bus crowding is computed from transit-card boarding and alighting taps** (Korea uses tap-on and tap-off) and sent in real time to bus information terminals and apps. It is shown in **3 levels: spacious / normal / congested** (여유 / 보통 / 혼잡). Subway Lines 1–8 use card data plus **onboard weight (load) sensors**. — [SmartToday (Korean)](https://www.smarttoday.co.kr/ko-kr/articles/24088); [Seoul Solution, TOPIS](https://seoulsolution.kr/en/node/2595); [TOPIS Bus Information System PDF](https://seoulsolution.kr/sites/default/files/vimeo/3.%20TOPIS%20Bus%20Information%20System.pdf)
  - *Most relevant analogue for Delhi:* crowding derived from ticketing taps rather than from dedicated sensors.
- **Japan.**
  - Tokyu Bus with NAVITIME (2021 pilot): infrared door sensors count boardings and alightings, and the bus NAVITIME app shows **3 levels**. Tokyu said it would verify guidance accuracy before full service, but no published verification result was found. — [乗りものニュース (trafficnews.jp)](https://trafficnews.jp/post/105257)
  - NAVITIME with Kanto Bus and others (Jan 2021): bus crowding estimated by **detecting passengers' smartphone Bluetooth signals**. — [iPhone Mania](https://iphone-mania.jp/news-351088/)
  - NAVITIME rail congestion prediction: station-to-station congestion is modelled from travel-demand (route-search) data plus on-site surveys, covering 54 Tokyo-area lines in the morning peak. — [NAVITIME presentation 2016](https://data.navitime.co.jp/pdf/presentation_20160715_01.pdf)
  - MLIT lists JR East among operators using **load-device (荷重装置) data** for congestion, and notes equipment and cost hurdles. — [MLIT PDF](https://www.mlit.go.jp/tetudo/content/001375655.pdf)
- **NS (Netherlands).** The NS app indicator is a forecast from historical data plus a weekly demand and rolling-stock forecast. The indicator does **not** account for events or weather. NS dropped real-time seat information after a 2013 trial because of sensor cost. NS reports a KPI of **seat availability at peak of 94.6% (2024) against a 95.5% target**. No forecast-accuracy metric is published. — [Treinreiziger.nl](https://www.treinreiziger.nl/geen-realtime-drukte-informatie-meer-bij-ns-treinen/); [NS Annual Report 2024, seat availability](https://www.nsannualreport.nl/annual-report-2024/activities-and-achievements-in-the-netherlands/operational-performance/seat-availability)
- **APC ground truth is itself noisy.** Port Authority of Allegheny County APC data often fails an internal consistency check (boardings should equal alightings per block). A vendor notes that APC type, boarding behaviour and maintenance strongly affect real-time APC quality and must be validated before go-live. — [arXiv 2112.06050](https://ar5iv.arxiv.org/html/2112.06050); [Syncromatics blog](https://syncromatics.com/blog/2020/passenger-crowding-tools-and-data)

### Inferences
- The accuracy figures of about 80–88% are **category-level hit rates** reported by the companies. They are probably measured on 3–4 coarse categories, which makes high accuracy easier to reach. A Delhi prototype should report its accuracy in the same way, as % correct category plus adjacent-category accuracy, so the numbers are comparable.
- Historical-pattern predictions (Transit, Google, NS) work for scheduled operation but degrade during disruptions or events. Google and NS both say so. A cheap fix is to flag low confidence when the bus is off schedule or on known event days.
- Seoul is the closest deployed precedent for "crowding from ticket data". Korea's tap-off makes alightings observable. In Delhi, paper or e-tickets probably record boarding and fare stage but **not alighting**, so alightings must be inferred (see Q2/Q3 notes and inferences).

### Gaps
- No independent or peer-reviewed accuracy evaluation of Google, Moovit or Citymapper crowding was found. Citymapper's method and accuracy were not found.
- Not retrieved: **Singapore LTA/SMRT** (e.g., MyTransport crowding, bus loading indicators), **Hong Kong** (MTR/KMB), **Stockholm SL** app crowding, **Deutsche Bahn** Auslastungsprognose (believed to be a 4-level forecast, but no source was retrieved), and **Tokyo Metro / JR East app** details. These are not covered here and the report writer should not assert specifics about them.
- No accuracy result was found for the Tokyu or NAVITIME bus pilots.

---

## Q2. What crowding categories and thresholds are standard? And what do academic prediction models achieve?

### Takeaway
The de facto data standard is GTFS-Realtime `OccupancyStatus`, an enum with values from EMPTY through FULL, plus `occupancy_percentage`. It is still marked experimental, and the levels are not linear. Consumer apps collapse it to **3–4 levels** (seats available / few seats or standing / crowded or full). In the research and planning literature, the physically meaningful threshold is **standing density**: about 4–5 standees/m² signals discomfort. TCQSM uses load-factor bands (≤0.5, ≤0.75, ≤1.0 of seats) and about 0.3–0.4 m² per standee. Academic APC-based models (LSTM, XGBoost, lasso/PLS) beat statistical baselines, but the abstracts reviewed give few headline numbers.

### Cited Findings
**Standards**
- **GTFS-RT `OccupancyStatus`:**
  - History: added as experimental in 2015, `occupancy_percentage` added in 2020, multi-car `CarriageDetails` added in Sept 2020, descriptions clarified in Feb 2021.
  - Values include EMPTY, MANY_SEATS_AVAILABLE, FEW_SEATS_AVAILABLE, STANDING_ROOM_ONLY, CRUSHED_STANDING_ROOM_ONLY, FULL, NOT_ACCEPTING_PASSENGERS (plus NO_DATA_AVAILABLE and NOT_BOARDABLE in later revisions).
  - Consumers "must not assume that the OccupancyStatus values follow a linear scale". `occupancy_percentage` is the linear measure, where 100 = the vehicle's total designed capacity.
  - Sources: [GTFS-RT revision history](https://gtfs.org/documentation/realtime/change-history/revision-history); [Google GTFS-RT reference](https://developers.google.com/transit/gtfs-realtime/reference.html); [MBTA GTFS-RT docs](https://github.com/mbta/gtfs-documentation/blob/master/reference/gtfs-realtime.md)
- **Agency variations exist.** TfNSW publishes numeric enum values and its own extensions. — [TfNSW forum](https://opendataforum.transport.nsw.gov.au/t/bus-occupany-status-values/444); [TfNSW GTFS-R spec v2 2025](https://opendata.transport.nsw.gov.au/sites/default/files/2025-09/TfNSW%20GTFS%20%20GTFS%20R%20Implementation%20Specification%20v2%20June%202025.pdf)
- **Tirachini, Hensher & Rose (2013) review.** Load factor says little about standing discomfort, and standees/m² is the better measure. "A standing density of four or five passengers per square metre is a very likely indicator of crowding discomfort." — [TR Part A review (typeset copy)](https://typeset.io/pdf/crowding-in-public-transport-systems-effects-on-users-2e50mw4fib.pdf)
- **Wardman & Whelan (2011)** also argue that the latest evidence should be expressed per standee/m² rather than as load factor. — [Transport Reviews 31(3), RePEc](https://ideas.repec.org/a/taf/transr/v31y2011i3p379-398.html)
- **TCQSM (3rd edition, as reproduced in a bus study):**
  - Seated load factor bands for LOS: A ≤0.50, B 0.51–0.75, C 0.76–1.00, with D–F for standing loads.
  - TCQSM standing space values: 0.4 m² per passenger (no body contact) and 0.3 m² (some body contact). These came from the rail section.
  - TCRP: dwell time rises about 0.63 s per passenger once occupancy exceeds a "critical occupancy" of 63% of total capacity.
  - Sources: [EASTS journal bus LOS paper](https://www.jstage.jst.go.jp/article/easts/13/0/13_1361/_article/-char/en); [TCQSM 3rd ed. (NAP)](https://www.nap.edu/read/14175/chapter/8); [TCQSM 4th ed. TRID](https://trid.trb.org/View/1893350)
- An AFC-based study of Rotterdam bus lines mapped loads to TCQSM LOS and found frequent LOS E/F in peaks. — [TU Delft repository](https://repository.tudelft.nl/file/File_0a74a4d5-e523-47e4-a624-c6393ae493e8)
- **Deployed display levels:**
  - Google: 4 levels, from many empty seats to cramped standing room only ([Techspot](https://www.techspot.com/news/80708-google-rolling-out-public-transit-crowdedness-predictions-google.html)).
  - Seoul: 3 levels ([SmartToday](https://www.smarttoday.co.kr/ko-kr/articles/24088)).
  - Tokyu/NAVITIME: 3 levels ([trafficnews](https://trafficnews.jp/post/105257)).

**Academic prediction models**
- **Talusan et al. (Nashville WeGo, about 17M APC observations, 2020–22):**
  - Models: an XGBoost trip-level model and an LSTM stop-level model for day-ahead and same-day **ridership level** (categorical) prediction.
  - Inputs: APC data combined with weather, traffic and calendar data.
  - Both beat a statistical baseline across the service day. The abstract gives no numeric metric.
  - The paper's main theme is cleaning noisy APC data.
  - Sources: [arXiv 2210.04989](https://arxiv.org/abs/2210.04989); [NSF PAR](https://par.nsf.gov/servlets/purl/10466147)
- **Zulqarnain et al.** Multitask learning predicts occupancy and delay jointly from GTFS, APC and spatio-temporal context. It is claimed to be more robust under sparse APC data than single-task models. — [NSF PAR 10466155](https://par.nsf.gov/servlets/purl/10466155)
- **Wood, Yu & Gayah (2023, IJTST).** Real-time occupancy of a given bus at downstream stops, from APC plus weather. Linear regression and random forest gave **similar** accuracy, so simple models are competitive. — [DOAJ](https://doaj.org/article/4b280ad3c60e4e7fa38fe2b9d75fa4cc)
- **Jenelius (2020, TR Part C 112, Stockholm bus line):**
  - Models: lasso and PLS regression for loads and alightings, plus a **probabilistic seat-allocation model** and bias correction.
  - Outputs: (1) P(get a seat on boarding), (2) expected standing time, (3) excess perceived travel time versus uncrowded.
  - Works with historical counts only, or with real-time AVL and counts added. Described as robust to data availability and "sufficiently early to be useful".
  - Sources: [WTR summary](https://www.worldtransitresearch.info/research/7934); DOI 10.1016/j.trc.2020.102647
- A 2026 arXiv preprint compares polygon-based and global ML models for bus occupancy. Results were not retrieved. — [arXiv 2605.00083](https://arxiv.org/pdf/2605.00083)

### Inferences
- **Recommended prototype categories:** map to the GTFS-RT enums so the output is standards-compliant. Seat capacity S and total capacity C are per bus type. Delhi's standard low-floor buses are commonly cited at about 35–40 seats and about 60–70+ total capacity, but this needs a local source.
  - Seats available: load / S < 0.75 → MANY_SEATS_AVAILABLE
  - Few seats: 0.75–1.0 → FEW_SEATS_AVAILABLE
  - Standing: S < load ≤ S + 2 standees/m² × standing area → STANDING_ROOM_ONLY
  - Crowded: up to about 4 standees/m² → CRUSHED_STANDING_ROOM_ONLY
  - Full: above that → FULL
  - Also publish `occupancy_percentage`.
- Jenelius's "seat probability + expected standing minutes" outputs are well suited to a planner. They are more decision-relevant than a level label, and they feed directly into a crowding multiplier (Q3).
- Evidence from Wood et al. and from Transit's historical-trend approach suggests a **historical mean or quantile by (route, direction, stop sequence, time-of-day bin, day type)** is a strong, defensible baseline. Gradient boosting is an optional upgrade.

### Gaps
- No RMSE, MAE or accuracy figures were obtained for Talusan, Zulqarnain or Jenelius. Full texts were not retrieved.
- The TCQSM bus-specific standing-area LOS table and 4th-edition changes were not confirmed.
- No source was found on inferring alightings from boarding-only tickets for crowding apps. Trip-chaining destination inference (Trépanier, Munizaga) is the standard approach in the AFC literature but was not retrieved here.

---

## Q3. How do crowding-aware planners trade off time against crowding, and what crowding multipliers are used?

### Takeaway
The standard method weights in-vehicle time by a **crowding multiplier** (perceived time = multiplier × in-vehicle time):
- Seated: about 1.0–1.2 (Wardman & Whelan mean 1.19).
- Standing: about 1.5–2.3 (Wardman & Whelan mean 2.32).
- Density-linear form: +0.18 per standee/m² (Singapore).
- Revealed-preference bus/tram estimate (NL): about 1.16 at seated capacity.

Routing then uses either generalized cost (a single criterion) or **McRAPTOR** with crowding as an extra Pareto criterion. Peer-reviewed field evaluations of crowding-aware routing apps are scarce. Simulation studies (BusMezzo) show load-balancing benefits.

### Cited Findings
**Multipliers**
- **Wardman & Whelan (2011)** meta-analysis of 17 British rail studies over 20 years: seated multiplier averages **1.19**, standing multiplier averages **2.32**. They recommend standee density as the metric. — [Transport Reviews via RePEc](https://ideas.repec.org/a/taf/transr/v31y2011i3p379-398.html); [WTR](https://www.worldtransitresearch.info/research/3863)
- **Tirachini et al. (2016, Singapore MRT):** the in-vehicle time multiplier **rises linearly by 0.18 per standing passenger/m²** (about 1.55 at 3/m², as reported in a secondary summary). — [Tirachini et al. 2016 TP PDF](https://lijunsun.github.io/files/papers/2016-TP-Crowding.pdf); [Springer 2023 review citing it](https://link.springer.com/10.1007/s11116-023-10420-1)
- **Hong Kong:** the in-vehicle time multiplier at full capacity is **1.72–1.98** depending on seat probability, as cited in a 2023 review. — [Springer s11116-023-10420-1](https://link.springer.com/10.1007/s11116-023-10420-1)
- **Yap, Cats & van Arem (2020, Transportmetrica A):**
  - Revealed-preference route-choice model on Dutch **urban tram and bus** smart-card data (OV-chipkaart).
  - The in-vehicle crowding multiplier is **1.16 when all seats are occupied**, and **1.31 for frequent travellers**.
  - Infrequent travellers appear not to account for expected crowding.
  - Sources: [WTR summary](https://www.worldtransitresearch.info/research/7671); [TU Delft repository](https://repository.tudelft.nl/record/uuid:f5b0c489-e359-4095-b49d-9f3cacccb2da)
  - *This is a bus-relevant RP value derived from ticket data.*
- **Santiago (Tirachini and co-authors):** bus and metro sitting and standing multipliers show significant heterogeneity by gender, age and income. — [White Rose eprint](https://eprints.whiterose.ac.uk/118336/1/Crowding_TT_trade_offv05.pdf)
- **Post-COVID valuations of crowding are more negative.** A 2023 paper says older multipliers may understate them. — [Springer 2023](https://link.springer.com/10.1007/s11116-023-10420-1)
- **Paris subway** discomfort–time trade-off, interval regression. — [EPFL Infoscience](https://infoscience.epfl.ch/record/204605/files/LapKon_2015.pdf?version=6)

**Routing and assignment algorithms**
- **RAPTOR / McRAPTOR (Delling, Pajor, Werneck, 2012/2015).** RAPTOR is round-based and returns the Pareto set of arrival time × transfers. McRAPTOR extends it to arbitrary extra criteria with label bags per stop. Pareto sets stay small in practice because the criteria correlate. — [Transportation Science 49(3)](https://pubsonline.informs.org/doi/fpi/10.1287/trsc.2014.0534); [KIT PDF](https://i11www.iti.kit.edu/extra/publications/dpw-rbptr-12.pdf)
- **The number of Pareto solutions grows superlinearly with the number of criteria**, which argues for keeping to 2–3 criteria. — [KIT thesis](https://publikationen.bibliothek.kit.edu/1000151245/149402295); [Route Planning survey arXiv 1504.05140](https://arxiv.org/pdf/1504.05140)
- **Open-source implementations:**
  - `pyraptor`: Python RAPTOR and McRAPTOR on GTFS. — [libraries.io](https://libraries.io/pypi/pyraptor)
  - Rust `vulture` example: a custom label (arrival time, per-route "badness" such as crowding). The Pareto front returns the fastest journey plus slower, less crowded alternatives. — [docs.rs vulture example](https://docs.rs/crate/vulture/latest/source/examples/custom_label.rs)
- **ChatPlanner (2026 arXiv preprint)** uses MC-RAPTOR with a per-stop crowding criterion and Pareto pruning. Its crowding values are **simulated** (normal distribution, normalized to [0,1]), not measured, so it is a weak evaluation. — [arXiv 2606.15315](https://arxiv.org/pdf/2606.15315)
- **BusMezzo and related simulation studies:**
  - Cats, West & Eliasson (2016, TR-B): a dynamic stochastic assignment with crowding. Static models miss crowding dynamics and understate the benefits of capacity. — [TU Delft PDF](https://pure.tudelft.nl/ws/files/11510486/Cats_et_al_TR_B_2016b.pdf)
  - Cats & Hartl (2016) compare BusMezzo, which captures the on-board crowding distribution, with VISUM. — [PDF](https://pure.tudelft.nl/ws/files/11605597/JoAT_Cats_and_Hartl_2016.pdf)
  - Drabicki, Kucharski, Cats & Fonzone (2017): BusMezzo extended with real-time crowding information (RTI-CL).
  - Drabicki, Kucharski & Cats (2023): RTCI used to mitigate bus bunching.
  - Source for the Drabicki papers: [KTH/TU Delft listing](https://repository.tudelft.nl/file/File_b1807af9-cd27-4574-9a95-5d22573ad014)

**Behaviour change evidence**
- **Stockholm metro RTCI pilot (Zhang, Jenelius & Kottenhoff, 2017).** Car-level crowding was displayed on platforms. There was a statistically significant shift in boarding between cars. **About 25% of passengers noticed, understood and found the information useful.** Many valued it even without changing behaviour. — [WTR 6591](https://www.worldtransitresearch.info/research/6591); [Public Transport 9(3), RePEc](https://ideas.repec.org/a/spr/pubtra/v9y2017i3d10.1007_s12469-016-0150-y.html)
- **Peftitsi, Jenelius & Cats (2022).** A simulation found that car-specific RTCI evens out load across cars. The benefit grows with demand only up to a point. — [WTR 9395](https://www.worldtransitresearch.info/research/9395)
- **Singh et al. (2023, NL stated choice).** Highly crowd-averse non-students would shift departure time given real-time crowding information. Others respond more to fare discounts. Flexible work hours are a prerequisite. — [TU Delft repository](https://repository.tudelft.nl/record/uuid:01c230b8-0abb-47bd-ae63-b2ea7f4da587)
- **Burger, Becker & Rossi (2023, UK rail).** Most respondents are highly crowding-sensitive, but a flexible subgroup does not use its flexibility to switch. — [Univ. Bristol](https://research-information.bris.ac.uk/en/publications/would-you-switch-understanding-intra-peak-demand-shifting-among-r/)
- **Yap et al.** Only frequent travellers include crowding in revealed route choice. — [WTR 7671](https://www.worldtransitresearch.info/research/7671)

### Inferences
- **Recommended prototype design (simple but well grounded):**
  1. Predict the load profile per trip and stop from ticket records: boardings observed, alightings inferred.
  2. For each trip leg, compute perceived IVT = Σ over segments of time × m(segment), where m depends on whether the rider is likely seated.
     - Seated: m = 1.0 when load < seats, else about 1.16–1.2 (Yap; Wardman & Whelan seated).
     - Standing: m = 1.5 + 0.18 × max(0, standees/m² − 3), or simply 2.0–2.3 (Wardman & Whelan standing), capped.
     - Use Jenelius-style P(seat) to blend the two: m = P(seat) × m_seated + (1 − P(seat)) × m_standing.
  3. Route with McRAPTOR (or pyraptor) on 2 criteria: arrival time and perceived crowding cost (or max crowding level). Show the fastest journey and the least-crowded journey from the Pareto set, which is the vulture pattern.
  4. Keep to 2–3 criteria (arrival, crowding, optionally transfers) for speed and readability.
- Make the multiplier a **user slider** ("I don't mind standing" ↔ "I want a seat"). Heterogeneity is large (Santiago, Yap), and post-COVID values are higher.
- Behaviour-change evidence is modest: about 25% uptake in Stockholm, and stated-preference shifts concentrated in flexible, crowd-averse users. Pitch the benefit as **user comfort and choice**, not as system-wide load balancing.

### Gaps
- No peer-reviewed field evaluation of a deployed crowding-aware *routing* feature was found (e.g., A/B test results from Google, Citymapper or Moovit).
- Full Wardman & Whelan breakdown by density bands was not retrieved; only the means are reported here.
- No bus-specific (rather than rail) multiplier per standee/m² was confirmed, apart from Yap's tram/bus value.
- No Indian or Delhi crowding valuation study was searched or found.

---

## Q4. How should uncertainty or confidence be communicated, and what evidence exists that users change behaviour?

### Takeaway
No study tests uncertainty displays specifically for crowding. The closest evidence comes from bus **arrival-time** prediction research (Kay et al. CHI 2016; Fernandes et al. CHI 2018): frequency-based displays (quantile dotplots, CDFs) lead to better decisions than text intervals. For crowding, the analogous approach is to show a probability distribution over the 3–4 levels, or "P(seat)", plus the data basis ("based on typical Tuesdays" vs live).

### Cited Findings
- **Kay et al. (CHI 2016), "When(ish) is My Bus?":** quantile dotplots on mobile reduced the variance of users' probability estimates by about 1.15× compared with density plots, and increased confidence. — [Northwestern MU Collective](https://mucollective.northwestern.edu/project/when-ish-is-my-bus); [PDF](https://vis.mit.edu/classes/6.859/readings/pdfs/Kay-WhenishIsMyBus.pdf)
- **Fernandes et al. (CHI 2018):** an incentivized bus-catching decision experiment. Quantile dotplots gave the best decisions, CDFs were nearly as good, and both beat textual uncertainty, which was sensitive to the interval chosen. — [CHI 2018 PDF](https://mucollective.northwestern.edu/files/2018-UncertainBusDecisions-CHI.pdf); [UW IDL](https://idl.uw.edu/papers/uncertainty-bus)
- **Deployed apps signal provenance rather than probability:**
  - Transit app: crowd reports override predictions for 10 minutes ([Mass Transit](https://masstransitmag.com/home/press-release/21160934/transit-app-public-transit-riders-help-one-another-avoid-crowds-with-the-transit-app)).
  - Moovit: shows agency feeds in preference to user reports ([Moovit blog](https://moovit.com/blog/how-crowded-is-your-bus-know-in-real-time-and-help-others-by-self-reporting/)).
  - NS: says its indicator ignores events and weather ([Treinreiziger](https://www.treinreiziger.nl/geen-realtime-drukte-informatie-meer-bij-ns-treinen/)).
- **Users value information even without acting on it** (Stockholm metro pilot). — [WTR 6591](https://www.worldtransitresearch.info/research/6591)
- For behaviour change evidence, see Q3 (Stockholm about 25% uptake and car shift; NL and UK stated-choice departure-time shifting).

### Inferences
- **Prototype UI recommendations:**
  - Use a 3–4 level colour badge (matching Google, Seoul and NAVITIME conventions).
  - Add a small stacked bar or dot strip showing P(level), e.g., derived from historical quantiles of load for that trip and time bin.
  - Add a "chance of a seat: 70%" text line, following Jenelius.
  - Add a confidence tag: High when there are many historical observations and low variance, Low when there are few, the bus is off schedule, or it is a holiday or event day.
  - Label the source: "Predicted from ticket data (typical weekday)".
- Accuracy validation for the hackathon:
  - Hold out recent weeks.
  - Report % exact category, % within ±1 category, and MAE in passengers. These are comparable to the industry claims of about 80–88% category accuracy.
  - Calibration: for example, does "70% seat chance" come true about 70% of the time?
- Be explicit that ticket-derived load excludes pass holders and fare evaders, so loads are likely underestimated. Calibrate against any manual counts if they are available.

### Gaps
- No empirical study found on uncertainty displays for crowding specifically, or on trust and calibration of crowding predictions in deployed apps.
- No data found on how often users override crowding-aware route suggestions in deployed apps.
