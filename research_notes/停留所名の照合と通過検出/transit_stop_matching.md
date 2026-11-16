# Mapping ticket stop names to GTFS stops with route context, stop order, fares and vehicle GPS (Delhi ONDC e-tickets)

Research date: 2026-11-16. Scope: methods, case studies and reported accuracies for linking fare/ticket stop names (ETM or e-ticket) to physical GTFS stops without relying on name similarity alone. Input for the Delhi Transport Stack Hackathon 2026 team (October 2026 ONDC e-tickets plus Delhi GTFS and DTC GPS).

How to read this file:
- Items marked **Local check** were computed by this researcher on the project data on 2026-11-16, using `data/processed/tickets_matched.parquet` (the team's current matches), `data/processed/patterns.parquet` (one representative pattern per route) and `data/raw/gtfs_static/`. They are measurements, not literature.
- The team's current results (exact 55.7%, fuzzy 18.3%, 400 m nearby 5.5%, unmatched 20.6%) and the purchase-time offset (median 0.8 min after the bus passed the boarding stop, 23% before) come from the research brief. The Local checks reproduce the four match shares exactly.

Overall finding up front:
- I found no published work, in India or elsewhere, that maps ETM or e-ticket stop names to GTFS using sequence alignment or fares. The methods below are assembled from three neighbouring areas: smart-card boarding inference from AVL, stop-conflation tools, and toponym matching.
- Two facts in our own data matter more than any paper:
  1. **The failures sit in one group of routes.** On routes whose GTFS trips carry `fare_stage` flags, 88.8% of tickets match exactly and 4.8% are unmatched. On the other routes (59% of tickets), 32.9% match exactly and 31.4% are unmatched.
  2. **The fare is a usable distance signal.** Fares are the official slab fares less a 10% app discount, and for 83% of exact matches the fare slab agrees with the along-route distance between the matched stops.

---

## 1. Route context, stop order and sequence alignment (operator stop lists vs GTFS stop sequences)

### Takeaway
Stop-matching tools outside India separate similar names with route evidence (same route and direction, distance from the previous stop), and one paper used a generalised Needleman–Wunsch alignment, but I found no Indian case (BMTC, MTC, KSRTC, TSRTC, DTC, Chalo) that aligns ETM or e-ticket stop lists with GTFS. For Delhi it is feasible and cheap: DTC's per-route fare-stage circulars list every stop in order (on 740C the GTFS `fare_stage` flags reproduce them exactly), and the tickets themselves give millions of "start before end" order constraints per route and direction.

### Cited Findings
**Elsewhere: route context in stop and name matching**
- **Needleman–Wunsch on stop names.** In an agent-based multimodal planning project, the authors write: "To resolve various namings for the geo-location and matching problem, we applied a generalization of the Needleman-Wunsch algorithm." Their reasons:
  - "Names and identifiers of various stops and lines in each data set may vary significantly."
  - Plain name-to-name matching fails partly because stops in a stop area share one name, so they mapped each street-map stop position to the operator's stop identifier.
  - Source: [Greulich, Edelkamp & Gath 2013, "Agent-Based Multimodal Transport Planning in Dynamic Environments" (Springer). Seen only as a search excerpt of a mirrored full text; I did not read it in full](https://doi.org/10.1007/978-3-642-40942-4_7)
- **Swiss ATLAS↔OSM "Stop Sync".** Each official platform is matched to OSM elements by "a fixed sequence of matching rules: shared identifiers, names, routes and distance".
  - GTFS `stop_id`s are resolved to ATLAS IDs so that GTFS routes can be compared with OSM route relations.
  - Shared routes feed back into stop matching: a nearby OSM node served by the same route and direction is "very likely the same stop".
  - Reported figures: 55,117 ATLAS platforms, a match rate of "89.5" (formula and unit not stated), and 5,790 unmatched platforms.
  - Source: [ATLAS↔OSM Stop Sync docs](https://atlas.osm.ch/docs)
- **gtfs-generator (OSM-based GTFS builder, 2026).** It matches by a strong identifier first (`uic_ref`). Otherwise it takes candidates in a radius (default 20 km) and accepts a name that matches directly, is an abbreviation, has similarity ≥0.8, or shares words.
  - The author states that "the matching quality strongly depends on making a good guess of the distance from the previous stop", which "greatly reduces the risk of similarly named stations being mismatched".
  - Problems reported: spelling variants, transliteration, and provider coordinates "off by multiple kilometers".
  - Source: [Jonah Brüchert, "Generating GTFS feeds" (Planet KDE, 7 Feb 2026)](https://planet.kde.org/jonah-bruchert-2026-02-07-generating-gtfs-feeds/)
- **Parent stops sharing a name.** Many schedules merge several stop locations on different roads into one parent stop with the same name, which breaks name-only matching. — [Poletti 2017, Polytechnique Montréal thesis (search excerpt)](https://publications.polymtl.ca/5091/1/2017_Poletti_Public_transit_route_mapping_large-scale.pdf)
- **Sequence-alignment ideas for GTFS.** A UNC Charlotte (CAMMSE) project proposes borrowing bioinformatics sequence-alignment tools for transit, treating GTFS trips as stop sequences and using Longest Common Subsequence for similarity. — [CAMMSE UNCC 2020 project sheet, Lownes & Becker (search excerpt)](https://cammse.charlotte.edu/wp-content/uploads/sites/191/2023/04/CAMMSE-UNCC-2020-UTC-Project-Information-10-Lownes-Becker.pdf)
- **Dynamic programming on timestamps.** A Xerox patent aligns observed arrival/departure timestamps to scheduled trips with dynamic programming. — [US patent application 20140288982 (search excerpt)](https://patents.justia.com/patent/20140288982)
- **Dynamic programming for destinations.** MIT teaching material lists a dynamic-programming method for inferring trip destinations from fare and vehicle-location data (Sánchez-Martínez 2017, TRR 2652). — [MIT 1.258J Lecture 10 references (2017)](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)

**India: what operator stop lists look like and existing tooling**
- **ETM data quality (GIZ roadmap).**
  - ETM and GPS vendors "don't use the same nomenclature and unique ids".
  - Different conductors select the same location under different stop names.
  - Origin/destination entries have significant errors on crowded buses.
  - GPS-linked ETMs that auto-set the origin only partly fix this.
  - Source: [GIZ/Changing Transport, Roadmap for Data-driven Transformation of Indian Bus Systems (2021), as quoted in the team's earlier note `etm_ticket_india.md`](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- **BMTC Bengaluru.** ETMs come preloaded with route, stop and stage-fare data and are locked to a route; buses carry GPS logging every 10 s. — [FactorDaily on BMTC ITS (search excerpt)](https://archive.factordaily.com/longform/big-data-real-time-gps-tonic-not-steroids-bengalurus-bus-service/)
- **KSRTC Karnataka.** All on-board fare collection has used handheld ETMs since 2004. The ETMs are loaded with route, stage and fare-table data for the depot. — [SSATP Fares Toolkit, Karnataka case study](https://www.ssatp.org/sites/ssatp/files/publications/Toolkits/Fares%20Toolkit%20content/case-studies/karnataka-india.html)
- **Payanam (WRI with the Telangana Open Data Portal).** A browser tool for "progressively mapping public transport routes when there wasn't geo-data available", i.e. routes known only as stop-name lists, and exporting them to GTFS.
  - It can load a databank of known stop locations to click on while mapping.
  - Its maintainers recommend it where routes have no variations.
  - It is manual and interactive; I found no automatic alignment or reported accuracy.
  - Sources: [Payanam (kandi summary of WRI-Cities/payanam)](https://kandi.openweaver.com/javascript/WRI-Cities/payanam); [static-GTFS-manager listing](https://awesome.ecosyste.ms/projects/github.com%2FWRI-Cities%2Fstatic-GTFS-manager)
- **Vonter/bmtc-gtfs (unofficial BMTC GTFS).** Built from routes, stops and timetables shown in the Namma BMTC app.
  - It covers only routes with working live tracking, and the maintainer warns the app is "not completely accurate".
  - Mobility Database lists it with 4,381 routes.
  - I found no write-up of how stop names were reconciled.
  - Sources: [bmtc-gtfs README (mirror)](https://gh.r-mj.com/Vonter/bmtc-gtfs); [Mobility Database mdb-2595](https://mobilitydatabase.org/feeds/gtfs/mdb-2595)
- **DTC per-route fare-stage circulars.** DTC publishes fare stages route by route as circulars. Examples: "Revised fare Stages of Route No.490" and "Fares stages of new route No. 114A on experimental basis". I found no single route-wise master list. — [DTC circulars archive (search excerpt)](https://dtc.delhi.gov.in/dtc-circulars/archive?page=9)
- **DTC circular for route 740C (dated 13/06/2026).**
  - Route 740C runs Dichaon Kalan Depot ↔ Anand Vihar ISBT, operated from 14-06-2026 "on experimental basis".
  - The Hindi page lists the fare stages per direction: 26 in the UP direction, from Anand Vihar ISBT to Dichaon Kalan Depot, and 25 in DOWN.
  - The English annex lists every stop in order and tags stage stops "Fare Stage" with a stage number.
  - It uses abbreviations and variant spellings, e.g. "Bakkarwala Xing", "Delhi Sect.", "P S Sadar Bazar", "Dr. RML Hospital", "11 Murti", "Kirbi Place", "Bhart Sadhu Samaj", "Dichaon Kalan Depot".
  - The copy list asks the IT manager to update "the online ticketing app and website" with this information.
  - Source: [DTC circular, route 740C (PDF; text extracted locally)](https://dtc.delhi.gov.in/sites/default/files/DTC/important-news/circular_for_route_no_740c.pdf)

**Local checks on Delhi data**
- **GTFS fare stages match the DTC circular (740C).** GTFS `740CUP` has 82 stops with 26 `fare_stage=1`; `740CDOWN` has 80 stops with 25. These are the same counts and essentially the same stage stops as the circular.
  - Spellings differ between the two lists, e.g. circular "Dichaon Kalan Depot" vs GTFS "Dichau Kalan Depot", "Bhart Sadhu Samaj" vs "Bhartiya Sadhu Samaj", "Kirbi Place" vs GTFS "kibri place" in DOWN.
  - The top ticket start names on 740C are GTFS names verbatim, including compound names such as "kendriya terminal / gurudwara rakab gunj".
  - Source: [Local check](../../data/raw/gtfs_static/stop_times.txt)
- **Ticket names come from the full stop list, not just fare stages.** This holds on the 1,214 routes that have `fare_stage` flags.
  - Ticket-weighted start names: 43.0% are fare-stage stops, 47.7% are other stops on the route, and 9.4% are not on the route by exact name.
  - Among exact on-route names, 47.4% are fare stages, against a median 34.5% of a route's stop names being fare stages.
  - Per route, the number of distinct ticket start names is a median 0.8× the number of GTFS stop names.
  - Source: [Local check](../../data/processed/tickets_matched.parquet)
- **Route variants and the representative pattern.**
  - 23.3% of the 2,574 routes have more than one distinct stop sequence across trips (maximum 9).
  - Only 1.5% of route–stop pairs (about 1,270 of 83,360) are missing from the most common pattern.
  - So variant-only stops are real (e.g. "Telephone Exchange") but are not the main cause of the 20.6% unmatched.
  - Source: [Local check](../../data/raw/gtfs_static/trips.txt)
- **Current matcher already enforces order.** Order violations (alighting at or before boarding on the pattern) are 0.0% among current matches, so the existing matcher already enforces boarding before alighting. — [Local check](../../data/processed/tickets_matched.parquet)

### Inferences
**1. Candidate set.** Restrict candidates to the union of all stop sequences of the ticket's route-direction, not one representative pattern.
- Build a supersequence by progressive alignment: start from the dominant pattern and align each other pattern to it with an LCS/Needleman–Wunsch on `stop_id` equality.
- Variant-only stops then get a position between their neighbours.
- Cost: a few dozen lines of numpy; 2,574 routes × ~35 stops is trivial.

**2. Order constraint.** Keep b before a. Use the opposite direction (UP↔DOWN) only as a penalised fallback when no forward pair is feasible.
- Count how often the fallback fires; that count measures wrong-direction selection by passengers.

**3. Learn each route's ticketing stop list from the tickets themselves.**
- Each ticket gives a constraint: start comes before end in the ticketing app's stop list, assuming the app only offers stops downstream of the source (to verify).
- Exact-matched names are anchors with known GTFS positions.
- For an unknown name n:
  - anchors that n precedes give upper bounds on its position;
  - anchors that precede n give lower bounds.
- Use robust quantiles of these bounds, e.g. the 90th percentile of the lower bounds and the 10th percentile of the upper bounds, to get an interval along the route.
- Then:
  - (a) search GTFS stops in that interval, on any pattern, and also stops of other routes within about 300 m of the shape between the bounding anchors, using a normalised name score;
  - (b) if nothing matches, place n at the interval centre and snap it to the nearest pattern stop, flagged `positioned_not_named`.
- Section 2 tightens the interval further with fare bands.

**4. Needleman–Wunsch per route-direction.** Align the ordered list of ticket names (ordered by step 3) with the GTFS supersequence.
- Match score: `sim(name_i, name_j)` (rapidfuzz `token_set_ratio` on normalised names), minus a penalty proportional to the gap between estimated and GTFS positions when both are known.
- Gaps: affine penalties, so runs of GTFS stops unused by tickets cost little.
- Ambiguous names like "Badarpur" on 460DOWN (candidates "Badarpur Village" / "Badarpur Border (T)") are then decided by which neighbours they sit between, not by string distance alone.

**5. DTC circulars as a third list.** Where the GTFS route has `fare_stage` flags and a DTC circular exists, use the circular's English annex as an independent reference to check alignments and harvest spelling variants (Dichaon/Dichau, Kirbi/Kibri, Bhart/Bhartiya).
- This is optional and manual; there is no consolidated download.

**6. Expected effect.** Moderate gains on the routes that already have `fare_stage` flags, which are already 88.8% exact; the large gains are on the routes without flags (Section 4).

### Gaps
- **Indian precedent.** No published Indian work was found that aligns ETM or e-ticket stop lists with GTFS stop sequences. Chalo, BMTC, MTC, KSRTC Kerala and TSRTC searches surfaced only device and system descriptions, Payanam, and volunteer GTFS projects.
- **Leads not read:**
  - the OSM wiki "Chennai Bus Route mapping project / Manual Mapping";
  - "Mapping Bus Transit Services in Hyderabad – An Illustrative Example of the Use of Open Geospatial Data" (TRID 1470817).
- **Accuracy figures.** No reported accuracy for Needleman–Wunsch or LCS stop alignment was found. The Greulich et al. chapter could not be read beyond an excerpt.
- **Cluster (DIMTS) route masters.** No public route-wise stop or fare-stage lists for cluster routes were found.
- **App ordering.** Whether the ONDC/One Delhi app restricts destinations to stops after the chosen source (the assumption behind step 3) is not documented in what I found.

---

## 2. Using fares: Delhi fare slabs, distance bands, GTFS `fare_stage`, and fare checks on candidate stop pairs

### Takeaway
Official Delhi bands are non-AC ₹5 up to 4 km, ₹10 for 4–10 km, ₹15 above 10 km, and AC ₹10 / ₹15 / ₹20 / ₹25 for up to 4 / 4–8 / 8–12 / above 12 km; the October 2026 e-tickets charge exactly 0.9× these (10% app discount). The slab agrees with along-route distance for 83% of exact matches (94% with ±15% tolerance) and almost as often for fuzzy and nearby matches. So the fare is a weak global validator, but a strong tie-breaker for candidates several km apart and a way to place unknown names along a route ("fare-band trilateration").

### Cited Findings
- **Official fare table (Delhi Tourism, Govt of NCT of Delhi), adults; children's fares listed separately; no effective date given:**
  - Ordinary (non-AC): "Up to 4 kilometers" Rs 5.00; "From 4 kilometers to 10 kilometers" Rs 10.00; "Above 10 kilometers" Rs 15.00.
  - AC: up to 4 km Rs 10; 4–8 km Rs 15; 8–12 km Rs 20; "Above 12 kilometers & Limited/Night Services" Rs 25.
  - DMRC metro feeder buses: up to 8 km Rs 7; above 8 km Rs 10.
  - Source: [Delhi Tourism, City Bus fares](https://delhitourism.gov.in/transport/city_bus.html)
- **App discount.** In July 2021 the Delhi Cabinet approved a 10% fare discount on DTC and cluster bus tickets bought through the app. — [India TV (2021)](https://www.indiatvnews.com/amp/news/india/delhi-govt-approves-10-pc-discount-in-fares-of-dtc-cluster-buses-on-tickets-purchased-through-app-720110)
  - The revamped One Delhi app launch report says 10% off bus tickets and daily passes is still offered. — [ThePrint](https://theprint.in/india/revamped-version-of-one-delhi-app-launched/1193959/)
- **How tickets are bought.** Passengers scan a QR code inside the bus and choose "their fare or source and destination stop". — [Hindustan Times via PressReader (18 Jul 2021)](https://www.pressreader.com/india/hindustan-times-delhi/20210718/281651078120594)
  - DTC and DIMTS buses were integrated onto ONDC with QR tickets. — [CIOL](https://www.ciol.com/tech/dtc-joins-ondc-network-with-qr-ticketing-for-easy-commuter-access-6945002)
- **Official GTFS documentation.** The Delhi OTD documentation lists only the standard GTFS files (agency, calendar, stops, routes, trips, stop_times). It says stop_times arrival/departure times are "a rough estimate generated by assuming a constant speed of travel", and does not document `fare_stage` or `stop_dist`. — [OTD Delhi documentation](https://otd.delhi.gov.in/documentation)

**Local checks on fares**
- **Fares are 0.9× the official slabs.**
  - AC tickets (80.4% of all) by fare per passenger: ₹9.0 40.7%, ₹13.5 33.5%, ₹18.0 13.3%, ₹22.5 11.6%.
  - Non-AC: ₹4.5 37.9%, ₹9.0 37.6%, ₹13.5 24.5%.
  - Odd values such as 26.5, 22.0 and 31.0 total under 1%.
  - ₹9.0 means ≤4 km on AC but 4–10 km on non-AC, so `is_ac` is required to decode the slab.
  - Source: [Local check](../../data/processed/tickets_matched.parquet)
- **GTFS `fare_stage` coverage.**
  - `fare_stage` is a 0/1 flag: 372,928 of 2,737,136 stop_times rows are 1.
  - It is present on 45.8% of trips and 1,214 of 2,574 routes.
  - The `stop_dist` column is empty everywhere.
  - On 740C the flags equal the DTC circular's fare stages (Section 1).
  - Source: [Local check](../../data/raw/gtfs_static/stop_times.txt)
- **Distance by slab agrees with the official bands.** Median along-route distance between matched stops, for exact matches (cumulative straight-line stop-to-stop distance `cum_m` in `patterns.parquet`):
  - AC: ₹9 → 2.84 km, ₹13.5 → 5.89 km, ₹18 → 9.21 km, ₹22.5 → 16.31 km.
  - Non-AC: ₹4.5 → 2.79 km, ₹9 → 6.78 km, ₹13.5 → 15.69 km.
  - Source: [Local check](../../data/processed/patterns.parquet)
- **Fare-consistency rate** (along-route distance inside the slab's band). Based on 2,014,385 matched tickets with standard fares:

  | Match type | No tolerance | ±15% | ±30% |
  |---|---|---|---|
  | Exact | 82.9% | 94.2% | 98.5% |
  | Fuzzy | 81.0% | 93.5% | 97.8% |
  | Nearby | 82.9% | 93.2% | 98.5% |

  Exact matches outside the band: 7.4% shorter than the band, 9.7% longer. — [Local check](../../data/processed/tickets_matched.parquet)
- **No published method for this.** I found none that uses fare slabs to disambiguate ticket stop names. Searches returned only distance-based fare systems that require a tap-out, and refund-at-alighting fare designs. See Gaps.

### Inferences
**1. Use the fare as a soft likelihood, not a hard band.** Estimate `P(slab | d, is_ac)` empirically from exact matches, as a histogram of `d` per slab, and add `log P` to the pair score.
- Hard bands would reject about 17% of correct exact matches.
- The two-sided misses (7.4% short, 9.7% long) suggest DTC charges by fare-stage count, not by exact stop-to-stop distance. With stops grouped into ~1.5 km stages, a 3.5 km trip can be charged as two or three stages.
- Test on the 1,214 flagged routes: compute stages crossed between the matched stops and check whether "number of stages → slab" predicts the fare better than 83%.
- If it does, use stage counts for flagged routes and distance for the rest.

**2. Tie-breaker value.** Fare discriminates only when candidate stops differ by roughly a slab width (4 km AC, 6 km non-AC mid band) in distance to the partner stop.
- Hypothesis (I did not verify the GTFS names on route 502): "S.J. Hospital" on 502UP is most likely Safdarjung Hospital. The matcher picked "T.B. Hospital", probably the one at Mehrauli and so far down the route, and the fare should expose that.
- Near-duplicates such as "Badarpur Village" vs "Badarpur Border (T)" are usually too close for fare to separate. Use order and neighbours (Section 1) or GPS (Section 3) for those.

**3. Fare-band trilateration for names with no GTFS candidate** ("Telephone Exchange" on 85UP, "Health Center" on 578DOWN).
- Each ticket n→a with anchor a at position x_a and slab [lo, hi] implies x_n ∈ [x_a − hi, x_a − lo]; for a→n tickets, x_n ∈ [x_a + lo, x_a + hi].
- Accumulate votes on a 100 m grid along the route supersequence; widen bounds by about 15% as tolerance.
- The argmax gives the position and the vote spread gives the uncertainty.
- With hundreds to thousands of tickets per unmatched (route, name), e.g. 865 for "Telephone Exchange" on 85UP and 896 for "Health Center" on 578DOWN, the interval should shrink to roughly a stage, mostly through tickets whose partners sit near slab boundaries.
- Then search stops near that position (any pattern of the route, or stops within about 300 m of the route shape) with name similarity as a secondary check.

**4. What fare cannot fix.**
- Fare does not pin the exact alighting stop within a slab.
- Riders who state a farther end stop within the same slab cannot be detected by fare alone.
- Treat the end stop as "somewhere in the slab-consistent range" when other evidence is weak.

**5. Practical encoding.** Map amount/pax to slab with a lookup keyed by (is_ac, fare), dividing official fares by 0.9. Drop the under-1% odd fares from fare-based scoring but keep them for name-based matching.

### Gaps
- **Current bands.** DTC's own current (2026) km bands were not found. The Delhi Tourism page has no effective date.
  - A Business Standard headline from 2016 reports that DTC raised AC fares by up to 10%; I did not read it. [Business Standard (2016)](https://www.business-standard.com/article/pti-stories/dtc-increases-fares-of-ac-buses-by-up-to-10-per-cent-116110201156_1.html)
  - The October 2026 amounts confirm the slab prices (₹10/15/20/25 and ₹5/10/15 before discount) but not the km boundaries.
- **Stage-to-fare rule.** DTC's rule linking stage counts to fares, i.e. how many stages fall in each slab, was not found.
- **Fare-based disambiguation.** No literature was found on using fare slabs to disambiguate or locate ticket stop names.
- **Meaning of `fare_stage`.** It has no official definition. The 740C comparison supports "1 = official DTC fare stage stop", but that is one route.

---

## 3. Using vehicle GPS: boarding inference at transaction time, and learning an alias table from GPS-confirmed boardings

### Takeaway
Matching the fare transaction time to the bus's AVL record is the standard way to infer boarding stops: London infers 96% of Oyster bus boardings (93% within ±1 min), and a Jeju study cut card boarding-stop errors from 6.2% to 1.0%. Those systems tap on entry, whereas Delhi e-tickets are bought a median 0.8 min after the bus passes the stop, so a purchase-lag model is needed. An alias table learned from GPS-confirmed boardings would cover 98.6% of no-vehicle tickets, but I found no literature on this kind of self-supervised alias learning; the nearest analogues are Beijing's no-GPS model, Jeju's correction using bus information system (BIS) data, and supervised toponym matching.

### Cited Findings
**London (Oyster plus iBus AVL)**
- **Method.** Origin inference "match[es] the AFC transactions with the AVL data to infer boarding stops". — [MIT 1.258J Lecture 10 (2017)](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- **Origin results**, from the same slides (10 weekdays, 6.1–6.5 million Oyster bus boardings per day):
  - "96% of boarding locations inferred within ± 5 min"; sub-bullets "96% within ± 2 min", "93% within ± 1 min", "28% between arrival and departure times";
  - "2.6% beyond ± 5 min";
  - "1.4% not matched to iBus route or trip".
  - The repeated 96% figures are as printed on the slides.
- **Destination results** (ten weekdays in June 2011; 15.6–16.1 million transactions):
  - "74.5% of bus alighting times and locations inferred within 1 km of subsequent Oyster tap".
  - Failure categories include: only transaction that day 5%; beyond the 750 m maximum distance 6.7%; bus heading away from the next origin 3.6%.
- **Survey comparison.** Inferred OD showed "small stop-by-stop differences" from the Bus OD Survey (BODS). BODS underestimated peak and midday ridership when survey return rates were low (50–80%).
- **Publications.**
  - [Gordon, Koutsopoulos, Wilson & Attanucci (2013), TRR 2343, pp. 17–24](https://worldtransitresearch.info/research/4986); [Gordon MIT thesis record](https://dspace.mit.edu/handle/1721.1/78242)
  - Wang, Attanucci & Wilson (2011, Journal of Public Transportation) applied trip-chaining to smart-card plus AVL data in London. It is described as the first known attempt to validate against manual passenger survey data. — [World Transit Research record](https://www.worldtransitresearch.info/research/4171); [Wang MIT thesis](https://dspace.mit.edu/handle/1721.1/60814)

**China, Korea, Chile**
- **Beijing.** Flat-fare buses do not record the boarding stop. Ma, Wang, Chen & Liu built a Markov-chain-based Bayesian decision tree to infer origins, verified on vehicles with GPS loggers. The abstract reports only "relatively high accuracy". — [Ma et al. (2012), J. Zhejiang Univ. Sci. C / FITEE](https://www.zjujournals.com/xueshu/fitee/EN/10.1631/jzus.C12a0049)
  - A 2018 review describes the common approach: estimate bus arrival times at stops from GPS and fuse them with card timestamps. The decision-tree method is described as the option when GPS is unavailable. Guangzhou card data lacked stop IDs because fare collection was not integrated with AVL. — [Journal of Modern Transportation (2018), s40534-018-0165-y (search excerpt; full text blocked)](https://link.springer.com/article/10.1007/s40534-018-0165-y)
- **Korea (Jeju).**
  - Against a boarding/alighting survey, smart-card boarding-stop information had a 6.2% error rate.
  - A six-step algorithm linking card records to bus information system (BIS) records reduced it to 1.0%.
  - Source: ["Algorithm for Correcting Error in Smart Card Data Using Bus Information System Data", J. Korea Inst. ITS (2023). Numbers from the abstract as surfaced by search; full text could not be fetched](https://koreascience.kr/article/JAKO202321448561849.pdf)
- **Seoul.** The card system records boarding time and a GPS-based vehicle location. — [Park, Kim & Lim (2008), TRR 2063, record](https://www.worldtransitresearch.info/research/136)
- **Santiago (Transantiago).** Munizaga, Palma & Mora (WCTR 2010) estimate boarding and alighting stops from smart-card and bus GPS data; the abstract gives no validation rate. — [WCTR abstract](https://wctrs-society.com/wp-content/uploads/abstracts/lisbon/general/02988.pdf)
  - A later validation paper (Munizaga et al. 2014) exists; I did not retrieve its numbers. — [record](https://www.worldtransitresearch.info/research/5250)

**India: ETM and GPS linkage**
- **ETM–AVL link.** An ETM can be linked "to the vehicle location system, to provide information for automatic update of fare stage or fare zone". — [SSATP Fares Toolkit, electronic on-board ticket machines](https://www.ssatp.org/sites/ssatp/files/publications/Toolkits/Fares%20Toolkit%20content/fare-collection-technologies/ticket-issuing-machine/electronic,-on-board.html)
- **Delhi (DIMTS).** GPS-based AVL is deployed on all buses, and the ETMs are smart-card enabled with GPRS. — [DIMTS presentation, Geospatial World Forum (search excerpt)](https://geospatialworld.net/gwf/speaker/SpeakersImages/smart-mobility-leveraging-ICT-and-Geo-technologies-DIMTS.pdf)
- **GPS-linked ETMs elsewhere in India.** They auto-set the origin, which only partly fixes origin errors; route, shift and trip are still selected by hand. Conductors also pick different names for the same location. — [GIZ Roadmap (2021), via `etm_ticket_india.md`](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)

**Learned name matching (for the alias step)**
- **Combining similarity metrics.** On a very large toponym dataset, single string-similarity metrics performed similarly to each other, and threshold tuning mattered. Supervised combinations, especially tree ensembles, "significantly outperform[ed] the individual similarity metrics". The abstract gives no figures. — [Santos, Murrieta-Flores & Martins (2017/2018), International Journal of Digital Earth](https://eprints.lancs.ac.uk/id/eprint/89481)
- **Neural matching.** A recurrent neural model over the raw strings beat earlier metrics and learned combiners on GeoNames pairs. — [Santos et al., "Toponym matching through deep neural networks", IJGIS](https://chesterrep.openrepository.com/entities/publication/087657a8-5dc8-4d5b-94ae-0c03f97b788f); [code](https://github.com/ruipds/Toponym-Matching)

**Our data**
- **Data README.**
  - GPS covers "DTC buses only" and is raw ("expect duplicates, gaps and GPS noise").
  - Ticketing "is from ONDC e-ticketing".
  - `vehicle_number` is blank on about half the rows.
  - Source: [Local file: data/raw/ticketing/README.md](../../data/raw/ticketing/README.md)
- **Tickets with and without a vehicle number match alike.**
  - Without a vehicle number: exact 54.3%, fuzzy 18.7%, nearby 5.7%, unmatched 21.3%.
  - With one: 56.9% / 17.9% / 5.3% / 19.9%.
  - Blank share: 48.5%.
  - Source: [Local check](../../data/processed/tickets_matched.parquet)
- **Alias coverage.**
  - 98.6% of no-vehicle tickets have a (route, start name) pair that also appears on tickets with a vehicle number; that rises to 99.9% when matching on the name alone.
  - 97.2% of the unmatched no-vehicle tickets are covered by such pairs.
  - Source: [Local check](../../data/processed/tickets_matched.parquet)
- **Stop spacing on representative patterns.**
  - Consecutive stop spacing: median 460 m (IQR 332–658 m), and 19.7% of gaps are under 300 m.
  - Route length: median 17.0 km (p90 31.7 km).
  - Source: [Local check](../../data/processed/patterns.parquet)

### Inferences
**1. Feasibility.** The alias idea is feasible and its coverage is high (98.6% of no-vehicle tickets by (route, start name)).
- Its accuracy is unknown and must be measured. The closest published benchmark (London, 93–96%) is for taps on entry, not purchases after boarding.

**2. Recommended pipeline**, about 2–3 days in Python with pandas, numpy, rapidfuzz and shapely or geopandas.

**Step 1: Stop passage times.** For each GPS trip in the DTC feed, map-match the points to the route shape or supersequence and interpolate the time the bus passed each stop.
- Drop duplicate points and GPS jumps.
- Require both observations to be within about 2 min of the passage.

**Step 2: Boarding likelihood from the purchase lag.** Model lag Δ = purchase time − passage time.
- Learn the density of Δ from vehicle tickets whose start name is an exact match. That set is a gold standard of about 0.57 × 51.5% ≈ 29% of all tickets.
- The team already sees a median of +0.8 min with 23% of tickets bought before the bus reached the stop.
- Score candidate stops by `p(Δ)`, which is name-agnostic, multiplied by order and fare terms.
- Do not use "the stop nearest the bus at purchase time". At an assumed 15–20 km/h, a 0.8 min lag is about 200–270 m, roughly half the median stop spacing, so the nearest stop is often the next one.

**Step 3: Accept an alias** for a key (route_direction, normalised ticket name) only when all of these hold:
- support ≥ about 20 tickets;
- the top stop holds ≥ about 80% of the posterior mass;
- the stop lies on the route's union of patterns;
- the decision is stable across weeks and time of day.

Rules for the rest:
- Very low name similarity with high purity: accept, but log it for review. This is the case where aliases learn things string similarity cannot, such as "S.J. Hospital" → Safdarjung.
- Low purity: send to review. Typical causes are dense stops, a wrong route or direction, or passengers choosing a terminal.

**Step 4: Key by route-direction, never globally.** Names such as "Health Center", "Telephone Exchange" and "Badarpur" refer to different stops on different routes. Fall back to the route without direction only when the direction-specific key is missing.

**Step 5: Reuse for end names.** Aliases learned from start names also apply to end names on the same route, because they come from the same ticketing route master. GPS cannot confirm alighting, so end names rely on alias, order, fare and trilateration.

**Step 6: Evaluate by masking names.**
- Hide the name on exact-match vehicle tickets and score top-1 accuracy and within-one-stop accuracy of the GPS-only inference, by route group and time of day.
- Then hold out 20% of the alias keys: learn aliases from the rest, apply them to the held-out keys' tickets, and compare with exact names or a manual sample.

**3. Pitfalls to design for**
- **Purchase lag and pre-boarding purchases.** About 23% of tickets are bought before the bus reaches the stop, so a one-sided window would drop them; use a two-sided learned density. Group purchases (pax > 1) may be bought later.
- **Dense stops.** One in five stop gaps is under 300 m, so GPS alone cannot separate neighbours reliably. Combine it with name and order, or accept "stop area" granularity.
- **Coverage bias.**
  - GPS is DTC-only, so vehicle tickets on cluster (DIMTS) buses cannot be GPS-confirmed.
  - The share of vehicle tickets whose `vehicle_number` appears in the GPS feed on the same date and route has not been measured; do this first.
  - Selection bias between tickets with and without a vehicle number looks small on match difficulty (54.3% vs 56.9% exact), but has not been checked by route mix or time.
- **Feedback loops.** Self-training reinforces its own errors: one wrong high-volume alias silently mislabels thousands of no-vehicle tickets. Keep a human gate for the top aliases by volume, and log provenance (`method = gps_alias / name_exact / fare_trilateration / manual`).
- **Drift.** DTC circulars tell IT to update the online ticketing app when stages change (Section 1, 740C). Version aliases by date, and re-learn them monthly or after circulars.
- **Noisy GPS and trip assignment.** London could not link 1.4% of boardings to an iBus route or trip. Expect more in Delhi, where the README warns of duplicates, gaps and noise.

**4. Learned name matcher.** For names that still lack aliases, a gradient-boosted classifier over several similarity features beats any single fuzzy threshold, per Santos et al. Features to use:
- token-set ratio, Jaro–Winkler, character n-gram TF-IDF cosine;
- a flag for an abbreviation-expansion match;
- position and fare consistency.

Train it on the GPS-confirmed aliases plus exact matches as positives, and on same-route non-chosen stops as negatives.

### Gaps
- **No direct precedent.** No literature was found on self-supervised alias or gazetteer learning from GPS-confirmed ticket boardings, and no accuracy for boarding inference where purchase follows boarding (conductor ETM or app QR).
- **Sources not retrieved:**
  - the full Gordon thesis (HTTP 429) and the Wang 2011 match rates;
  - the Munizaga et al. (2014) validation numbers;
  - Beijing accuracy figures (the abstract only says "relatively high");
  - the full Jeju paper (numbers are from its abstract via search).
- **Untested data checks:**
  - the share of ticket vehicle numbers present in the DTC GPS feed;
  - whether the app auto-fills the start stop from the bus's GPS when the QR code is scanned. If it does, start names on vehicle tickets are system-chosen, which changes both the error model and the alias semantics.

---

## 4. Data-quality practice: Delhi GTFS issues, building and validating stop-name crosswalks, human-in-the-loop review

### Takeaway
The Delhi GTFS issues that hurt matching are structural: 65% of stop_ids share a name with another stop, 23% of routes have several patterns, and above all routes without `fare_stage` flags (59% of tickets) match only 32.9% exactly against 88.8% on flagged routes. Practice elsewhere (Swiss ATLAS↔OSM, GTFS validator) is rule cascades with route evidence plus a human problem queue; published crosswalk precision and recall are rare, so the team should label its own sample, and review effort concentrates well (10% of routes hold 60% of unmatched tickets).

### Cited Findings
**Delhi GTFS: provenance and caveats**
- **Official caveat.** OTD's only documented caveat is that stop_times times are "a rough estimate generated by assuming a constant speed of travel". — [OTD Delhi documentation](https://otd.delhi.gov.in/documentation)
- **Provenance.** Chartr describes building India's first open GTFS for Delhi's bus network, covering all DTC and DIMTS routes, stops, schedules and fares, now integrated into the Delhi Transport Stack (a Delhi Transport Department digital public infrastructure). — [Chartr GTFS](https://chartr.in/products/gtfs/); [Chartr Transport Stack](https://chartr.in/products/transport-stack/)

**Local checks on Delhi GTFS and the current matches**
- **Shared names.** 6,862 stops carry only 4,483 distinct normalised names. 2,047 names are shared by two or more stop_ids, covering 4,426 stops (64.5%). Most look like direction pairs on opposite sides of the road; I did not verify that systematically. — [Local check](../../data/raw/gtfs_static/stops.txt)
- **The lineage split** (routes with any `fare_stage=1` vs none):

  | Routes | Share of tickets | Exact | Fuzzy | Nearby | Unmatched |
  |---|---|---|---|---|---|
  | With flags | 40.8% | 88.8% | 4.6% | 1.8% | 4.8% |
  | Without flags | 59.2% | 32.9% | 27.7% | 8.0% | 31.4% |

  Source: [Local check](../../data/processed/tickets_matched.parquet)
- **By agency** (`routes.txt` agency_id):
  - DTC routes, 77.4% of tickets: exact 52.5%, unmatched 21.7%.
  - DIMTS routes, 20.9%: exact 72.1%, unmatched 9.5%.
  - Ticket routes absent from GTFS, 1.8% of tickets: 100% unmatched.
  - Flags exist on 964 of 1,814 DTC routes and 250 of 760 DIMTS routes, so the split is not simply DTC vs cluster.
  - Routes with a "D-" prefix (likely the newer DEVI services; not verified): 6.3% of tickets, a 22.9% unmatched rate, and 7.1% of all unmatched tickets.
  - Source: [Local check](../../data/raw/gtfs_static/routes.txt)
- **Concentration of unmatched tickets.**
  - 1,444 routes have unmatched tickets; the top 10% of those routes hold 60.1% of them.
  - The 15 largest unmatched (route, start name) pairs hold 16,862 tickets (3.2% of unmatched). The largest:
    - ("502UP", "S.J. Hospital") 1,551
    - ("567BSTLUP", "Nangloi (Najafgarh Road)") 1,494
    - ("460DOWN", "Badarpur") 1,316
    - ("D-9101DOWN", "Aerocity") 1,307
    - ("502DOWN", "Mehrauli Terminal") 1,207
    - ("578DOWN", "Health Center") 896
    - ("85UP", "Telephone Exchange") 865
  - Source: [Local check](../../data/processed/tickets_matched.parquet)

**Validator checks and conflation practice**
- **GTFS validator notices that catch misplaced or misordered stops:**
  - `stop_too_far_from_shape`: a published example flags stops more than 100 m from a route shape. — [Survey of errors in US GTFS static feeds (Findings)](https://findingspress.org/article/116694-a-survey-of-errors-in-gtfs-static-feeds-from-the-united-states)
  - `stops_match_shape_out_of_order`: stop A precedes B in the trip but matches later along the shape, which usually indicates bad shapes, bad stop locations, or both. — [OneBusAway wiki, Stop to Shape Matching](https://github.com/OneBusAway/onebusaway-application-modules/wiki/Stop-to-Shape-Matching)
  - Google notes that loops and overlapping sections make stop-to-shape matching hard, and recommends setting `shape_dist_traveled`. — [Google Transit Partners help](https://support.google.com/transitpartners/answer/1095631?hl=en)
- **Human review in ATLAS↔OSM.**
  - Disagreements become "problems" in fixed categories: pair too far apart, no counterpart, conflicting names or platform codes, duplicates, and a match that contradicts route evidence.
  - Reviewers work from a map (unmatched shown in red), a Problems page, route comparisons and reports.
  - Each run re-reads the sources, so fixed items drop off the list.
  - Source: [ATLAS↔OSM Stop Sync docs](https://atlas.osm.ch/docs)
- **PTNA (GTFS vs OSM comparison).** After exact name matching, checking whether the GTFS name is contained in the OSM name is a useful secondary signal. Special characters caused false mismatches. — [OSM Community forum, PTNA GTFS–OSM comparison thread (search excerpt)](https://community.openstreetmap.org/t/ptna-new-feature-gtfs-osm-comparison/109659/5)
- **Errors when snapping stops to networks.** Assigning a bus stop to the wrong side of the road can cause large errors, and stops near crossings tend to be matched to the wrong link. — [Vuurstaek et al., GTFS→OSM mapping (search excerpt)](https://documentserver.uhasselt.be/bitstream/1942/26214/1/gtfsOsm.pdf)
- **pfaedle.** It considers candidate OSM nodes within a radius of each GTFS station. — [Bast & Brosi (2018), sparse map-matching (pfaedle)](https://ad-publications.informatik.uni-freiburg.de/SIGSPATIAL_Sparse%20map%20matching%202018.pdf)
- **Published accuracy is scarce.** A targeted search found no study reporting precision/recall for GTFS-to-OSM stop matching on name and distance. ATLAS reports a match rate only. — [ATLAS↔OSM Stop Sync docs](https://atlas.osm.ch/docs)

**Record-linkage tooling usable for review loops**
- **Splink.** Fellegi–Sunter probabilistic linkage with EM estimation, no training data needed, runs on DuckDB in Python, and its documentation covers evaluation including clerical labelling. — [Splink documentation](https://moj-analytical-services.github.io/splink)
- **dedupe.** Active learning over a Fellegi–Sunter-style model, useful when there is no training data. — [data-matching-software list](https://github.com/J535D165/data-matching-software)

### Inferences
**1. Fix the routes without flags first.**
- They hold about 90% of unmatched tickets: 59.2% × 31.4% ≈ 18.6 points out of 20.6. This group includes the 1.8% of tickets whose route is absent from GTFS.
- Their low exact rate suggests the ONDC ticketing stop master and GTFS v32 come from different lineages for these routes.
- Before engineering, ask Transport Stack / IIIT-Delhi (the data README names IIIT-Delhi's centre as contact) for:
  - the ONDC route-stop master with stable stop IDs;
  - a newer GTFS with `fare_stage` flags on more routes.
- Either could turn the problem into a key join.
- Also check routes not in GTFS (1.8%) and "D-" routes against the latest DTC timetables.

**2. Normalisation dictionary** (one day), built from the failure examples and the 740C circular:
- "S.J." → "Safdarjung"
- "Bdr" → "Border"
- "X-ing" / "Xing" → "Crossing"
- "(T)" → "Terminal"
- "Sect." → "Secretariat"
- "P S" / "P.S." → "Police Station"
- drop "Dr."
- "Centre" / "Center"
- "Hosp" → "Hospital"
- "Mkt" → "Market"
- "Sec" → "Sector"
- "Extn" → "Extension"
- "Ph" → "Phase"
- "Vill" → "Village"
- "Nh8" → "NH-8"
- "Reddison" → "Radisson"

Also:
- Split "A / B" compounds into alternatives, and treat parenthesised qualifiers as optional.
- Add a transliteration key: collapse doubled letters and drop "h" after consonants and the vowels "a"/"aa", so that Najafghar/Najafgarh, Hastal/Hastsal/Hastsaal, Dichau/Dichaon and Kirbi/Kibri collide.

**3. Stop areas.**
- Cluster stop_ids with the same normalised name within about 300 m into "stop areas" (from the 64.5% shared-name stops).
- Match ticket names to areas first, then pick the stop_id that lies on the ticket's route-direction pattern.
- Report crowding at stop_id level only when that pick is unique.

**4. Validation protocol.**
- **Masked exact matches.** Hide names on a random 10% of exact matches and measure top-1 and within-one-stop recovery for each method:
  - route order + fare;
  - trilateration;
  - GPS alias.
- **Manual labelling.** Label a stratified sample of 300–500 (route-direction, ticket name) pairs, by match class × volume decile × route group, with the GTFS map, the route polyline and DTC circulars as references.
- **Report:**
  - precision and coverage, both pair-weighted and ticket-weighted;
  - inter-rater agreement, with about 20% double-labelled.
- **Acceptance.** Accept automatic matches at the score threshold where sample precision is at least about 95%. Everything below goes to review.

**5. Review tool** (half a day).
- A Streamlit or Jupyter + folium page, with the queue sorted by ticket volume.
- For each key show:
  - the route polyline and candidate stops;
  - the fare-trilateration interval;
  - the GPS-inferred boarding histogram;
  - neighbouring anchor names;
  - the DTC circular spelling, where available.
- Decisions go into a versioned CSV crosswalk: `route_dir, ticket_name_norm, stop_id | stop_area_id, method, score, reviewer, date`.
- Because 10% of routes hold 60% of unmatched tickets, a few hours of review on the top roughly 150 routes should move the headline rate a lot.

**6. GTFS hygiene checks.**
- Run the MobilityData validator and look specifically at `stop_too_far_from_shape` and `stops_match_shape_out_of_order`.
- Also flag same-name stops more than 1 km apart on the same route; these are likely wrong locations or genuinely different places.

### Gaps
- **Delhi GTFS defects.** No public documentation was found of Delhi GTFS defects (duplicates, variants, lineage); the figures above are local checks only.
- **Indian crosswalk accuracy.** No published precision or recall for stop-name crosswalks in Indian ETM or e-ticket contexts.
- **ONDC stop master.** Whether the ONDC ticketing stop master has stable IDs, and whether it can be shared, is unknown.
- **`fare_stage` lineage.** Why `fare_stage` flags exist for only 1,214 routes (lineage or version) is undocumented.
