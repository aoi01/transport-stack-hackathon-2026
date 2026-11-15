# Bus on-board load estimation from smart card / AFC / ETM fare data: alighting inference, expansion, and accuracy

Scope note: about 20 search and fetch calls (Nov 2026). Several key full texts (Southwick 2016 MIT thesis, Alsger 2016 TRC, Munizaga 2014 TRC, Gordon 2013 TRR) could not be opened. The search engine sometimes paraphrased snippets, or an MIT server returned HTTP 429, so some headline numbers come from abstracts or secondary citations. These are flagged where it matters. Numbers I remember from training but could not re-verify are in Gaps, not in Findings.

Common method in the literature: the "trip-chaining" rule set, first set out by Barry et al. (NYC, 2002) and Zhao/Rahbee/Wilson (Chicago, 2007), then generalized as MIT's ODX (Gordon 2012/2013). It assumes:
1. A rider's next boarding stop, or the first boarding stop for the last trip of the day, is near where they alighted.
2. The candidate alighting stop is the downstream stop on the boarded trip that is closest to that next origin, within a maximum walking distance (typically 400 to 1,100 m).
3. AVL/GPS timestamps give the alighting time, and a time-feasibility check is applied (the rider must get there before the next tap).
4. Trips that can't be chained, for example a single tap per day or a distance over the threshold, are left "unlinked" and handled later in expansion/scaling.

---

## Q1. What share of trips can typically be assigned an alighting stop, and how accurate is it when validated?

### Takeaway
Most studies infer a destination for about 70 to 90% of fare-media boardings on large networks with one integrated card (London about 75 to 77%, Chicago about 70%, NYC about 90%, Santiago over 80%, Changzhou 80%). The rate drops sharply when the data covers only part of the network or some operators: Changsha had about 27% of records chainable. Where true alightings exist (tap-on/tap-off systems used as ground truth), exact-stop accuracy is about 72 to 80% (Brisbane/SEQ). Accuracy within a tolerance such as 400 m or a zone is about 79 to 90%+. Headline "inference rates" are not accuracy, and many studies never validate against real alightings.

