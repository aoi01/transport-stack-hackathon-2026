# Open / free road-traffic and road-network data for Delhi (for a bus segment travel-time predictor)

Research date: 2026-11-17. About 17 tool calls (searches and fetches). Labels: **[V]** = verified this session from a cited page or search snippet. **[I]** = inferred, or from background knowledge not re-checked this session. No accounts were created, no keys were requested, nothing was downloaded, and no team data was sent anywhere.

Framing used throughout. The model is trained on **October 2026** bus GPS. A source is only useful for **training features** if its data **for October 2026 can still be obtained now (Nov 2026)**. Live-only APIs can help only with (a) static or "typical" priors, (b) future inference-time features, or (c) data the team would have had to log at the time.

## Q1. Live/historical traffic speed sources usable in India (Mappls, Google, TomTom, HERE, Waze, Uber Movement, Ola Maps)

### Takeaway
None of the commercial traffic APIs gives free, storable, model-trainable **historical** segment speeds for Delhi in October 2026. TomTom Traffic Stats is the only product found that is explicitly historical, per-segment and floating-car based, and it is trial or paid. Google, Ola and Mappls are live or predictive routing APIs: they give ETAs now, not October history, and Google's terms forbid storing results or building content from them. Waze for Cities is free but only for government partners, and no Delhi partner was found. Uber Movement is not a viable source.

### Cited findings

