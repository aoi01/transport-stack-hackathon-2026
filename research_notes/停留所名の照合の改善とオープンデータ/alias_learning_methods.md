# Resolving ticket stop names beyond string normalisation: GPS-based boarding inference and alias learning, Indian ETM practice, corridor geocoding, record linkage / LLM matching, and evaluation without gold labels (Delhi ONDC e-tickets)

Research date: 2026-11-16. Scope: methods a small team can build in about a week to resolve the free-text boarding and alighting names on Delhi ONDC e-tickets to GTFS stops, using vehicle GPS (AVL), fares, route order and gazetteers, with reported accuracies and practical thresholds.

This note goes deeper on the gaps left by `../停留所名の照合と通過検出/transit_stop_matching.md` and `../停留所名の照合と通過検出/indic_name_matching.md` and does not repeat them. Detecting when a bus passes a stop from GPS is covered in `../停留所名の照合と通過検出/gps_stop_passage.md`.

Markers used below:
- **[search excerpt]**: I saw the claim only in a search-engine summary or snippet; the page itself could not be fetched (HTTP 403/429, SSL error or connection reset). Treat it as weaker evidence.
- **Local check**: computed by me on 2026-11-16, read-only, on `data/processed/tickets_matched.parquet` (2,559,899 tickets; the team's current matches) and `data/raw/gtfs_static/`. Nothing from `data/` was sent to any external service. Names were only lower-cased and stripped, so key counts are approximate.
- Derived numbers (Wilson bounds, sample sizes, distances travelled during the purchase lag) are my own arithmetic and appear under Inferences.

Headline findings:
1. **No direct precedent.** I found no published study, in India or elsewhere, that learns a name→stop alias table from GPS-confirmed boardings, or that models the lag of a ticket bought on board after boarding. The nearest precedents:
   - tap-on matching in London (93% within ±1 min of an iBus stop event);
   - Shenzhen's ±2–4 min matching windows (67–72% of bus transactions matched; failures came from GPS gaps);
   - Fortaleza, where a passenger can pass the turnstile long after boarding; the authors' fix was to move a regular user's origin to their earliest validation point;
   - MBTA's correction for farebox clock drift.
2. **Indian ETM data is ID-based.** BMTC's ETM rows carry "from" and "till" stop IDs and stop sequence numbers. So Indian studies rely on the operator's stop master instead of matching names, and I found no Indian study that reports the accuracy of mapping ETM or app ticket names to GTFS.
   - In Delhi, DTC has issued pre-printed stage tickets since its ETMs were phased out in September 2022. DIMTS cluster ETMs record origin, destination and fare stage.
3. **Acceptance rules for aliases must be borrowed from other fields:**
   - entity-linking priors: count(m,e)/count(m), pruning at about 0.065, and the finding that priors drift over time;
   - counting distinct contributors rather than records;
   - container constraints. In Doerr & Papagelis, the precision of one-to-one place-name matches rose from 91.9% to 96.2% when the containing country was known.
4. **Local check:** there is plenty of GPS-checkable support for start names. 87.7% of unmatched tickets have at least 10 vehicle-numbered tickets with the same (route-direction, start name). End names, however, must pool both directions: the share of unmatched tickets whose end name never appears as a start name falls from 20.4% (same direction) to 4.6% (both directions pooled).

---

## Q1. Using AVL/GPS at transaction time to infer boarding stops and to learn name→stop aliases (lag modelling, acceptance thresholds, avoiding self-reinforcing errors)

### Takeaway
Join each vehicle-numbered ticket to the stop-passage times of that bus. Score every stop on the route with a two-sided purchase-lag density learned from the data, not with "the stop nearest the bus at purchase time". Then pool the scores by (route-direction, normalised name).

Accept an alias only when all of these hold:
- enough independent support: at least 20 tickets and at least 5 distinct vehicle-days;
- a clear majority: the 95% Wilson lower bound on the top stop's share is at least 0.5, or the top two adjacent stops together hold at least 0.8;
- the same answer in both halves of the month.

Published accuracy exists only for tap-on validation (London 93–96%). Purchase after boarding is not modelled anywhere I could find, so the team has to measure accuracy itself by hiding the names of exact-match tickets. Keep the GPS evidence and the name evidence as separate views, so that neither is ever trained on the other's output.

### Cited Findings
**Origin inference where the fare transaction happens at boarding**
- **London (Oyster + iBus).** Already in `transit_stop_matching.md`. 96% of boardings are inferred within ±5 min of an iBus stop event and 93% within ±1 min. Only 28% fall between the iBus arrival and departure times. 1.4% could not be matched to an iBus route or trip. — [MIT 1.258J Lecture 10 (2017)](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- **Seoul and Brisbane** record a tap at boarding and at alighting, so the boarding stop is known. Shenzhen buses are entry-only: the card record has only the boarding time and the route. — [Sari Aslam et al. 2024, "Alighting location estimation from public transit data: a case study of Shenzhen", Transportation Planning and Technology, doi:10.1080/03081060.2024.2382247](https://discovery.ucl.ac.uk/id/eprint/10195948/1/Alighting%20location%20estimation%20from%20public%20transit%20data%20%20a%20case%20study%20of%20Shenzhen.pdf)
- **Shenzhen boarding method** (same paper):
  - Step 1 joins card and GPS records on date, bus plate number, route and trip start time. This exact join located 59% of bus boardings (9,089,850 records).
  - For the rest, the authors searched time windows around the card time, because the two clocks disagree and GPS points are missing. They cite GPS position errors of 10–100 m.
  - Windows of ±2, ±3 and ±4 min raised the match rate to 67%, 71% and 72%. Forward-only windows of 2, 3 and 4 min gave 62%, 70% and 71%.
  - They chose ±4 min (11,092,699 records matched). About 30% of bus card records still could not be matched, which they attribute to missing GPS data.
  - There was no ground truth for bus boarding stops, so no accuracy figure is reported for them.
- **Chinese practice: dwell-window rule** [search excerpt]. One study takes the GPS position whose timestamp is closest to the card tap. It notes that the GPS timestamp usually comes slightly before the tap, because passengers tap after the bus has stopped. A tap counts as valid only if it falls between the bus's GPS arrival and departure times. — [Applied Sciences 9(17):3597 (2019), "Citywide Metro-to-Bus Transfer Behavior Identification Based on Combined Data from Smart Cards and GPS"](https://www.mdpi.com/2076-3417/9/17/3597)
- **Santiago.**
  - Munizaga & Palma (2012) estimate alighting time and position for more than 80% of boarding transactions [search excerpt]. — [record](https://typeset.io/papers/estimation-of-a-disaggregate-multimodal-public-transport-1ztsj3c5dy)
  - A 2014 validation against three sources (the same database, a Metro OD survey with registered card numbers, and volunteers) reports about 90% correct estimates in all cases [search excerpt]. — [Munizaga, Devillaine, Navarrete & Silva 2014, TR-C 44](https://www.worldtransitresearch.info/research/5250)
  - A webinar reports 84% correct alighting position and time against a small OD survey (secondary source) [search excerpt]. — [Munizaga webinar 2014](https://de.slideshare.net/BRTCoE/webinar-using-smart-card-and-gps-data-for-policy-and-planning-the-case-of-transantiago)
- **Brisbane.** South-East Queensland data contain both boarding and alighting stops, so trip-chaining assumptions can be tested against them. The authors' revisions cut the mean distance between actual and estimated alighting stops from 806 m to 530 m [search excerpt]. — [Alsger, Assemi, Mesbah & Ferreira 2016, TR-C 68](https://www.worldtransitresearch.info/research/5965)
- **Chicago (CTA bus).** Cui's 2006 MIT thesis builds a bus OD matrix from a seed matrix based on fare-card (AFC) data, with boarding and alighting totals from passenger counters. It reports results for route segments of 3–5 combined stops. I found no published share of CTA bus transactions with inferred origins [search excerpt]. — [Cui 2006, DSpace@MIT](https://dspace.mit.edu/handle/1721.1/37970)
- **Beijing, Jeju and Seoul** are covered in `transit_stop_matching.md`. In Jeju, card boarding-stop errors fell from 6.2% to 1.0% after a correction using the bus information system. — [J. Korea ITS 2023](https://koreascience.kr/article/JAKO202321448561849.pdf); [Park, Kim & Lim 2008](https://www.worldtransitresearch.info/research/136)

**Systems where the transaction can lag boarding**
- **Fortaleza** (Caminha, Furtado, Pinheiro & Ponte, Unifor, 2016).
  - Validation records give only the time the card passed the bus turnstile. The authors looked up the bus's GPS position at that time, but note it may not be the passenger's origin: a passenger can stay at the back of the bus and pass the turnstile much later.
  - Their mitigation: for a regular user, move every origin to that user's earliest validation point seen across the days analysed.
  - Data: March 2015, 4,783 georeferenced stops, 359 routes, about 104 million GPS records.
  - The paper does not quantify the lag.
  - Source: [arXiv 1606.04190](https://arxiv.org/abs/1606.04190)
- **Conductor-issued ETM tickets in India** (GIZ roadmap):
  - Origin and destination often contain significant errors, because conductors lack time to enter them in crowded buses.
  - ETMs that set the origin automatically from the bus location reduce this "to some extent", but route, shift and trip are still entered by hand.
  - Different conductors pick different names for the same place.
  - Source: [GIZ/Changing Transport, Roadmap for Data-driven Transformation of Indian Bus Systems (2021), pp. 4–5](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- **Chennai MTC GPS-fitted ETMs.**
  - A trial on more than 200 buses failed because tickets took too long to issue: about 8 s per ticket against 4 s on the old ETMs and at most 2 s by hand.
  - The battery lasted three hours.
  - The conductor punched codes for the boarding and destination stops.
  - Source: [Raghavendran et al. 2017, IJMET 8(10), §3.1](https://iaeme.com/MasterAdmin/Journal_uploads/IJMET/VOLUME_8_ISSUE_10/IJMET_08_10_012.pdf)
- **Delhi ticket channels** (Urban Catalysts for HVT, August 2024):
  - The One Delhi app sells tickets on board, using the bus number or the QR code on e-buses.
  - Tummoc lets users pre-book by origin and destination.
  - Since April 2024 a WhatsApp chatbot sells tickets after the user states origin and destination.
  - At Mayapuri depot in March 2024, 28% of tickets were bought through apps and 72% from conductors.
  - The One Delhi app does not record origin and destination for women's free tickets.
  - Source: [Framework to collect and analyse gender disaggregated travel data (2024), pp. 8–10](https://ride.transport-links.com/wp-content/uploads/TUC_Framework-for-collection-of-gender-disaggregated-data_10102024-8.pdf)

**Clock offsets and time tolerance**
- **MBTA** [search excerpt]:
  - Farebox clocks drift slowly, and a timing error of more than a few seconds can make the inference pick a different origin stop.
  - The fix interpolates each farebox's clock error between calibrations. The drift is measured by logging the garage server's connection to the farebox in both systems just before calibration.
  - The same chapter says some systems, London Buses among them, avoid origin inference by integrating AVL and fare collection on board so each transaction gets a location.
  - Source: [R. Dumas thesis, Ch. 2 "Origin, Destination, and Interchange Inference at the MBTA"](https://radumas.info/thesis/ODX)

**How accurate GPS-derived stop times are at 10–30 s sampling** (more in `gps_stop_passage.md`)
- **Interpolation error.** Interpolating bus times between AVL polls can produce errors almost as large as the polling interval where bus speed varies widely [search excerpt]. — [National Academies Press, TCRP AVL report, ch. 12](https://nap.nationalacademies.org/read/13907/chapter/12)
- **Singapore.** On noisy arrival-time records, interpolation reduced arrival-time error by up to about 30% for some services. Precision and recall exceeded 80% when an error of up to 1 min was allowed [search excerpt]. — [Meegahapola et al. 2019, arXiv 1907.08483](https://arxiv.org/abs/1907.08483)
- **Cambridge.** AVL samples arrive every 20 or 30 s, and each location is accurate to about ±30 m [search excerpt]. — [Bejan et al., ITSC 2010](https://www.cl.cam.ac.uk/~arb33/papers/BejanAEtAl-StatisticalModellingAndAnalysisOfSparseBusData-ITSC2010.pdf)

**Analogues for alias acceptance thresholds** (none come from transit)
- **Entity-linking priors.** The mention→entity prior is estimated as count(m,e)/count(m) over anchor links.
  - Source for the prior: [arXiv 2202.13404](https://arxiv.org/abs/2202.13404)
  - One multilingual system ignores anchors whose prior is below 0.065, a value taken from earlier work, to discard rare and anomalous uses. — [arXiv 2105.15110](https://arxiv.org/abs/2105.15110)
  - Others keep only the top-k candidates by prior: top 40 in [arXiv 1712.01797](https://arxiv.org/abs/1712.01797). In [arXiv 1509.02301](https://arxiv.org/abs/1509.02301), keeping 64 candidates and then re-ranking the top 10 cost an insignificant amount of accuracy [search excerpt].
- **Priors drift over time.** The prior depends on the time of both the text and the knowledge base, which affects linking performance. — [João, "On the Temporality of Priors in Entity Linking", ECIR 2020](https://arxiv.org/abs/2101.05593)
- **Count distinct contributors, not records.** In work on place names from Flickr tags, many generic city-core terms had problematic "user ubiquity" (number of distinct users), which was used to judge tags [search excerpt]. — [Hollenstein 2008 MSc thesis, Univ. Zürich](https://www.geo.uzh.ch/dam/jcr:c5b291f0-22fa-4fcc-8d79-723648dfe5c5/msc_livia_hollenstein_2008.pdf); [Hollenstein & Purves 2010, JOSIS](https://josis.org/index.php/josis/article/view/3)
- **Knowing the container raises precision** (about 1,000 Roman-monument place names in Austria and Hungary, matched to the Alexandria Digital Gazetteer):
  - With the country known, the precision of one-to-one matches rose from 91.87% to 96.17% for exact-name matching, and from 87.2% to 93.15% for phrase containment.
  - Recall was 78.55% / 69.35% with the country constraint and 66.79% / 58.83% without.
  - Estimated gazetteer completeness was about 65%.
  - Source: [Doerr & Papagelis 2007, IEEE TKDE 19(8)](https://www.eecs.yorku.ca/~papaggel/docs/papers/all/PlacenameMatching-IEEE-TKDE-Aug-2007.pdf)

**Self-reinforcing errors**
- **Pseudo-labelling.** Naive pseudo-labelling overfits to its own wrong labels, which the authors call "confirmation bias". Their mitigations are mixup and a minimum number of truly labelled samples in each mini-batch. — [Arazo et al., arXiv 1908.02983](https://arxiv.org/abs/1908.02983)
- **Co-training.** It needs two views that are each sufficient and conditionally independent given the class. — [Wikipedia: Co-training](https://en.wikipedia.org/wiki/Co-training); [Blum & Mitchell 1998](https://publications.ri.cmu.edu/storage/publications/pub_files/pub1/blum_a_1998_1/blum_a_1998_1.pdf)
  - Later experiments found co-training sensitive to these assumptions [search excerpt]. — [Ng & Cardie 2003](https://www.cs.jhu.edu/~yarowsky/acl03cd/emnlp/pdfs/Ng.pdf)

**Local checks** ([tickets_matched.parquet](../../data/processed/tickets_matched.parquet))
- **Ticket mix.** 51.48% of tickets carry a vehicle number. 6.56% have more than one passenger. The match column (null = unmatched) gives exact 55.67%, fuzzy 18.30%, nearby 5.46% and unmatched 20.56%. 98.75% of tickets have a route code ending in UP or DOWN.
- **Support per (route-direction, start name) key on vehicle-numbered tickets.** There are 52,702 keys. The median key has 7 tickets, 6 distinct vehicles and 7 distinct vehicle-days.

  | Key passes | Share of keys | Share of vehicle tickets |
  |---|---|---|
  | ≥5 tickets | 59.3% | 96.7% |
  | ≥10 tickets | 42.3% | 92.1% |
  | ≥20 tickets | 26.9% | 83.6% |
  | ≥50 tickets | 11.9% | 65.0% |
  | ≥100 tickets | 5.2% | 46.5% |
  | ≥5 distinct vehicle-days | 58.7% | 96.6% |
  | ≥10 distinct vehicle-days | 41.5% | 91.8% |

- **Unmatched tickets** (526,429; the flag is per ticket, so either end may have failed): share whose (route-direction, start name) key has enough vehicle tickets.

  | Condition on the key | Share of unmatched tickets |
  |---|---|
  | ≥5 vehicle tickets | 93.1% |
  | ≥10 vehicle tickets | 87.7% |
  | ≥20 vehicle tickets | 78.6% |
  | ≥50 vehicle tickets | 59.5% |
  | ≥10 vehicle tickets in each half of October (1–15 and 16–31) | 75.0% |

  25,933 distinct unmatched keys; 7,881 of them have at least 20 vehicle tickets.
- **End names of unmatched tickets.**
  - 20.4% never appear as a start name in the same direction on vehicle tickets.
  - Pooling UP and DOWN cuts this to 4.6%. With pooling, 84.4% have at least 10 such tickets and 76.7% at least 20.
  - Requiring both ends to be supported (start name in the same direction, end name pooled over both directions): 78.9% of unmatched tickets at ≥10 tickets, 67.7% at ≥20.
- **GTFS shapes.** All trips have a `shape_id` (3,498 shapes) and `shapes.txt` has `shape_dist_traveled`, so route corridors and along-route positions can be computed directly. — [Local check](../../data/raw/gtfs_static/shapes.txt)

### Inferences
**1. Do not use "the stop nearest the bus at purchase time".**
- At 12–20 km/h a median stop gap of 460 m takes 1.4–2.3 min. A median lag of 0.8 min is 160–270 m of travel, and one 11 s GPS sample is 37–61 m.
- So the boarding stop is usually the stop passed most recently, sometimes the one before it. The 23% of tickets bought before the bus arrives point to the next stop.
- London shows that even with tap-on validation only 28% of taps fall inside the dwell window. A rule that requires the transaction to fall inside the dwell window (as in the Chinese study above) would therefore discard most tickets. Use a tolerance window instead.

**2. Lag model** (half a day, once stop-passage times exist from `gps_stop_passage.md`).
- **Anchors.** Use vehicle-numbered tickets whose start name is an exact match and maps to a single stop on the route.
- **GPS join.** Normalise the registration number (upper case, alphanumerics only). Require the bus to be within about 300 m of the ticket route's shape at purchase time; this rejects mistyped plates and the wrong route.
- **Lag.** Compute Δ = purchase time − passage time at the anchor stop.
- **Fit.** Fit a mixture: an empirical density (histogram in 15 s bins or a kernel density estimate over −15 to +20 min) plus a uniform background for nonsense joins, estimated with a few EM iterations.
- **Strata.** Fit it separately for one passenger vs several, AC vs non-AC, peak vs off-peak, and routes with vs without `fare_stage` flags.
- **Freeze it.** Do not re-fit it later on tickets labelled by aliases.

**3. Ticket-level posterior.**
- For each candidate stop s on the union of the route-direction's patterns:

  p(s | t, v) ∝ π_route(s) × [ (1−ε)·f_Δ(t − τ_v(s)) + ε·u ]

  - τ_v(s) is vehicle v's passage time at s on the current trip.
  - π_route(s) is the boarding share at s measured from exact anchors only (or uniform).
  - ε is the background weight learned in step 2.
- Restrict candidates to stops passed between t − 15 min and t + 10 min.

**4. Pool by key and accept by rule.** Pool the posteriors as soft counts per key (route-direction, normalised name). Suggested defaults, to be tuned on masked anchors:

| Criterion | Default | Rationale |
|---|---|---|
| Support | ≥20 GPS-joined tickets and ≥5 distinct vehicle-days | Tickets on one bus-trip share one GPS join, so count vehicle-days as the effective sample. At ≥20 tickets, 78.6% of unmatched tickets are covered by start key (Local check). |
| Confidence | 95% Wilson lower bound on the top stop's share ≥0.5, with n = distinct vehicle-days | Wilson lower bound for an observed share of 0.8: 0.49 at n=10, 0.58 at n=20, 0.67 at n=50 (derived). |
| Purity | Top stop ≥0.7, or top two adjacent stops ≥0.8 → assign the stop area | The 0.8 min lag smears probability onto neighbouring stops, and 19.7% of stop gaps are under 300 m (`transit_stop_matching.md`). |
| Margin | (top − second-best non-adjacent stop) ≥0.25 | Guards against a key that mixes two places with the same name (e.g. "Badarpur"). |
| Temporal stability | Same top stop, or an adjacent one, in both halves of October, with ≥10 tickets in each half | Priors drift over time (João). 75.0% of unmatched tickets have keys with enough data in both halves (Local check). |
| Route and order consistency | Stop lies on the route-direction's patterns, and inside the order and fare-band interval implied by anchor partners (`transit_stop_matching.md` §2) | A second check that does not use GPS. |
| Name sanity | If the GPS-chosen stop's string score is below 50 but another stop on the route scores ≥90, send the key to review | The two views disagree. |
| Volume gate | A human reviews the top ~100 aliases by ticket volume | One wrong high-volume alias mislabels thousands of tickets. |

- **End names.** Learn aliases from start names in both directions, then map them to the stop on the current direction's pattern via a stop area (same-name stops within about 300 m). The direction-specific key fails for 20.4% of unmatched tickets; pooling fails for 4.6% (Local check).
- **Keys that fail.** Classify them as:
  - "stop area": adjacent stops share the mass;
  - "ambiguous name": two separated modes;
  - "insufficient": too little support.
  Ambiguous and insufficient keys go to fare trilateration (`transit_stop_matching.md`), corridor geocoding (Q3) or manual review.

**5. Guarding against self-reinforcement.**
- **Two views.** Treat GPS timing (blind to names) and string/geocode evidence (blind to time) as the two co-training views.
  - Accept automatically only when they agree, or when GPS is strong and the name gives no evidence either way.
  - Send disagreements to review. Never use one view's output to train the other.
- **Freeze inputs.** Keep the lag density and π_route frozen on exact anchors. Never chain aliases transitively, i.e. never use alias-labelled tickets to learn new aliases on other routes.
- **Hold out by time and by vehicle.** Learn on October 1–15 and test on October 16–31. As a second test, hold out 20% of vehicles.
- **Measure the ceiling before trusting aliases.** Hide the names of exact-match anchor keys and check how often the pooled top stop equals the anchor stop.
  - A systematic off-by-one error means the lag density is mis-centred. Fix it per stratum instead of loosening the thresholds.
- **Record provenance** for each match (`method = name_exact / gps_alias / fare_trilateration / osm_geocode / llm / manual`), with version and date.
- **Re-learn** after DTC circulars change stages (`transit_stop_matching.md`).

**6. Delhi-specific checks before relying on GPS aliases.**
- **Auto-filled start stop.**
  - If the app fills the start stop from GPS when the QR code is scanned, start names on QR tickets will sit tightly at the bus's current or previous stop. The lag distribution would then be narrow, around 0 to +1 stop.
  - Compare the lag distribution of tickets with and without a vehicle number, and of e-bus QR tickets with other tickets, before trusting it as passenger behaviour.
- **Purchases before boarding.** Bus-number and QR purchases imply the passenger is on board. Tummoc and WhatsApp purchases are made by origin and destination (HVT 2024). This may explain the 23% bought before the bus arrives and the blank vehicle numbers.
  - Check whether bought-before rates differ by whether a vehicle number is present.
- **Coverage.** GPS covers DTC buses only (data README, in `transit_stop_matching.md`). Measure the share of vehicle numbers that join to GPS on the same date before estimating coverage.

**7. Expected accuracy.**
- Do not quote London's 93–96% for this setting. Per-ticket top-1 accuracy will be lower, because the lag is comparable to the time between stops.
- Pooling can still be right whenever the per-ticket errors are unbiased. Report the anchor-recovery rate from step 5 (top-1 and within one stop) as the evidence.

**8. Implementation order (about 5 days for 2–3 people).**
- Day 1: stop-passage times and the GPS join (`gps_stop_passage.md`).
- Day 2: lag mixture and ticket posteriors.
- Day 3: key pooling, acceptance rules and the masked-anchor test.
- Day 4: review page for the top keys and the end-name pooling.
- Day 5: fare and order cross-checks, corridor geocoding of the residual (Q3), and the evaluation report (Q5).

### Gaps
- **No lag model in the literature** for app or QR purchase after boarding, or for conductor sale. I found no measured lag for conductor ETMs in India.
- **Unverified BMTC report.** A July 2026 report in The Hindu says BMTC's GPS-enabled ETMs generate QR codes tied to fixed geographic stages. When payment is slow, passengers are charged for the next stage, and drivers are asked to slow down near stage boundaries. I saw this only in a search summary and could not open the article, so it is unverified. — [PressReader, The Hindu Bangalore, 8 Jul 2026](https://www.pressreader.com/india/the-hindu-bangalore-9ww1/20260708/281689736557560)
- **Inaccessible sources.** The full texts of Gordon (2012) and Wang (2010/2011) returned HTTP 429/403, so their exact iBus matching rules and windows are not confirmed here. The MBTA clock-correction details come from a search summary.
- **Chicago.** No published share of CTA bus fare transactions with inferred origins.
- **Not measured locally.** Two quantities need the GPS archive (`data/raw/bus_gps/*.7z`), which I did not extract:
  - the share of ticket vehicle numbers that join to the DTC GPS feed;
  - the lag distribution by ticket channel.

---

## Q2. Indian ETM and e-ticket data: how studies mapped ETM "stage names" or ticket stop names to stops or GTFS, and with what coverage and accuracy

### Takeaway
Indian ETM studies take the operator's stop or stage IDs as given. BMTC's ETM rows carry "from" and "till" stop IDs and stop sequence numbers; Kerala's carry stages. The problems they report are data quality: conductors entering the wrong stop, systems that record only stages, and ETM and GPS vendors using different IDs. None of them involve name matching.

I found no Indian paper or report that maps ETM stage names or app ticket names to GTFS with a reported accuracy. The closest are:
- WRI India's analytics tool combining ETM and vehicle-tracking data;
- BMTC attaching GPS coordinates to about 7,000 stop names;
- an IIIT-Delhi thesis that uses ticket data as ground truth for routes.

In Delhi, DIMTS cluster ETMs record origin, destination and fare stage. DTC buses have used pre-printed stage tickets with no stop-level origin and destination since 2022. ONDC app tickets are therefore the only stop-level source for DTC demand.

### Cited Findings
**BMTC (Bengaluru)**
- **IIIT-Bangalore study** (Jayabal & Rajagopalan 2020): ETM data for four depots, December 2018 and July 2019.
  - Each record has 59 parameters, including "ticket from stop id", "ticket till stop id", "from/till stop seq no", trip direction (UP/DN), vehicle number, passenger count and amount.
  - ETMs upload over GPRS every 5 minutes. BMTC generates about 40 million ETM transactions a month, with about 6,600 buses on about 2,500 routes.
  - Analysis was by stop ID and stop name. The paper describes no name-matching step.
  - Source: [CEUR-WS Vol-2557, paper 3](https://ceur-ws.org/Vol-2557/paper-03.pdf)
- **WRI India data analytics tool** [search excerpt]. It uses ETM fields (route, schedule, trip, origin and destination stop, passengers, fare) plus vehicle-tracking latitude, longitude and speed. It found heavy demand between two BMTC stops about 2.8 km apart, and services were added between them. — [WRI India, Data Analytics Tool (Shakti Foundation copy)](https://old.shaktifoundation.in/wp-content/uploads/2019/07/Data-Analytics-Tool.pdf)
- **Stop geocoding** [search excerpt]. BMTC began assigning GPS coordinates to the names of its 7,000 bus stops; all buses carry tracking units. — [FactorDaily](https://archive.factordaily.com/longform/big-data-real-time-gps-tonic-not-steroids-bengalurus-bus-service/)

**Kerala KSRTC, Bhubaneswar and Karnataka**
- **Trivandrum** [search excerpt]. An OD matrix can be built by querying the ETM database with a MATLAB program. The data cover six Trivandrum depots, with about 1 million transactions a month. — [Cyril & George 2018, "Electronic ticket machine data analytics for public bus transport planning" (IEEE)](https://ieeexplore.ieee.org/document/8390198/)
- **Stage-only recording.** Bhubaneswar records the exact origin and destination stop of each ticket. Trivandrum and a few other cities record only stages. The average urban stage is about 2 km. — [GIZ roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)
- **Kerala stage rules.** Stages are 2.5 km. The fare runs from the stage stop before the boarding stop to the stage stop after the alighting stop, so a trip can never be "within" one stage. — [Platform7, "Decoding a bus ticket – Part 1" (2021)](http://www.platform7.in/2021/02/decoding-bus-ticket-part-1.html)
- **Karnataka.** KSRTC ETMs are loaded with route, stage and fare tables (already in `transit_stop_matching.md`). — [SSATP Fares Toolkit](https://www.ssatp.org/sites/ssatp/files/publications/Toolkits/Fares%20Toolkit%20content/case-studies/karnataka-india.html)
  - Mysuru ITS covers 500 buses, 2,400 stops and 6 terminals with vehicle location tracking [search excerpt]. — [SSATP ITS Toolkit, Mysore case](https://www.ssatp.org/sites/ssatp/files/publications/Toolkits/ITS%20Toolkit%20content/case-studies/mysore-india.html)

**Chennai MTC**
- **GPS ETM trial.** It failed on more than 200 buses: 8 s per ticket against 4 s on the old ETMs and at most 2 s by hand. — [IJMET 2017](https://iaeme.com/MasterAdmin/Journal_uploads/IJMET/VOLUME_8_ISSUE_10/IJMET_08_10_012.pdf)
- **Kalanidhi et al. (2013)** combined ETM data with CMDA OD patterns, a passenger survey and GPS to study accessibility. I saw this only as related work in another paper; no mapping method or accuracy is given there. — [Jayabal & Rajagopalan 2020, §2](https://ceur-ws.org/Vol-2557/paper-03.pdf)

**APSRTC/TSRTC, BEST, PMPML, AICTSL**
- **APSRTC/TSRTC.** No ETM-based OD or stop-mapping study was found; a consulting deck on Scribd is of unverified provenance [search excerpt]. — [Scribd "Transforming RTC"](https://www.scribd.com/document/976888535/Transforming-RTC)
- **BEST Mumbai.** Only a BEST/EMBARQ presentation on feeder services and e-ticket sales was found [search excerpt]. — [Slideshare](https://www.slideshare.net/slideshow/connect-karo-feederbus5a/19891072)
- **PMPML Pune.** Only monthly statistical reports at route and depot level [search excerpt]. — [PMPML report (Sep/Oct 2024)](https://pmpml.org/assets/media_center/173389713550ccda9860e440932d126ed6fa52a6a0.pdf)
- **AICTSL Indore** [search excerpt]. After BRTS operations ended, conductors issue tickets inside the iBuses, and UPI/QR payment was added. No stop-level or OD analysis was found. — [Free Press Journal](https://www.freepressjournal.in/indore/indore-news-upi-system-ends-fare-disputes-in-ibuses-digital-payments-bring-transparency-reduce-disputes-and-ease-commuting-experience)

**Delhi DTC and DIMTS cluster buses**
- **DTC tickets** (Urban Catalysts for HVT, 2024):
  - DTC uses pre-printed tickets in stage blocks, about eight blocks per conductor. This captures only the total tickets per route per day.
  - The handheld ETMs used on DTC buses since 2016 were phased out in September 2022.
  - Source: [Framework … gender disaggregated travel data (2024), p. 8](https://ride.transport-links.com/wp-content/uploads/TUC_Framework-for-collection-of-gender-disaggregated-data_10102024-8.pdf)
- **DIMTS cluster ETMs** (same report):
  - In use since 2017; upgraded to Android GPRS devices in January 2021.
  - The back end keeps origin, destination, fare stage, time of issue and the number of tickets.
  - Their QR and card readers were reported not functional.
  - Source: [same report, pp. 8–10](https://ride.transport-links.com/wp-content/uploads/TUC_Framework-for-collection-of-gender-disaggregated-data_10102024-8.pdf)
- **IIIT-Delhi thesis on DTC route detection** [search excerpt]. It took the true route from user ticketing data and reports a route-detection error of about 38%. I could not open the record to confirm the method. — [IIIT-Delhi repository, handle 123456789/1124](https://repository.iiitd.edu.in/jspui/handle/123456789/1124)

**Common Indian issues** (GIZ roadmap)
- Conductors make origin and destination errors.
- The same place is entered under different names.
- Ticket IDs are duplicated.
- ETM and GPS vendors "don't use the same nomenclature and unique ids".
- The roadmap recommends recording stop-to-stop rather than stage data.
- Source: [GIZ roadmap 2021, pp. 4–5](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf)

### Inferences
- **Look for the stop master first.** The Indian norm is a structured route-stop master: IDs plus sequence numbers, as at BMTC. The ONDC app very likely has one too, since ticket names come from the full stop list (`transit_stop_matching.md`).
  - Ask for the ONDC route-stop master with IDs and sequence numbers. With it, each route needs a one-off mapping of IDs to GTFS stops instead of free-text matching of about 65k (route, name) pairs.
  - The DIMTS ETM back end (origin, destination, fare stage) is a second master to ask for, at least for cluster routes.
- **Stage semantics shape the fare signal.** If Delhi charges by stage the way Kerala does (from the stage before boarding to the stage after alighting), the fare sets distance only to within about one stage (2–2.5 km).
  - That is consistent with fares agreeing with distance for only about 83% of exact matches (`transit_stop_matching.md`).
  - Use fares as a soft interval, never a hard filter.
- **No benchmark to compare against.** No Indian benchmark exists, so the team's own masked-anchor and manual-sample results (Q5) will be the first reported accuracy for this kind of crosswalk. Present them as such.
- **Precedent for GPS-assisted origins.** Indian GPS-linked ETMs already treat "bus position at ticket time → origin stop" as acceptable (GIZ). The Chennai and BMTC experience shows the cost: a few seconds per ticket, and the bus moves on during ticketing. This supports modelling the lag explicitly rather than snapping to the current stop.

### Gaps
- **No accuracy reported in India.** No Indian study reports coverage or accuracy for mapping ETM stage or stop names, or app ticket names, to GTFS or physical stops.
- **Operators with nothing found.** I found no studies for PMPML, BEST, TSRTC/APSRTC or AICTSL. I did not search Chalo's or other ETM vendors' engineering material.
- **Unopened documents.** I could not open the WRI analytics-tool PDF (SSL error), the IIIT-Delhi thesis (connection reset), the NITK Kerala thesis or The Hindu BMTC article.
- **ONDC app internals.** Whether the ONDC/One Delhi stop list shares IDs with the DIMTS ETM master or with the Chartr GTFS is undocumented.

---

## Q3. Corridor-constrained geocoding: matching names to OSM POIs inside a route buffer, then snapping to a stop

### Takeaway
All three open geocoders can restrict results to a box or circle and can bias them towards a point. None can restrict to a route buffer, and the public Nominatim server allows at most 1 request per second. The practical design is to:
1. extract Delhi POIs and places locally from OSM;
2. keep those within about 250 m of the ticket route's GTFS shape (wider for village and campus polygons);
3. match names with rapidfuzz against `name`, `alt_name`, `short_name` and `name:en`;
4. snap to the stop on the route's pattern whose position along the route agrees with the order and fare interval.

I found no published accuracy for this exact technique. Two pieces of evidence bear on it:
- in gazetteer matching, knowing the container raised one-to-one precision from 91.9% to 96.2%;
- in Indian addressing, 80% of addresses cite a landmark 50–1,500 m from the address.

Together they support a hard corridor constraint, but warn that a landmark's position is not the stop's position.

### Cited Findings
**Geocoder controls**
- **Nominatim parameters:**
  - `viewbox=<x1>,<y1>,<x2>,<y2>` is a boost (bias). `bounded=1` turns it into a filter that excludes results outside the box. With a small box, `bounded=1` also allows amenity-only searches such as `[pub]`.
  - `countrycodes` is a hard filter.
  - `layer` (address, poi, railway, natural, manmade) and `featureType` (country, state, city, settlement) select places by theme.
  - `limit` defaults to 10, maximum 40.
  - `dedupe=0` returns every result; `namedetails=1` returns all names of a place.
  - Source: [Nominatim Search API docs](https://nominatim.org/release-docs/latest/api/Search/)
- **Nominatim public-server policy:**
  - at most 1 request per second;
  - bulk jobs on a single thread from one machine;
  - jobs that run longer than a day, or on a schedule, are limited to 4 requests per minute;
  - results must be cached;
  - a real User-Agent or Referer is required;
  - heavier use should go to your own instance or a commercial provider.
  - Source: [OSMF Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)
- **Photon API:**
  - `lat`/`lon` set a focus point; `zoom` (default 12) sets the focus radius; `location_bias_scale` (default 0.4) sets how much a result's prominence still counts.
  - `bbox` restricts results to an area.
  - `osm_tag` filters by OSM tag (deprecated in favour of include/exclude filters); `layer` (house, street, locality, district, city, …) filters by result type.
  - `limit`, `lang` and `dedupe` are also available.
  - Source: [Photon API v1 docs](https://github.com/komoot/photon/blob/master/docs/api-v1.md)
- **Running Photon locally:** it needs Java 21+ and OpenSearch 3.x unless the embedded server is used. A planet database takes about 95 GB. GraphHopper publishes weekly dumps for the planet and "selected country datasets"; India is not named. — [Photon README](https://github.com/komoot/photon)
- **Pelias:**
  - `boundary.rect.*`; `boundary.circle.lat/lon/radius` (radius in km, default 50); `boundary.country`. Several boundaries combine as an intersection.
  - `focus.point.*` sorts partly by proximity but still allows important distant results.
  - `layers` (venue, address, street, locality, …), `sources` (osm, oa, wof, gn) and `size` (default 10).
  - Source: [Pelias search docs](https://github.com/pelias/documentation/blob/master/search.md)

**Evidence that bears on accuracy**
- **Container constraint.** Knowing the containing region raised the precision of one-to-one place-name matches from 91.87% to 96.17% for exact names and from 87.2% to 93.15% for containment. — [Doerr & Papagelis 2007](https://www.eecs.yorku.ca/~papaggel/docs/papers/all/PlacenameMatching-IEEE-TKDE-Aug-2007.pdf)
- **Indian landmark addresses.** 80% of addresses in India are written relative to a landmark, typically 50–1,500 m from the actual address. — [Rustogi, Bhattacharya, Church & Raskar 2018, arXiv 1801.06540](https://arxiv.org/abs/1801.06540)
- **OSM POI completeness** depends on the POI category [search excerpt]. — [KIT publication](https://publikationen.bibliothek.kit.edu/1000158824/150739297)
- **OSM coverage in Delhi** (from `indic_name_matching.md`, Overpass query of 2026-11-16): 2,421 bus-stop nodes, of which 71 have `alt_name`, 51 `short_name` and 228 `name:hi`. — [Overpass API](https://overpass-api.de/)
- **LLM toponym resolution with candidates** [search excerpt]. Retrieving GeoNames candidates for a fine-tuned 7B model raised accuracy from 0.90 to 0.93 over seven datasets (83,365 toponyms). — [Hu et al., CEUR-WS Vol-3969 paper 6](https://ceur-ws.org/Vol-3969/paper6.pdf)

### Inferences
**Recipe** (about 1.5 days; offline; no external calls on ticket data)
1. **Gazetteer.** One Overpass or osmium extract for the Delhi NCR bounding box. Keep `name`, `name:en`, `alt_name`, `short_name`, `old_name`, `official_name`, the geometry and the tags. Store point-on-surface plus polygon, and cache it as GeoParquet. Feature types:
   - `amenity` = hospital, clinic, school, college, university, place_of_worship, marketplace, police, post_office, fire_station, bus_station, cinema;
   - `office`, `shop=mall`, `leisure=park|stadium`;
   - `railway=station`, `station=subway`;
   - `place` = village, hamlet, suburb, neighbourhood, quarter, locality;
   - named `landuse` such as industrial.
2. **Corridor.** From `shapes.txt` (all trips have shapes, with `shape_dist_traveled`), buffer the route-direction's shape by 250 m. Use the distance from the POI's polygon, not its centroid, and allow 500 m for `place=village` or large campuses.
   - Project each POI onto the shape to get its along-route position.
3. **Candidate filter.** Keep POIs whose along-route position lies inside the order and fare interval for the residual name (`transit_stop_matching.md` §§1–2). This interval does the disambiguation that raw distance cannot, since the median stop gap is 460 m.
4. **Name score.**
   - Use the folded keys and the identifier guard from `indic_name_matching.md`: numbers, single letters and acronyms must match.
   - Score with `token_set_ratio` / `ratio` ≥ 90 and a margin of ≥4 over the runner-up.
   - Add a type bonus when the ticket's type word agrees with the tag (Hospital↔amenity=hospital, Mandir/Gurudwara↔place_of_worship, Gaon/Village↔place=village, Market↔marketplace).
5. **Snap.** Choose the stop on the route-direction's pattern with the nearest along-route position, normally within ±250 m.
   - If two stops lie within 150 m of each other, assign the stop area instead.
   - Mark the result `osm_geocode`.
6. **Accept.** Accept automatically only when:
   - the top POI is unique;
   - the snapped stop agrees with the GPS posterior, if the key has GPS support (Q1), or at least with the fare/order interval.

   Otherwise send it to the review queue, with a map view of the route, the candidate POIs and the stops.
7. **Validate before use.** Hide the names of exact-match anchor keys that contain a landmark word (hospital, school, temple, market, village, etc.). Run steps 2–6 and report top-1 stop accuracy, within-one-stop accuracy and the median error in metres. Then set the buffer and score thresholds from this curve.

**Tool choice**
- Use the local extract plus rapidfuzz (simple and fast).
- Use public Nominatim only for a few hundred residual names that the local method cannot handle, and only if sending those names is allowed: `viewbox` = route bbox, `bounded=1`, `namedetails=1`, cached, about 300 names in 5 min at 1 request/s.
- Self-hosting Photon or Pelias for India is not worth it in a hackathon week unless a country dump is already at hand.

**Scope**
- This helps landmark-type names the most: hospitals, schools, temples, villages, markets, metro stations.
- Generic names such as "Health Center", "Telephone Exchange" or "Power House" will often match several POIs in the corridor. They need the GPS alias (Q1) or the fare interval.

### Gaps
- **No published accuracy** for corridor-constrained POI matching of bus-stop or ticket names, in India or elsewhere.
- **OSM POI completeness** in Delhi, by category, has not been quantified.
- **Country dumps.** Whether GraphHopper publishes a Photon dump for India was not confirmed.

---

## Q4. Probabilistic record linkage and learned matchers (Fellegi–Sunter/Splink, dedupe, Zingg; transliteration features and multilingual embeddings; LLM matching with verification) — accuracy for place or stop names

### Takeaway
The problem is already blocked by route: each ticket name has about 30–80 candidate stops. Within that block, a Fellegi–Sunter model can combine name, identifier tokens, position/fare and GPS evidence into one calibrated weight. Splink fits it by EM and supports term-frequency adjustment on name tokens. But no study reports its accuracy on place or stop names.

The only accuracy numbers for place names come from:
- LLM pipelines with candidate lists: POI entity resolution F1 0.89–0.94 with GER-LLM on DeepSeek-V3; toponym resolution accuracy 0.93 with GeoNames candidates;
- supervised station matching: F1 above 99% (Bast et al., in `indic_name_matching.md`).

Transliteration models are best used as features. MuRIL represents romanised Hindi far better than mBERT (NER F1 25.5 → 69.8) but has not been tested on name matching, and I found no evidence for LaBSE on names.

Use LLMs offline on the residual names only. Give them a shuffled candidate list plus "NONE", and accept an answer only when independent evidence (GPS posterior, fare/order interval) agrees.

### Cited Findings
**Splink (Fellegi–Sunter) term-frequency adjustment**
- TF adjustment makes a match on a rare value count for more than a match on a common one. The u-probability of an exact match on value x is set to x's term frequency.
- Settings:
  - `tf_adjustment_column`;
  - `tf_adjustment_weight`: 0 turns adjustment off, 0.5 halves its effect;
  - `tf_minimum_u_value`, e.g. 0.001, which caps the boost from very rare values such as typos.
- On fuzzy levels Splink uses the greater of the two term frequencies.
- Adjustment is off unless turned on per comparison level.
- The docs recommend adjusting on the full name rather than each part, because the parts are not independent.
- Source: [Splink docs, Term frequency](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html)
- **uk_address_matcher** (MoJ, built on Splink) [search excerpt]: an exact-match stage, then a two-pass Splink stage. The second pass compares distinguishing tokens within each candidate group. Accuracy is analysed from a column of true labels, but I did not see precision or recall figures. — [uk_address_matcher docs](https://moj-analytical-services.github.io/uk_address_matcher/get_started)

**dedupe and Zingg** (active learning; no place-name accuracy found)
- **dedupe.** `sample()` returns the record pairs dedupe is "most curious" to have labelled, i.e. uncertainty sampling for a labelling UI [search excerpt]. — [dedupe API docs](https://dedupe-staging.readthedocs.io/en/stable/API-documentation.html)
  - A user report shows how much a labelling session depends on the version: one version stopped at 100 negative and 1 positive label, an earlier one at 22 negative and 18 positive [search excerpt]. — [dedupe issue #1077](https://www.github.com/dedupeio/dedupe/issues/1077)
- **Zingg.** The workflow is findTrainingData → label → train → match/link. Maintainers advise repeating findTrainingData and label until the labelled pairs represent the matching you need; no number is given [search excerpt]. — [Zingg tutorial (Medium)](https://medium.com/data-science/step-by-step-identity-resolution-with-python-and-zingg-e0895b369c50); [Zingg discussion #476](https://www.github.com/zinggAI/zingg/discussions/476)

**Learned matchers for station and toponym names** (already in `indic_name_matching.md`)
- Random forest on character trigrams plus distance: F1 > 99% for station matching. — [Bast, Brosi & Näther, arXiv 2012.15267](https://arxiv.org/abs/2012.15267)
- Supervised combinations of similarity metrics beat any single metric. — [Santos et al., IJDE](https://eprints.lancs.ac.uk/id/eprint/89481)

**Transliteration and embeddings**
- **MuRIL** vs mBERT on transliterated (romanised) Hindi test sets:

  | Task | mBERT | MuRIL |
  |---|---|---|
  | PANX NER F1 | 25.5 | 69.8 |
  | UDPOS F1 | 25.0 | 63.1 |
  | XNLI accuracy | 39.6 | 68.2 |
  | Tatoeba accuracy | 3.0 | 14.9 |

  - Averaged over languages, transliterated sets improve far more than native ones; PANX, for example, goes from 14.2 to 57.7.
  - MuRIL's transliterated training pairs came from Dakshina and from the indic-trans transliteration of Wikipedia.
  - Source: [MuRIL, arXiv 2103.10730](https://arxiv.org/abs/2103.10730)
- **LaBSE** [search excerpt]. L3Cube-IndicSBERT reports beating LaBSE on Indic sentence-similarity tasks; this is not name matching. I found no evaluation of LaBSE on transliterated place or person names. — [arXiv 2304.11434](https://arxiv.org/abs/2304.11434)
- **indic-transliteration** (PyPI) converts between Indic scripts and standard schemes (Harvard-Kyoto, IAST, SLP1, WX, …). The page says nothing about informal romanisation. — [PyPI indic-transliteration](https://pypi.org/project/indic-transliteration/)
- **IndicXlit** is about 59–61% top-1 for Hindi romanised→native (`indic_name_matching.md`). — [IndicXlit](https://github.com/AI4Bharat/IndicXlit)

**LLM matching against a candidate list**
- **Match, Compare or Select** (Wang et al., COLING 2025) [search excerpt]:
  - Three strategies: matching (judge each pair independently), comparing (pick the better of two) and selecting (choose the match from a list, or none).
  - Selecting is often the most cost-effective, but its accuracy changes markedly with the position of the true match in the list.
  - ComEM first filters candidates with a cheaper step and then selects. It reports an F1 gain of about 16–18% over pairwise matching (16.02% or 17.58%, depending on the paper version), on 8 datasets with 9 LLMs.
  - Source: [arXiv 2405.16884](https://arxiv.org/abs/2405.16884)
- **GER-LLM** (EMNLP 2025), geospatial entity resolution of POIs:
  - Data: Dianping, Meituan, Gaode, OSM and Foursquare records for Nanjing, Hangzhou and Pittsburgh.
  - Method: spatial blocking (quadtree plus area-of-interest detection), group prompting, and graph-based conflict resolution to keep decisions globally consistent.
  - Results: average F1 0.9164. With DeepSeek-V3: 0.8892 (Nanjing), 0.9412 (Hangzhou), 0.9187 (Pittsburgh), the best on all three datasets.
  - LLM interactions per dataset: 229–284, against 6,008–6,623 for pairwise matching.
  - Open-weight models in the extracted Table 6: Qwen3-14B 0.7583 / 0.9079 / 0.8654; Qwen3-32B 0.8231 / 0.8889 / 0.8947. I read these from text extracted from the PDF; the columns are aligned but not visually checked.
  - Source: [GER-LLM, ACL Anthology 2025.emnlp-main.1186](https://aclanthology.org/2025.emnlp-main.1186.pdf)
- **LLM toponym disambiguation** [search excerpt]. Accuracy is highest at country level and falls at finer administrative levels (ADM1/ADM2). A larger model does not reliably do better. — [Welscher et al., AGILE GIScience Series 7 (2026)](https://agile-giss.copernicus.org/articles/7/46/2026/agile-giss-7-46-2026.pdf)
- **Zero-shot LLMs on unseen entities** (already in `indic_name_matching.md`). GPT-4 beats fine-tuned matchers by 34–57% F1 on out-of-distribution entities. — [Peeters & Bizer, arXiv 2310.11244](https://arxiv.org/abs/2310.11244)

### Inferences
**1. Route-blocked Splink design** (1–1.5 days)
- **Blocking:** same route-direction. Candidates are the stops on the union of its patterns, plus optionally stops of other routes within 300 m of the shape.
- **Comparisons:**
  - (a) Name, from strongest to weakest: canonical exact; folded or skeleton exact; Jaro–Winkler ≥0.92; token-set ≥90 with the identifier guard; else. Apply TF adjustment on the canonical name with `tf_minimum_u_value` about 0.001, so that common words ("metro station", "crossing", "village") count little and rare locality words count a lot.
  - (b) Identifier tokens (numbers, block letters, Kalan/Khurd): agree / conflict / absent.
  - (c) Along-route position: inside the order and fare interval / within one stop of it / outside.
  - (d) GPS posterior share for the key: ≥0.6 / 0.3–0.6 / <0.3 / no GPS.
  - (e) Q3 geocode snap: agrees / disagrees / none.
- **Training:** estimate u from random within-block pairs and m by EM. Fellegi–Sunter assumes the comparisons are independent given match status, but (a) and (e) are correlated. So calibrate the final threshold on labelled keys (Q5) rather than trusting the posterior probabilities.
- **Decision:** one stop, or stop area, per (route-direction, name). Take the argmax with a margin, and send ties to review.
- **Simpler alternative:** logistic regression or gradient boosting on the same features, trained on silver labels (Q5). This is likely to perform as well within a week, and is easier to debug.
- **dedupe or Zingg:** use only if a labelling loop is wanted out of the box. dedupe's uncertainty sampling suits a few hundred labels. I did not verify Zingg's runtime stack; check how heavy it is before choosing it.

**2. Transliteration features**
- Folded keys and phonetic skeletons (`indic_name_matching.md`) are cheaper and already effective.
- If IndicXlit is installed, add one feature: the overlap (Jaccard) of the top-5 Devanagari beams of the two names. Do not compare top-1 strings.
- MuRIL or LaBSE embedding cosine is an unproven extra feature. Try it only if time allows, and keep it only if it improves the masked-anchor score.

**3. LLM protocol** (offline, residual names only, about 1–2k keys)
- **Prompt.** For each residual key, give:
  - the ticket name;
  - the route's ordered stop list with stop_ids (up to about 80);
  - the along-route interval implied by fares and order;
  - the top three GPS candidates, if any;
  - OSM POIs in the corridor;
  - the option "NONE".

  Ask for structured output: stop_id, confidence and a short reason.
- **Two runs.** Run twice with the candidate order shuffled, because selection accuracy depends on list position. Accept only when both runs agree and the answer agrees with an independent signal (GPS posterior, fare interval or geocode). Everything else goes to review.
- **Model choice.** If data terms forbid sending ticket names to external APIs, use an open-weight model run locally. In GER-LLM's Table 6, Qwen3-32B is 2–7 F1 points below DeepSeek-V3 and Qwen3-14B 3–13 points below, depending on the city.
- **Ceiling.** Expect the LLM to be best at acronyms and alternate names (S.J. → Safdarjung, NSIC → Modi Mill). Do not use it for generic names, where only GPS or fares can decide.

### Gaps
- **Tools.** No published accuracy for Splink, dedupe or Zingg on place, toponym or stop names.
- **Embeddings.** No evaluation of LaBSE or MuRIL on matching romanised Indian place names.
- **LLMs.** No LLM benchmark on Indian bus-stop or locality names.
- **Unverified LLM details.** The Match/Compare/Select and toponym-resolution numbers come from abstracts or search excerpts.

---

## Q5. Evaluation without gold labels: weak supervision, how many manual labels, active learning

### Takeaway
Use three sources of labels, in decreasing order of trust:
1. **Exact-name anchors with their names hidden.** These are silver labels: free, but biased towards easy names and well-kept routes.
2. **Agreement between independent weak signals** (GPS posterior, fare/order interval, OSM geocode, guarded string match), treated as labelling functions.
3. **A small stratified manual sample.** About 200 labelled keys give ±3 points at 95% confidence if precision is about 95% (384 keys if it is about 90%).

Context from other work:
- Active-learning benchmarks needed about 200–2,400 labels to train a matcher close to its best F1.
- Importance sampling (OASIS) cut the labels needed for evaluation by up to 83% under heavy class imbalance.
- Weak supervision (Snorkel) came within 3.6% of models trained on large hand-labelled sets.
- Doerr & Papagelis show that precision can even be estimated without labels, from statistics on how many places share each name.

### Cited Findings
**Weak supervision**
- **Snorkel.**
  - On four datasets plus work with the US Department of Veterans Affairs and the FDA, it improved on earlier heuristic approaches by 132% on average and came within 3.60% of models trained on large hand-curated sets.
  - In a user study, experts built models 2.8× faster and 45.5% better than with seven hours of hand labelling.
  - Source: [Ratner et al., Snorkel (PVLDB 11(3), 2017), arXiv 1711.10160](https://arxiv.org/abs/1711.10160)
- **Panda** [search excerpt]. Snorkel-style labelling functions applied to entity matching, with an IDE for writing and debugging them and a labelling model specific to entity matching. — [Wu et al., PVLDB 14(12) 2021, arXiv 2106.10821](https://arxiv.org/abs/2106.10821)
- **ZeroER** [search excerpt]. Entity resolution with no labels: a two-component Gaussian mixture fitted by EM, with adaptive regularisation and transitivity. It is reported comparable to supervised methods on five benchmarks; I did not verify per-dataset figures. — [Wu et al., SIGMOD 2020, arXiv 1908.06049](https://arxiv.org/abs/1908.06049)
- **Estimating precision from multiplicity.** Doerr & Papagelis estimate gazetteer completeness and the precision and recall of one-to-one place-name matches from the matching run itself, with no other data. Their example is about 1,000 place names with an estimated completeness of about 65%. They validated the model by removing places from the gazetteer. — [Doerr & Papagelis 2007](https://www.eecs.yorku.ca/~papaggel/docs/papers/all/PlacenameMatching-IEEE-TKDE-Aug-2007.pdf)

**How many labels**
- **Active-learning benchmark** (Meduri, Popa, Sen & Sarwat, SIGMOD 2020): runs start from 30 seed labels and add 10 per iteration, up to 2,360 labels.
  - Random forest with query-by-committee reached F1 0.99 on DBLP-ACM after 260 labels, 0.99 on DBLP-Scholar after 1,770, 0.98 on Cora after 1,700, and 0.963 / 0.971 on Abt-Buy / Amazon-Google only at 2,360.
  - Linear-SVM margin sampling with blocking reached its best F1 with fewer labels (170–930), but lower F1 on hard datasets (0.61–0.70 on Abt-Buy and Amazon-Google).
  - Tree ensembles held up under up to about 20% label noise.
  - Source: [arXiv 2003.13114](https://arxiv.org/abs/2003.13114)
- **OASIS** [search excerpt]. Adaptive importance sampling for estimating F-measure, precision and recall of entity resolution. The estimates converge to the true values, and it needed up to 83% fewer labels on six datasets with class imbalance up to about 1:3000. Released as a Python package. — [Marchant & Rubinstein, PVLDB 10(11) 2017, arXiv 1703.00617](https://arxiv.org/abs/1703.00617)

**Validating against natural ground truth**
- Santiago validated against volunteers and a survey with registered card numbers, getting about 90% correct [search excerpt]. — [Munizaga et al. 2014](https://www.worldtransitresearch.info/research/5250)
- Brisbane uses its tap-on and tap-off records as ground truth [search excerpt]. — [Alsger et al. 2016](https://www.worldtransitresearch.info/research/5965)
- In both cases the system already contained labels for part of the data, as Delhi's exact-name anchors do.

### Inferences
**Protocol** (about 1.5 days including labelling)
1. **Silver set from anchors.**
   - Take exact-match keys on vehicle-numbered tickets and hide their names.
   - Score every method on them: GPS posterior (Q1), fare/order interval, geocode (Q3), Splink or classifier (Q4).
   - Report top-1 and within-one-stop accuracy, stratified by route group (with vs without `fare_stage`), peak vs off-peak, and one vs several passengers.
   - Re-weight to the route mix of the unmatched tickets, because anchors over-represent routes with `fare_stage` flags (88.8% exact on those vs 32.9% on the rest, `transit_stop_matching.md`).
2. **Labelling functions** (each returns a stop_id or abstains):
   - `LF_exact_canonical`;
   - `LF_gps_alias` (Q1 thresholds);
   - `LF_fare_order` (the single stop in the interval that also has the best name score);
   - `LF_osm_snap`;
   - `LF_guarded_fuzzy`.

   For each, report coverage, overlap, conflict rate and accuracy on the silver set. Combine them by majority vote, or by Snorkel's LabelModel if it is available. Keys with conflicts are the active-learning pool.
3. **Manual labels.**
   - Label 300 keys, stratified by method × ticket-volume decile × route group. Double-label 20% to measure agreement between labellers.
   - Show each labeller the route polyline, the candidate stops, the GPS histogram, the fare interval, OSM POIs and the DTC circular spelling if one exists.
   - At about 30–60 s per key, this is about 2.5–5 hours of work (my estimate).
4. **Active learning.** After the first 100 stratified labels, add labels in batches of 10, chosen from keys with small margins or conflicting labelling functions (dedupe-style uncertainty sampling). Stop when the chosen threshold and its precision estimate stop moving.
5. **Report:**
   - precision, by key and by ticket, with 95% Wilson intervals;
   - coverage, i.e. the share of unmatched tickets resolved;
   - a coverage–precision curve over the acceptance threshold.

   Operate where the lower 95% bound on precision is at least 0.90, or 0.95 for fully automatic acceptance. Report drift between the two halves of October.
6. **Optional:** use OASIS-style importance sampling when estimating recall over the full candidate space (heavily imbalanced) rather than precision of accepted aliases.

**Derived sample sizes** (normal approximation, z = 1.96)

| Expected precision | ±5 points | ±3 points |
|---|---|---|
| 0.95 | 73 | 203 |
| 0.90 | 138 | 384 |

Wilson lower bounds for an observed share p:

| n | p = 0.7 | p = 0.8 | p = 0.9 |
|---|---|---|---|
| 10 | 0.40 | 0.49 | 0.60 |
| 20 | 0.48 | 0.58 | 0.70 |
| 50 | 0.56 | 0.67 | 0.79 |
| 100 | 0.60 | 0.71 | 0.83 |

**How many labels for a learned matcher.** About 200–400 labelled keys (plus thousands of silver anchors) should be enough for a tree-based classifier on a few strong features. This rests on Meduri et al.: 260 labels reached F1 0.99 on the easier DBLP-ACM. On hard, product-like data, F1 kept improving up to 2,360 labels, so treat the labelled set as an evaluation set first and a training set second.

### Gaps
- **No published label budgets** or agreement statistics for stop-name crosswalks or ticket-name matching.
- **Not verified:**
  - ZeroER's per-dataset F1;
  - OASIS's per-dataset label savings;
  - Panda's F1 against supervised baselines.
- **Untested correlation.** Whether the silver-set accuracy on exact anchors predicts accuracy on genuinely non-matching names is not known. It must be checked with the manual sample: compare silver and manual accuracy for the same method.