### Cited Findings
**London (TfL Oyster + iBus AVL; MIT ODX)**
- Gordon, Koutsopoulos, Wilson & Attanucci (2013), TRR 2343:17–24, "Automated Inference of Linked Transit Journeys in London Using Fare-Transaction and Vehicle Location Data". Inputs: Oyster bus taps (entry-only) plus iBus AVL. Underlying thesis: Gordon (2012, MIT). — [WTR record](https://www.worldtransitresearch.info/research/4986); [MIT DSpace thesis](https://dspace.mit.edu/handle/1721.1/78242)
- Figures quoted in a 2013 workshop deck by Nigel Wilson (via MIT OCW 1.258J lecture 10 materials) for London bus: origin inference 96%, destination inference 77%. The full-day London OD matrix, including seed matrix and scaling, ran in about 30 minutes on an Intel PC. These are secondary slide figures, not the paper itself. — [MIT OCW 1.258J Lecture 10 PDF](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/34a43911aaac62cc71eac31baa0521b1_avWOCswUJyI.pdf)
- Tang et al. (Leeds/Changsha) cite chainable shares from earlier studies: about 75% London (Gordon et al. 2013), 70% Chicago (Zhao et al. 2007), 90% New York (Barry et al. 2002). — [Tang et al., White Rose eprint](https://eprints.whiterose.ac.uk/153460/1/Tang%20et%20al%20-%20SCS%20-%20alighting%20stop%20estimation%20-%20WR.pdf)
- Wang, Attanucci & Wilson (2011), J. Public Transportation 14(4):131–150. Applies trip chaining to Oyster plus AVL for London buses. Described as the first known attempt to validate against a manual passenger survey, the TfL Bus OD Survey (BODS). Its thesis compares BODS, ETM and Oyster data for surveyed trips. Exact validation percentages were not retrieved. — [MIT DSpace article](https://dspace.mit.edu/handle/1721.1/110021); [Wang 2010 thesis](https://dspace.mit.edu/handle/1721.1/60814)

**Santiago (bip! card + bus GPS; basis of ADATRAP)**
- Munizaga & Palma (2012), TRC: estimates alighting time and position for more than 80% of boarding transactions, using two 1-week datasets. Cases it cannot estimate: users with only one transaction per day, non-integrated fare modes, and fare evaders. — [repositorio.uchile.cl](https://repositorio.uchile.cl/handle/2250/112102)
- Munizaga, Devillaine, Navarrete & Silva (2014), TRC 44:70–79, "Validating travel behavior estimated from smartcard data". Exogenous validation using volunteers who reported their real trips. Correct-estimation percentages were reported as about 90% in all cases. Search summaries do not state the distance tolerance. — [repositorio.uchile.cl](https://repositorio.uchile.cl/handle/2250/126684); [WTR](https://www.worldtransitresearch.info/research/5250)
- Devillaine, Munizaga, Palma & Zúñiga (2013) propose endogenous checks (internal consistency, used to find errors) and exogenous checks (survey or volunteer comparison). One Santiago check used a detailed OD survey of about 300,000 metro users. — [Emerald chapter](https://emerald.com/insight/content/doi/10.1108/9781781902882-038)

**Brisbane / South-East Queensland (go card, tap-on AND tap-off, so ground truth exists)**
- Alsger, Assemi, Mesbah & Ferreira (2016), TRC 68:490–506. Runs the standard trip-chaining algorithm while hiding the recorded tap-offs, then compares. The proposed changes cut the mean distance between actual and estimated alighting stops from 806 m to 530 m. — [WTR 5965](https://www.worldtransitresearch.info/research/5965)
- Alsger et al. (2015), TRR 2535. Tests the trip-chaining assumptions, including allowable walking distance, on go card data. The literature uses walking thresholds of 400, 800, 1,000 and 1,100 m. — [SAGE TRR 2535-10](https://journals.sagepub.com/doi/10.3141/2535-10); [WTR 5914](https://www.worldtransitresearch.info/research/5914)
- A Brisbane go card study reports destination estimation accurate for 79% of trips within 400 m, plus 1.4% more destinations resolved after calibration. — [search summary of WTR/related record](https://www.worldtransitresearch.info/research/5965) (exact paper not pinned down; treat as indicative)
- Assemi, Alsger, Moghaddam, Hickman & Mesbah (2020), Public Transport 12:89–? (DOI 10.1007/s12469-019-00218-9). Neural networks correct trip-chaining errors. Exact-stop accuracy rose from 72.2% to 79.5%. Mean error on wrongly estimated stops fell from 1,689 m to 503 m, and zone-level accuracy improved by more than 5%. Errors correlate with zone and transaction attributes, which undermines the "nearest stop to next boarding" assumption. — [WTR 7783](https://www.worldtransitresearch.info/research/7783); [IDEAS](https://ideas.repec.org/a/spr/pubtra/v12y2020i1d10.1007_s12469-019-00218-9.html); accuracy pair also cited in [arXiv 2608.11223](https://arxiv.org/html/2608.11223)

**Gatineau, Canada (STO)**
- Trépanier, Tranchant & Chapleau (2007), J. ITS 11(1):1–14. Destination estimated from the sequence of boarding stops. The Gatineau algorithm was later calibrated and validated against Brisbane data (He & Trépanier 2015). — [TRID](https://trid.trb.org/View/804750); [Polytechnique Montréal](https://publications.polymtl.ca/21334)

**China**
- Changsha (Tang et al.; 6 months of IC card + GPS, 7 lines). 31.7% of raw records were unusable: 6.3% duplicates, 9.9% with no GPS match, 15.5% with no boarding stop. Only 26.7% of records fell in chainable types X1+X2. 38.3% could not get an alighting stop. The low rate is explained by a subnetwork with multiple operators, which breaks trip chains. A GBDT model trained on the chained trips achieved GEH < 5 at 98% of stops, and the load profile matched the max-load stop. The "ground truth" was itself trip-chained estimates, which the authors acknowledge as a limitation. — [Tang et al. eprint](https://eprints.whiterose.ac.uk/153460/1/Tang%20et%20al%20-%20SCS%20-%20alighting%20stop%20estimation%20-%20WR.pdf)
- Changzhou (May 2025; 838k taps, 43 routes, flat fare, entry-only) with a Hierarchical Bayesian Latent-Destination model. Chaining rate: 80.4% (71.0% same direction, 7.2% opposite direction, 2.3% recurrence imputation); 19.6% unchained. There were no true alightings, so scores measure agreement with chain labels. Full model top-1 51.2%, top-3 71.5%, top-5 79.8%. Top-1 is 68.2% with card history and 26.5% for cold-start cards. — [arXiv 2608.11223](https://arxiv.org/html/2608.11223)
- Shenzhen (Sari Aslam et al. 2024, Transportation Planning & Technology). Bus card-to-GPS boarding-stop match is 59% exact, rising to 62/70/71% with ±2/3/4-minute windows. After cleaning, 69% of journeys remain. Validation was possible only on the subway, which has tap-out: last-location accuracy 90.05 to 92.15% with inferred home location, versus 81.01% without. — [UCL Discovery PDF](https://discovery.ucl.ac.uk/id/eprint/10195948/1/Alighting%20location%20estimation%20from%20public%20transit%20data%20%20a%20case%20study%20of%20Shenzhen.pdf)

**Seoul / Korea (distance-based fares; tap-off mandatory)**
- Lee et al. (2021), Applied Sciences, "Estimating Destination of Bus Trips Considering Trip Type Characteristics". Seoul-area bus alighting tag rate was 98% (Apr 2020), so tap-off data serves as nearly 100% ground truth for testing estimators meant for single-fare cities. Accuracy percentages were not retrieved. — [DOAJ](https://doaj.org/article/a36b09c8568d409d87326073d0b9faa8); [preprint](https://www.preprints.org/manuscript/202109.0396)

**Other**
- Kumar et al. (2018): ranking candidate trajectories raised inference coverage from 70% to 85% (city not given in the citing text). — cited in [arXiv 2608.11223](https://arxiv.org/html/2608.11223)
- A review states that most alighting studies report 75 to 96% accuracy. It notes that "most researchers have evaluated an inference rate based on rules they set", not true alightings. — [UW thesis "Smart Card Data Mining and Inference for Transit System"](https://digital.lib.washington.edu/server/api/core/bitstreams/6b4d62b5-745e-497d-9d51-d831288129b6/content)
- Deep learning on entry-only data: Jung & Sohn (2017), IET ITS, forecast bus destinations with a deep-learning architecture (Korea). — [Wiley](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-its.2016.0276)
- Review: Hussain, Bhaskar & Chung (2021), TRC 125:103044. Covers cleansing, estimating unknowns (destination inference), transfer detection, validation and OD scaling. — [WTR 8473](https://www.worldtransitresearch.info/research/8473); [PolyU](https://research.polyu.edu.hk/en/publications/transit-od-matrix-estimation-using-smartcard-data-recent-developm/)

### Inferences
- Rough expectations: about 70 to 85% of fare-media boardings get a destination. Of those, about 70 to 80% are the exact stop and about 80 to 90% are within about 400 m or the correct zone. Combined, roughly 55 to 65% of all fare-media boardings end up with a correct exact alighting stop. The rest must be distributed probabilistically.
- Network completeness matters more than the algorithm. If only some operators or routes are in the data (Changsha), chaining collapses. For Delhi, if ETM data covers DTC but not cluster (DIMTS) buses, or excludes metro, chaining will break at those transfers.
- Accuracy degrades for single-trip-per-day users and cold-start cards (top-1 26.5% vs 68.2% in Changzhou). Using a card's history and symmetry (the first origin of the day as the destination of the last trip) is the main lever.

### Gaps
- Exact figures often quoted from memory could not be re-verified: Trépanier 2007 (about 66%), Zhao 2007 (about 71% rail), Nassir et al. 2011 Minneapolis, Wang 2011 BODS validation percentages, and Munizaga 2014 distance tolerance. Full texts were not accessible.
- No validated alighting accuracy found for Netherlands OV-chipkaart, Singapore EZ-Link, Japan IC cards, or Beijing in this pass. All are tap-in/tap-out systems, so alighting is observed, not inferred.

---

## Q2. How accurate are resulting stop-level / segment-level load profiles vs APC or manual counts?

### Takeaway
Few published studies report formal load error metrics (MAPE/RMSE) for AFC-derived loads against APC. The MIT MBTA work (Southwick 2016) gives the strongest evidence: trip-level scaled ODX loads are "reliable" for about 90% of bus trips and broadly similar to APC, with trip-level variability. APC is itself noisy: Pearson r = 0.661 against a card dataset, undercounting on crowded trips, and video-APC load drift corrected to RMSE ≈ 9 passengers against manual counts. Validate against manual ride checks where possible, and treat APC as a noisy reference.

### Cited Findings
- Southwick (2016), MIT SM thesis "Understanding Bus Passenger Crowding Through Origin Destination Inference" (MBTA). Components: trip-level ODX scaling, passenger-centric crowding metrics, and estimating crowding sources. Scaling that accounts for passengers not using smart media gives reliable load estimates for about 90% of MBTA bus trips. Against APC, ODX loads show inherent variability, but many trips are similar to APC. Detailed error statistics were not retrieved: the PDF fetch returned HTTP 429. — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/104323)
- Changsha (Tang et al.): the estimated load profile per line matches the max-load stop of the reference with small differences in peak magnitude, and 98% of stops have GEH < 5. The reference was chain-inferred, not observed. — [Tang et al.](https://eprints.whiterose.ac.uk/153460/1/Tang%20et%20al%20-%20SCS%20-%20alighting%20stop%20estimation%20-%20WR.pdf)
- Xu, Zhou, Wang & Sun (2026), arXiv 2605.19834. Closed-loop load estimation that fuses video APC, Wi-Fi counts and context, with stop-by-stop recursion and constraints (load ≥ 0, load ≤ capacity C = 80, alighting ≤ load). Ground truth: onboard manual counts. RMSE 9.13 ± 0.90 and MAE 7.04 ± 0.62 passengers with physical projection, versus RMSE 20.57 for open-loop perception, and an unconstrained fusion failure case at 19.98 ± 5.46. Illustrates cumulative drift in boardings-minus-alightings recursion and why feasibility constraints matter. It also notes that AFC combined with partial-fleet APC is used to infer occupancy on non-APC trips (their ref [20]). — [arXiv 2605.19834](https://arxiv.org/pdf/2605.19834)
- APC as a reference: a 2026 arXiv appendix reports APC counts versus a smart-card dataset Pearson r = 0.661, with APC systematically undercounting on crowded trips. — [arXiv 2605.00083](https://arxiv.org/pdf/2605.00083). European field study: APC tends to undercount boardings, with better accuracy at lower volumes and simpler door layouts. — [ResearchGate](https://www.researchgate.net/publication/338601680_Empirical_Study_on_the_Accuracy_and_Precision_of_Automatic_Passenger_Counting_in_European_Bus_Services). IR APCs are said to overestimate loads by a statistically significant margin. — [USPTO 10850588](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10850588). Italy review: aggregate APC is accurate, with slight overestimation of exits. — [ScienceDirect](https://www.sciencedirect.com/org/science/article/pii/S1874447825000077)
- MBTA fare-compliance work (2024) reconciles APC boardings and AFC taps per stop event, flagging APC errors such as negative or implausible non-interaction counts, and blocked sensors. Data covered more than 787,000 boardings. — [MassDOT/ROSAP](https://rosap.ntl.bts.gov/view/dot/81919/dot_81919_DS1.pdf)
- Older farebox versus ride-checker comparisons (AC Transit, TRR 1202, 1988): large discrepancies were often due to matching problems, not counting error. — [TRR 1202](https://onlinepubs.trb.org/Onlinepubs/trr/1988/1202/1202-003.pdf)

### Inferences
- The MAPE/RMSE of AFC loads versus APC is under-reported in the literature. A hackathon team reporting stop-segment MAE/RMSE and peak-load-point accuracy would add something new.
- Errors accumulate in the load recursion (load_k = load_{k-1} + board_k − alight_k). Enforce non-negativity and capacity, and force everyone off at the terminal. This clean-up cut RMSE by more than half in the video-APC study.
- Peak-load-point location is typically more robust than absolute peak magnitude (Changsha). Report both.

### Gaps
- No published load MAPE/RMSE was found for Santiago ADATRAP, London, or Seoul bus loads against APC. Southwick's numeric APC comparison could not be extracted.

---

## Q3. How do studies scale sampled/partial data to total ridership, and how do they quantify uncertainty?

### Takeaway
Standard practice has two steps. First, scale inferred-journey flows to observed counts per vehicle trip or route segment, using farebox/ETM totals, APC or gate counts (ODX scaling, Gordon et al. 2018; Southwick 2016 trip-level). Second, distribute boardings with no inferred destination using the inferred alighting distribution from the same trip, route or time band, or by IPF/EM against APC boardings and alightings. Uncertainty is rarely quantified. Recent Bayesian work gives posterior intervals: for example, the median OD flow range is 13.3% across reliability assumptions.

### Cited Findings
- Gordon, Koutsopoulos & Wilson (2018), TRC, "Estimation of population origin–interchange–destination flows on multimodal transit networks". Scales passenger-journey flows using passenger counts at each station gate and bus farebox, estimating flows of non-AFC passengers and of AFC passengers whose journeys were not inferred. — [WTR 6836](https://www.worldtransitresearch.info/research/6836)
- Southwick (2016): trip-level scaling to include passengers not using smart media (MBTA), with reliable loads for about 90% of bus trips. — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/104323)
- Route-level OD from APC counts: Ji, Mishalani & McCord, an IPF-based algorithm starting from a base OD and fitted to trip-level APC boardings and alightings. McCord et al. (2010) tested IPF with a null base against a field experiment with observed true OD. An EM method combining a small on-board survey with APC beats IPF when APC data are plentiful (2015). The IPF-Iterative Base variant (WCTR 2013). Mishalani/Ji/McCord (2011) studied the effect of survey sample size. — [WTR 3545](https://www.worldtransitresearch.info/research/3545); [ASCE](https://ascelibrary.com/doi/10.1061/%28ASCE%29TE.1943-5436.0000647); [WCTR abstract](https://wctrs-society.com/wp-content/uploads/abstracts/rio/general/3404.pdf); [arXiv 1911.05777 review of limits](https://arxiv.org/pdf/1911.05777)
- Bayesian time-varying OD from boarding/alighting counts: — [arXiv 2403.04742](https://arxiv.org/html/2403.04742v2)
- Changzhou HBLD (2026) uncertainty: 100 posterior draws give OD predictive intervals. Reliability-scenario bands vary the chain-label reliability π. For OD pairs with ≥ 50 expected trips, the median flow range across π is 13.3% of mean flow, above 27.1% for the most sensitive 10%. Day-clustered bootstrap 95% CIs are used for ablations. The authors warn the intervals are conditional on the hyperparameters. — [arXiv 2608.11223](https://arxiv.org/html/2608.11223)
- Coverage gaps that scaling must cover: cash fares (TriMet ODX excludes cash; card IDs rotated), users with one tap per day, non-integrated modes, and fare evaders (Santiago). — [TriMet Mobility Data PDF](https://trimet.org/imi/pdf/Mobility%20Data.pdf); [repositorio.uchile.cl](https://repositorio.uchile.cl/handle/2250/112102)
- CTRF 2025 session title "Enhancing Transit Smart Card Destination Estimation Algorithm Using Count Data" shows count-data fusion is still active (no abstract accessible). — [sched](https://ctrf2025.sched.com/event/21JOf/enhancing-transit-smart-card-destination-estimation-algorithm-using-count-data)

### Inferences
- For Delhi ETM, each paper ticket is a sale. Expansion is mostly about passengers who generate no ticket: pass holders, free "pink ticket" riders (if not recorded with a stop), fare evaders, and staff. The scale factor per trip = (estimated true boardings, from APC or manual sample or ticket-to-count ratios) ÷ (ETM tickets). Apply it per trip × time band, not globally.
- Quantify uncertainty with (a) bootstrap over days/trips, (b) scenario bands over unknowns such as the pass-holder share and alighting distribution for unlinked riders, and (c) posterior sampling if using a Bayesian model.

### Gaps
- No published uncertainty figures for London/Santiago production load estimates were found. Gordon 2018 scaling error metrics were not retrieved.

---

## Q4. Which open-source tools/code exist?

### Takeaway
Public code is thin. The main public ODX implementation is UrbanLogiq's ODX for TriMet (Python/kedro, Docker). Robert Dumas's thesis site documents a bus ODX design. Most academic implementations (MIT ODX for TfL/MBTA/CTA, Santiago ADATRAP) are not public.

### Cited Findings
- UrbanLogiq / TriMet ODX: infers Origin/Destination/Transfer events for TriMet riders, structured as a kedro pipeline, with Docker recommended. Input is a transaction journal of boarding taps (date, time, stop ID, line ID, card ID; rotated IDs; cash excluded). — [GitHub urbanlogiq/odx](https://github.com/urbanlogiq/odx); [TriMet Mobility Data](https://trimet.org/imi/pdf/Mobility%20Data.pdf)
- Robert Dumas thesis, ODX algorithm chapter (bus origin, destination and interchange inference): — [radumas.info/thesis/ODX](https://radumas.info/thesis/ODX)
- Lisbon IST thesis applying ODX to a multimodal network (Carris/Metro): — [IST thesis PDF](https://fenix.tecnico.ulisboa.pt/downloadFile/1689244997263080/tese_rl_12_02.pdf)
- MIT OCW 1.258J lecture 10, "Origin, Destination, and Transfer Inference": slides covering ODX rules. — [MIT OCW](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/34a43911aaac62cc71eac31baa0521b1_avWOCswUJyI.pdf)

### Inferences
- For a hackathon, a minimal ODX is about 200 lines of pandas plus a KD-tree over GTFS stops. Chaining is (card_id, day) sorted by time, then the next origin stop is mapped to the nearest downstream stop on the current trip's GTFS stop sequence within 400 to 800 m, with a time-feasibility check. Reimplementing is likely faster than adapting the TriMet repo.

### Gaps
- Not verified whether the urbanlogiq/odx repo is still maintained or licensed permissively. No public ADATRAP code was found.

---

## Practical takeaways for the Delhi task (ETM tickets + GTFS, bus only)

- **Check first whether Delhi ETM tickets already carry a destination.** Indian stage-fare ETM tickets generally record origin, destination, number of passengers, fare, ticket type and route. Example: KSRTC Trivandrum ETM data includes "number of passengers, fare, ticket type, route, origin, destination and the time". — [ETM analytics (IEEE/ResearchGate)](https://www.researchgate.net/publication/325983769_Electronic_ticket_machine_data_analytics_for_public_bus_transport_planning); [IEEE 8390198](https://ieeexplore.ieee.org/document/8390198/). If so, alighting inference is unnecessary for ticketed riders. Loads come directly from cumulative boardings minus alightings per trip, which ETM studies note can yield link volumes and stop-level load. The hard part shifts to (a) passes and free tickets without a stop, (b) stage or fare-band destinations that need mapping to a stop and are ambiguous across a stage, and (c) evaders. If tickets have no ID linking repeated rides, trip chaining is impossible anyway, because paper tickets are anonymous.
- **If the destination is a fare stage, not a stop,** spread alightings uniformly or by stop attractiveness across the stops in that stage. Stage-level accuracy is analogous to zone-level accuracy, which is higher than exact-stop accuracy (Assemi 2020 shows a gap of more than 5 points).
- **Build loads with physical constraints:** load ≥ 0, ≤ capacity (crush load), everyone off at the last stop, and alightings ≤ current load. This roughly halves RMSE in the video-APC case. — [arXiv 2605.19834](https://arxiv.org/pdf/2605.19834)
- **Expansion:** use per-trip and per-time-band factors where any count ground truth exists. Otherwise use scenario bands for pass and free-rider shares. Report the uncertainty band.
- **Validation metrics to report:** segment-level MAE/RMSE (passengers), MAPE on peak-load segment, peak-load-point hit rate, and GEH < 5 share (used by Tang et al.). Without ground truth, use holdout consistency checks such as recovering hidden destinations from tickets that have them.
- **Matching tickets to GTFS trips and stops:** ETM time plus route to GTFS trip, and AVL/GPS if available. Shenzhen got only a 59% exact match, 71% with a ±4-minute window, so expect material loss and use time windows. — [UCL Shenzhen](https://discovery.ucl.ac.uk/id/eprint/10195948/1/Alighting%20location%20estimation%20from%20public%20transit%20data%20%20a%20case%20study%20of%20Shenzhen.pdf)