**Ola Maps (Krutrim)**
- [V] At its 2024 launch, the free tier was 5M calls/month per API (Autocomplete, Reverse Geocoding, Vector Tiles, Directions), with higher volumes at about half of Google's rates — [Inc42](https://inc42.com/buzz/after-google-maps-cuts-prices-ola-maps-announces-new-pricing-structure-to-woo-developers); [Business World](https://businessworld.in/article/ola-maps-vs-google-maps-ola-krutrim-offers-3-year-free-ola-maps-to-startups-smbs-on-ondc-526548)
- [V] The current pricing page (as surfaced by search) lists Directions as the first 100K requests free, then ₹0.199/request up to 5M, then ₹0.049/request — [Ola Maps pricing](https://maps.olakrutrim.com/pricing). This conflicts with the 2024 5M free figure. Treat the current page as authoritative, but the exact tier was not confirmed by a direct fetch.
- [V] Customer notice, August 2026: revised pricing and tiers from **1 Sep 2026**, prepaid "Ola Maps credits" replace card billing, and usage within the free-tier allowance needs no credit balance. The notice gives no per-API free numbers and says nothing on caching or ML training; those terms sit in linked T&C / Fair Usage PDFs that were not read — [Ola Maps update 2026](https://maps.olakrutrim.com/pricing/update-2026)
- [V] Traffic-aware routing, multimodal and two-wheeler routes were described in 2024 as planned "Routes APIs" — [YourStory](https://yourstory.com/2024/07/bhavish-aggarwal-responds-google-launches-free-ola-maps-apis-developers-startups); [Motor India](https://www.motorindiaonline.in/krutrim-announces-new-pricing-and-strategic-future-roadmap-for-ola-maps/). Whether a live traffic-flow tile or segment-speed API exists now was not confirmed.

**Google Maps Platform (Routes / Distance Matrix)**
- [V] India pricing: legacy Distance Matrix (India SKU) has 70,000 free monthly events, then $1.50 per 1,000 up to 5M, then $0.38. India pricing applies to customers with billing and primary usage in India — [Google India pricing](https://developers.google.com/maps/billing-and-pricing/pricing-india?hl=de); [Distance Matrix usage & billing](https://developers.google.cn/maps/documentation/distance-matrix/usage-and-billing?hl=en)
- [V] Routes API policies say "Cache or store Google Maps Content only as expressly permitted." Place IDs may be stored indefinitely and lat/lng for up to 30 days. Durations and route results have **no caching exception**. Bulk downloading of "directions, distance matrix results" is barred, and so is "creat[ing] content based on Google Maps Content" — [Routes API policies](https://developers.google.com/maps/documentation/routes/policies)
- [I] Storing Google travel times to build a training dataset, or showing them on a non-Google map, very likely breaches these terms. The policy page does not use the words "machine learning". Training on Google durations should be treated as not permitted unless legal review says otherwise.

**Mappls (MapmyIndia)**
- [V] Mappls sells a Distance Matrix / predictive-ETA API on AWS Marketplace that takes historical traffic into account. It is sold in contract blocks (e.g. up to 100,000 requests), with support via awsmapisupport@mapmyindia.com — [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-dtnihnen3b5e2); [listing 2](https://aws.amazon.com/marketplace/pp/prodview-pcnm56cwbu2uq)
- Gap: the Mappls developer portal's free credits, traffic-flow API and terms were not found by search (see Gaps).

**TomTom**
- [V] Traffic Stats is a historical service built on anonymised floating-car data. Route Analysis gives average and median travel time, speeds, P15/P85 speeds, travel-time ratio and P5–P95 travel time. Each segment carries average speed, speed limit, name, median, standard deviation and percentiles. Area Analysis gives per-segment, per-direction stats with functional road class. Output is XLS, SHAPE or JSON. There is a 30-day free trial (API key or MOVE Portal) and a 60-day Batch evaluation using sample data; full access means contacting TomTom — [TomTom Traffic Stats intro](https://docs.tomtom.com/traffic-stats/documentation/product-information/introduction)
- [V] Default limits: Route Analysis allows 24 date ranges; Area Analysis allows 1; maximum range is 1 year per analysis — [Traffic Stats limits](https://docs.tomtom.com/traffic-stats/documentation/user-guide/other-options/limits-release-notes-user-guide)
- [V] General TomTom APIs give 2,500 free non-tile requests/day on all plans (HTTP 429 when exceeded) — [TomTom FAQ](https://developer.tomtom.com/platform/documentation/faqs). The pricing page lists Traffic Flow Segment Data and Traffic Incidents with free quotas — [TomTom pricing](https://developer.tomtom.com/pricing). These are **live** APIs.
- [V] TomTom Traffic Index, New Delhi 2025: 10 km takes 24 min 28 s on average (+28 s vs 2024), 25 min 58 s in the morning peak and 31 min 45 s in the evening peak. Congestion level is 106% and 104 h are lost per year at rush hour — [TomTom Traffic Index New Delhi](https://www.tomtom.com/traffic-index/new-delhi-traffic/). Delhi ranked 23rd worldwide in 2025 vs 10th in 2024 (as reported by search summary) — [TomTom city page](https://www.tomtom.com/traffic-index/city/new-delhi/)
- Gap: whether India / Delhi is in Traffic Stats market coverage (the Market Coverage page was not read), and the T&C on storage or ML training.

**HERE**
- Only an unverified third-party claim was found: HERE Routing v8 Freemium allows 30k transactions/month — [gotime docs](https://gotime.readthedocs.io/en/latest/pricing.html). No official HERE traffic-flow pricing or terms were retrieved.

**Waze for Cities (formerly Connected Citizens Program)**
- [V] The program is free, for about 3,000 partners worldwide, mostly government bodies. Partners exchange a GeoRSS XML/JSON feed (alerts, jams) updated every 2 minutes. There is no public API; cities must apply — [Waze for Cities](https://www.waze.com/id/wazeforcities); [Waze partner help](https://support.google.com/waze/partners/answer/10618477); [Waze data-sharing tools](https://support.google.com/waze/partners/answer/10618047)
- [V] No Delhi or Indian government Waze for Cities partner was found in search results — [search context: Waze India mapping wiki](https://waze.com/wiki/India/Mapping_guidelines)
- [V] A news item reports that Delhi Traffic Police "ties up with navigation platforms to provide real-time road alerts". The platforms are not identified in the snippet and the article was not read — [inkl](https://www.inkl.com/news/delhi-traffic-police-ties-up-with-navigation-platforms-to-provide-real-time-road-alerts)

**Uber Movement**
- [V] Launched in 2017, it released CSV data under CC BY-NC — [TechCrunch 2017](https://techcrunch.com/2017/08/30/uber-movement-traffic-data-finally-makes-it-out-of-beta/)
- [I] Background knowledge, not re-verified here: Uber Movement was shut down in roughly late 2023, and past downloads (which reportedly included some Indian cities) are no longer offered. Even if old copies exist, they are licensed NC and pre-date 2026, so they have no value for October 2026.

### Inferences
- [I] **For October 2026 training data, the only practical external speed history** is (a) TomTom Traffic Stats (trial or paid; check India coverage and whether the trial T&C allow model training), or (b) the team's own bus GPS. Every free API is live or predictive.
- [I] **Ola Maps** is the most permissive-looking Indian option on cost, and it bills in INR with data in India. A useful pattern is a one-off query of Directions/Distance Matrix ETAs for each stop-to-stop pair at several departure times. That gives a "typical car ETA" prior for sparse links. Before storing results or using them as training features, read the T&C and Fair Usage PDFs.
- [I] **Google**: do not cache durations or train on them. It is fine for ad-hoc sanity checks only.
- [I] **Live APIs at inference time** (TomTom Flow Segment Data at 2,500 free/day, Ola Directions) could add a "current car speed on the link" feature in production. This only helps if the same feature is logged going forward to train on. It cannot be backfilled for October.
- [I] TomTom Traffic Index city-level hourly/daily congestion is an aggregate useful for slide context (e.g. "Delhi 106% congestion"). It is not a segment feature.

### Gaps
- Mappls developer portal free tier, Traffic API (flow tiles, ETA) and terms on storage/ML: not retrieved.
- Ola Maps T&C / Fair Usage PDFs (caching, derived data, ML): not read.
- TomTom: India in Traffic Stats coverage; T&C for trial-data use in models.
- HERE official freemium and traffic terms for India: not found.
- Uber Movement shutdown date: not confirmed from a primary source this session.

## Q2. Delhi Traffic Police advisories, closures, events, VIP movement; ITMS and signal timing

### Takeaway
There is no structured or open feed (API/CSV) of Delhi Traffic Police (DTP) closures. Advisories are published as posts on X **@dtptraffic**, on the DTP website and Facebook, and are widely republished by news outlets. A hand-built **event/closure calendar for Oct–Nov 2026** is therefore feasible and is the highest-value "unusual day" feature. The ITMS (adaptive signals, 42 corridors) was only **approved on 30 Sep 2026**, so it does not affect October 2026 and offers no open signal-timing data.

### Cited findings
- [V] DTP posts advisories on X as **@dtptraffic** (e.g. a post dated 24 July 2026), plus its website and Facebook. Helplines are 1095 and 011-25844444. In October 2025, officers were ordered to act on complaints tagged on X (congestion, signal malfunctions, breakdowns) — [Tribune](https://www.tribuneindia.com/news/delhi/traffic-police-officials-directed-to-act-promptly-on-complaints-received-on-x); [webindia123, Jul 2026](https://news.webindia123.com/news/articles/India/20260724/4478900.html)
- [V] The DTP website domain is traffic.delhipolice.gov.in (page surfaced in search, not read) — [DTP site](https://traffic.delhipolice.gov.in/node/86). The brief's "delhitrafficpolice.nic.in" was not confirmed as the current site.
- **Advisories relevant to the October–November 2026 training and evaluation window [V]:**
  - 11 Oct 2026: diversions warned at about 30 points — [Outlook India](https://www.outlookindia.com/national/delhi-traffic-advisory-police-warn-of-diversions-at-30-points-on-october-11)
  - 12–13 Oct 2026: advisory "in view of the law and order situation", with likely disruption city-wide and diversions at Minto Rd, Mandi House, Patel Chowk, Guru Nanak Chowk, Lodhi Rd flyover, Sardar Patel Marg and CP Outer Circle — [News On AIR 13 Oct](https://newsonair.gov.in/delhi-traffic-police-issue-advisory-in-view-of-the-law-and-order-situation/); [News On AIR 12 Oct](https://newsonair.gov.in/delhi-traffic-police-issues-advisory-amid-law-and-order-situation-in-new-delhi/); [Devdiscourse "dynamic diversions"](https://www.devdiscourse.com/article/headlines/3990727-delhi-traffic-advisory-police-implement-dynamic-diversions-due-to-prevailing-situation)
  - Dussehra 2026 advisory (incl. Dwarka) — [NewKerala](https://www.newkerala.com/news/a/delhi-traffic-police-issues-advisory-ahead-dussehra-celebrations-876.htm)
  - 1 Nov 2026: INDIA-bloc rally at Ramlila Maidan, restrictions 10:00–17:00 — [News On AIR](https://newsonair.gov.in/delhi-traffic-police-issues-traffic-advisory-in-view-of-proposed-rally-by-opposition-parties-at-ramlila-maidan/)
  - 5–11 Nov 2026: Diwali rush arrangements around Anand Vihar ISBT — [Business Today](https://www.businesstoday.in/india/story/delhi-traffic-advisory-for-diwali-rush-out-check-all-diversions-566073-2026-11-05)
  - Earlier reference: BRICS Summit, 11–13 Sep 2026, with 22 diversion points and curbs on 35+ roads — [Business Today](https://www.businesstoday.in/india/story/brics-summit-traffic-alert-delhi-lists-22-diversion-points-curbs-on-35-roads-from-sept-11-554711-2026-09-11)
- **ITMS [V]:** On 30 Sep 2026 the CCEA approved ₹1,789.52 crore for Delhi ITMS: 42 corridors, 3 phases over 24 months plus 5 years O&M. Delhi Police will appoint a Master System Integrator, with C-DAC as PMC. Features include AI adaptive signals, ANPR enforcement and real-time monitoring. The project comes more than a decade after it was first planned — [Republic World](https://www.republicworld.com/india/cabinet-clears-rs-1790-crore-ai-powered-intelligent-traffic-management-system-for-delhi-2026-09-30-137995); [Policy Edge](https://www.policyedge.in/p/cabinet-clears-1789-crore-plan-for-traffic-responsive-signals-across-42-delhi-corridors); [Construction World](https://www.constructionworld.in/policy-updates-and-economic-news/delhi-clears-rs.-17.9-bn-intelligent-traffic-system-across-42-corridors/98293)
- [V] There was no report that the MSI had been selected or that rollout had started as of early October 2026 (search summary).
- Signal timing data: no public source found.

### Inferences
- [I] Build an **`event_calendar.csv`** (date, start–end time, affected roads/junctions, type: rally / law-and-order / festival / VIP / summit / construction) from @dtptraffic posts and news. Then geocode the named junctions and use OSM to buffer the affected roads. Features: `is_event_day`, `segment_within_X_m_of_closure`, and `event_type`. The 12–13 Oct law-and-order days and Dussehra/Diwali-week effects fall inside the October training data and are likely sources of large residual errors. Check the residuals on those dates first.
- [I] Scraping X is restricted by X's terms and API pricing. Manual collection of a few dozen advisories for a hackathon, or using news-agency copies (News On AIR is public broadcaster content), is the practical route.
- [I] Because ITMS is only approved, signal infrastructure in October 2026 was largely fixed-time or legacy. Signal *counts* from OSM are a better proxy than timing.

### Gaps
- No machine-readable DTP closure archive or API was found. Whether DTP shares alerts with Google/Mappls (the "navigation platforms" tie-up) and which platforms are involved was not confirmed.
- VIP-movement notices are generally not published in advance (not verified this session).
- Complete list of October 2026 advisories (only those surfacing in search were captured).

## Q3. OpenStreetMap for Delhi: attribute quality and use as features

### Takeaway
OSM is the only fully open (ODbL) road network suitable for storage, combination, map display and model training. Geometry, junctions and flyovers are generally usable. Attribute tags such as `lanes` and `maxspeed` are sparse and inconsistent in India, so use them as optional features and rely more on derived topology (signal counts, junction density, road class, flyover/bridge flags).

### Cited findings
- [V] No Delhi-specific study of lanes/maxspeed completeness was found. A 2017 Punjab study (intrinsic indicators: length completeness, attribute completeness, semantic accuracy, navigability) found OSM progress there to be slow — [Sehra et al., MDPI Future Internet 2017](https://www.mdpi.com/1999-5903/9/2/15)
- [V] Official baselines are weak: Union Territories (Delhi is one) have very little published road-network data, and many PWD sources are outdated (some from 2007) — [OSM talk-in 2015](https://lists.openstreetmap.org/pipermail/talk-in/2015-November/002406.html)
- [V] Anecdote: OSM way history for a Delhi–Gurugram Expressway segment shows inconsistent tags across versions (lanes 4 / maxspeed 80 vs lanes 18 / maxspeed 40) — [OSM way 190261045 history](https://www.openstreetmap.org/way/190261045/history/14)
- [I] Background knowledge: OSM data is licensed under ODbL 1.0. Storage, combination, commercial use and map display are allowed with attribution, and share-alike applies to derived *databases* that are publicly distributed. Model weights and produced works are generally not "derivative databases" — [OSM copyright](https://www.openstreetmap.org/copyright) (not fetched this session)
- [I] Background knowledge: a Delhi extract can be obtained from Geofabrik (India / northern-zone extract, >5 MB, not downloaded) or via the Overpass API for a bounding box. OSMnx can compute node degree and intersections.

### Inferences (feature recipe)
- [I] Per stop-to-stop segment (map-match the bus path or route shape to OSM ways):
  - `n_traffic_signals` (count of `highway=traffic_signals` nodes within 15–20 m of the path), and signals per km
  - `n_junctions` (nodes with degree ≥3), junction density, and roundabout count (`junction=roundabout`; important in Lutyens' Delhi, e.g. Mandi House, Patel Chowk)
  - share of length on `highway=trunk/primary/secondary/tertiary/residential`
  - share on `bridge=yes` / `layer>0` (flyovers) and `tunnel`/underpass, which have fewer signals and free-flowing speeds
  - `lanes` and `maxspeed` only where present, with a missing-indicator
  - bus-lane tags (`busway=*`, `lanes:bus`, `bus:lanes`). [I] Delhi's BRT was dismantled earlier and bus lanes are mostly painted and unenforced, so expect few tags.
  - distance to nearest metro station or Phase 4 construction site (see Q4)
- [I] **Filling sparse links**: train a link-level "typical speed" model on dense links using these static features, then apply it to sparse links (cold-start prior). Alternatively use graph smoothing via neighbouring segments.
- [I] Check attribute coverage quickly with taginfo for India or an Overpass count over the Delhi bbox before investing in a feature.

### Gaps
- Actual percentage coverage of `lanes`, `maxspeed` and `traffic_signals` in Delhi (taginfo or Overpass not queried this session).
- Whether OSM signal mapping in Delhi is complete enough for counts to be reliable. Spot-check against Street View or local knowledge.

## Q4. Road works / metro construction / flyover projects affecting October–November 2026

### Takeaway
DMRC Phase 4 is still under construction in 2026, with long barricaded stretches and diversions planned jointly with DTP. No consolidated, dated, open list of closures exists, so a manual list of active work zones (from DMRC / DTP / news) is the practical approach.

### Cited findings
- [V] January 2026: Phase 4 sites have about 20 km of barricading, LED rope lights, blinkers, road studs and diversion signage, with a three-layer barrier at diversion points. Diversions are planned with DTP, and 270+ traffic marshals are deployed around the clock — [ThePrint](https://theprint.in/india/dmrc-phase-4-construction-20-km-barricades-blinkers-for-commuters-safety/2836170); [Construction World](https://www.constructionworld.in/transport-infrastructure/metro-rail-and-railways-infrastructure/delhi-metro-phase-4-sites-get-enhanced-safety-measures/85346)
- [V] Phase 4 includes double-decker viaducts (road flyover plus metro) — [ThePrint](https://theprint.in/india/dmrc-constructing-3-double-decker-viaducts-in-its-phase-4-expansion/2367445). The CM reviewed Phase 4 work at RK Ashram Marg — [Construction World](https://www.constructionworld.in/amp/policy-updates-and-economic-news/rekha-gupta-reviews-phase-four-work-at-rk-ashram-marg/90609)
- [V] April 2026: a ₹1,471 crore elevated corridor along Mehrauli–Badarpur Road was approved, to be executed by DMRC (integrated with metro) — [Swarajya](https://swarajyamag.com/amp/story/news-brief/delhi-govt-approves-rs-1471-crore-elevated-corridor-along-mehraulibadarpur-road-dmrc-to-execute-integrated-project)
- [V] Utility works also cause DTP closures, e.g. TPDDL cabling and Delhi Jal Board pipeline work on New Rohtak Road (closure "till June 30", year as per article) — [India.com](https://www.india.com/news/india/delhi-traffic-advisory-new-rohtak-road-shut-till-june-30-jams-slow-movement-diversions-underground-pipeline-work-delhi-jal-board-8404903/)
- [V] November 2025 (prior year): Central Vista re-carpeting caused night-time restrictions in the Lutyens zone — [India TV](https://www.indiatvnews.com/delhi/delhi-traffic-advisory-recarpeting-work-under-central-vista-project-prompts-night-time-alert-restrictions-in-lutyens-zone-2025-11-23-1018682)
- [V] Delhi traffic hotspot programme: 215 fixes at 62 hotspots (date not shown in snippet) — [NewsBytes](https://www.newsbytesapp.com/news/india/delhis-traffic-mess-215-fixes-at-62-hotspots/tldr)

### Inferences
- [I] Add a static feature `segment_overlaps_metro_construction` (binary or overlap length) by digitising active Phase 4 corridors (e.g. Mehrauli–Badarpur, RK Ashram Marg area, Majlis Park–Maujpur, Janakpuri–RK Ashram alignments). Corridor alignments are on DMRC's site and in OSM (`railway=construction`). [I] OSM often maps under-construction metro lines, which is a cheap source.
- [I] Corridors with active construction during October 2026 should show persistent (not day-specific) under-prediction if the model lacks a link fixed effect. Check residuals per segment against the construction overlap.

### Gaps
- No dated list of PWD/DDA/DMRC road closures active in October–November 2026 was found. Phase 4 corridor-wise completion status as of Nov 2026 was not verified.
- PWD Delhi and DDA project dashboards were not searched (budget).

## Q5. Academic / open datasets of Indian urban traffic speeds

### Takeaway
No IIT Delhi / IIT Madras / IISc open dataset of Delhi road speeds was found. The closest material is an IIIT-Delhi paper on Delhi bus GPS (Open Transit Data) and small datasets for other cities. None cover October 2026, so these are useful only for methods or priors.

### Cited findings
- [V] "Benchmark Dataset for Timetable Optimization of Bus Routes in the City of New Delhi" (IIIT-Delhi, arXiv 1910.08903) uses real-time Delhi bus GPS for 543 routes and 3,464 stops and is pitched for travel-time estimation — [arXiv](https://arxiv.org/pdf/1910.08903)
- [V] Durgapur bus trajectory dataset (smartphone GPS and sensors on intra-city buses), on GitHub — [GitHub](https://github.com/stilllearningsoumya/bus_trajectory_dataset)
- [V] Bangalore traffic open data (Datameet): route travel times collected by polling Google Maps twice an hour for about 8 months. The author mentions a similar method for 20 Indian cities — [Datameet group](https://groups.google.com/g/datameet/c/NDT9b0nmVgM). [I] This likely conflicts with Google's caching terms (Q1), so treat its licensing as unclear.
- [V] JICA / Hitachi Chennai report: bus GPS used to compute road travel speeds (report only, no dataset) — [JICA PDF](https://openjicareport.jica.go.jp/pdf/12304416.pdf)

### Inferences
- [I] The team's own October 2026 bus GPS is denser and more current than any academic set. Academic material is most useful for method citations (e.g. separating dwell time from running time, as the Durgapur authors note that GPS speed includes stoppage time).
- [I] Delhi's Open Transit Data portal (otd.delhi.gov.in, GTFS and GTFS-RT for DTC/cluster buses) is the likely origin of the hackathon data. If the team has *all* buses' October GTFS-RT positions (not only their routes), using other routes' buses on shared links is the cheapest way to fill sparse links. Not verified this session.

### Gaps
- No IISc, IIT Delhi (TRIPP) or IIT Madras (RBG Labs, which has worked on Chennai bus arrival prediction) open speed dataset was confirmed. These institutions publish papers, but no open data download was found.
- Any Delhi government open traffic-volume or ATCC count data: not searched.
