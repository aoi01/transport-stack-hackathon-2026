# Bus crowding from partial e-ticket data: expansion, probabilistic loads and validation (Delhi, notes as of Nov 2026)

How sources are tagged:

- **[S]**: peer-reviewed or official source; I checked the numbers in the full text, the slides or the abstract.
- **[M]**: peer-reviewed or official source, but I saw the numbers only in an abstract, a secondary write-up or a search snippet.
- **[W]**: press, vendor or blog source, or a snippet whose origin is unclear.
- **(snippet)**: I saw only a search-result excerpt, not the document itself.

The worked numbers under the "Inferences" headings are my own calculations, not published results.

## 1. Expansion and calibration when the capture rate varies (raking/IPF, hierarchical Bayes, capacity bounds, external counts, practice in other cities)

### Takeaway

London, Santiago and the US studies of IPF (iterative proportional fitting) never use one global sampling rate. They take a card sample that already covers most riders and scale it to independent control totals at route, trip or station level. Those totals come from ETM or farebox boardings, gate counts, APC (automatic passenger counters) or fare-evasion surveys, and the results are then checked against surveys. I found no study that expands a self-selected app/QR sample of about 3–4%.

For Delhi, the main error is therefore not sampling noise. It is the capture rate differing from cell to cell, plus the free riders and pass holders who are missing entirely.

The fixes that fit in about a week:

- **Split the expansion factor** into two parts: capture of paid tickets, and a free/pass share.
- **Rake to the official totals by operator** (DTC vs cluster).
- **Give each route its own capture rate**, partly pooled with other routes and bounded by bus capacity.
- **Ask the operators for totals** from their ETMs and from Saheli card taps, to use as control totals.

### Cited Findings

**London (MIT ODX)**

- ODX (MIT's method for inferring origin, destination and interchange from fare and GPS data) "does not make inferences for all fare transactions" and "needs to be scaled up to full demand". The control totals it uses are ETM boardings on buses, an APC sample, and rail gatelines. [S] — [MIT OCW 1.258J Lecture 10, 2017](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- How much London could infer [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf):
  - Boarding location found within ±5 min for 96% of bus boardings, and within ±1 min for 93%.
  - 1.4% of boardings not matched to an iBus trip.
  - Destination inferred for 74.6% of boardings.
  - Interchange status inferred for 91% of journey stages.
- Scaling at trip level [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf):
  - Where APC exists, IPF assigns the remaining destinations "in probability".
  - The control totals are APC boardings and alightings minus the ODX boardings and alightings.
- Scaling at journey level [S] — [same lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf):
  - Expansion factors scale the Oyster journeys that were inferred, so that they also stand for non-Oyster riders and for journeys that were only partly recorded.
  - Control totals exist for stations and routes but not for itineraries, so "trillions of solutions can satisfy control totals".
  - The adopted approach is to "scale all full-journey itineraries to satisfy control totals".
- Gordon, Koutsopoulos & Wilson (2018, TR-C) scale journey flows to the passenger counts at each station gate and bus farebox. This gives estimates both for riders without a card and for card journeys that could not be inferred. The results were validated against surveys and traditional OD matrices. [M] — [World Transit Research summary](https://worldtransitresearch.info/research/6836)
- Compared with TfL's manual Bus OD Survey (BODS), there were only "small stop-by-stop differences". BODS itself undercounted ridership in the peaks and at midday when its return rates were low (50–80%). [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- Wang, Attanucci & Wilson (2011, *J. Public Transportation* 14) describe their work as the first known check of smart-card bus OD against a manual survey (BODS). The thesis compares BODS, ETM and Oyster counts on the surveyed trips. [M] — [DSpace@MIT](https://dspace.mit.edu/handle/1721.1/110021); [thesis](https://dspace.mit.edu/handle/1721.1/60814)

**Santiago (card-only payment, with fare evasion)**

- Munizaga, Gschwender & Gallegos (2020, TR-A 141:307–322) estimate correction factors for fare evasion in smart-card OD matrices. They work in sequence and use external evasion measurements plus the Metro OD survey. [M] — [IDEAS/RePEc](https://ideas.repec.org/a/eee/transa/v141y2020icp307-322.html); [U. Chile repository](https://repositorio.uchile.cl/handle/2250/179318)
  - Partial evasion: 5% on bus stages that come before a Metro stage.
  - Total evasion: 37% on bus-only trips.
  - This shows how large a capture bias that differs by channel can be.
- Earlier Santiago practice [W/M] — [Munizaga webinar, 2014](https://de.slideshare.net/BRTCoE/webinar-using-smart-card-and-gps-data-for-policy-and-planning-the-case-of-transantiago):
  - Bus boardings were expanded with expansion factors.
  - Alightings were estimated, then aggregated to bus or route level.
  - Trip-stage estimates were about 90% correct, but "fare evasion not included".
  - Validation against large OD surveys was still pending.
- Devillaine et al. name fare evasion and group travel as sources of bias in passive-data OD. They propose two kinds of validation: endogenous (internal consistency) and exogenous (external data). [M] — [Emerald chapter](https://emerald.com/insight/content/doi/10.1108/9781781902882-038)

**Bogotá**

- Bus passengers validate only when boarding, so destinations must be inferred. [M] — [arXiv 2112.04009](https://arxiv.org/html/2112.04009v2)
- Press reports a Universidad Nacional study putting TransMilenio fare evasion at 29.66% in the first half of 2022 (about 3 in 10 users). [W, snippet; I could not confirm which article holds the figure] — [Cambio](https://cambiocolombia.com/pais/articulo/2023/8/transmilenio-lanza-estrategia-para-descubrir-los-colados); [La FM](https://www.lafm.com.co/bogota/transmilenio-la-nueva-estrategia-para-evitar-colados)
- Since August 2023, inspectors check cards on board with an NFC app. [W, snippet; same two articles] — [Cambio](https://cambiocolombia.com/pais/articulo/2023/8/transmilenio-lanza-estrategia-para-descubrir-los-colados); [La FM](https://www.lafm.com.co/bogota/transmilenio-la-nueva-estrategia-para-evitar-colados)

**How Indian operators record tickets (ETM)**

- Indian operators record every conductor-issued ticket in an ETM, so they hold the full set of tickets. Chennai MTC issued about 16 lakh tickets a day through ETMs across 32 depots. [W] — [DT Next](https://www.dtnext.in/news/chennai/16-lakh-tickets-being-issued-through-electronic-ticketing-machines-in-mtc-buses-daily-788073)
- Studies build OD matrices and load profiles directly from ETM records:
  - Kerala KSRTC, by querying the ETM database [M] — [NITK repository](https://idr.nitk.ac.in/handle/123456789/8234)
  - Bengaluru, at route and corridor level [M] — [CEUR-WS Vol-2557 paper 3](https://ceur-ws.org/Vol-2557/paper-03.pdf)
- Karnataka's state bus corporations issue zero-value "Shakti" tickets to women, so free riders appear in the ticket data (more than 100 crore free rides). [W] — [The South First](https://thesouthfirst.com/news/karnataka-congress-upbeat-over-shakti-scheme-celebrated-100-cr-plus-free-rides-for-women-said-it-will-pump-in-more-funds)
- Delhi's pink tickets were issued per ride. Operators were reimbursed in proportion to pink tickets issued (Rs 10 per pink ticket), and about 1,000 million were issued between Oct 2019 and Jan 2023. So route-level counts of free riders exist inside the operators' systems. [M] — [Dasgupta & Datta 2023, Ashoka Econ DP-105](https://dp.ashoka.edu.in/dp/RePEc/ash/wpaper/paper105_0.pdf)
- From November 2025 the Pink Saheli smart card replaced paper pink tickets. It is tapped on ETMs and each journey is recorded digitally; more than 8 lakh women had switched to it. [W] — [Tribune](https://www.tribuneindia.com/news/delhi/over-8l-women-shift-to-delhis-digital-free-bus-travel-scheme/); [The Logical Indian](https://thelogicalindian.com/delhi-launches-pink-saheli-smart-card-for-women-and-transgenders-free-bus-travel-digital-access-and-inclusive-mobility-revolution/)

**Public control totals for Delhi**

| Year | Total buses, daily passengers | DTC | Cluster | Source |
|---|---|---|---|---|
| FY2019–20 | >51 lakh | 33.4 lakh | 17.71 lakh | [NewsBytes](https://www.newsbytesapp.com/news/auto/economic-survey-2025-26-finds-delhi-bus-ridership-down-nearly-20/story) [M] |
| FY2023–24 | about 41.4 lakh (sum) | 25.02 lakh | 16.39 lakh | [Newslaundry](https://www.newslaundry.com/2025/10/15/public-transport-falters-petrol-sales-rise-can-delhis-ev-policy-fill-the-gap) [M] |
| FY2024–25 | ~40.8 lakh | 25.6 lakh | 15.3 lakh | [NewsBytes](https://www.newsbytesapp.com/news/auto/economic-survey-2025-26-finds-delhi-bus-ridership-down-nearly-20/story) [M] |

The FY2019–20 and FY2024–25 figures are from the Economic Survey of Delhi 2025–26.

- Digital QR ticketing for DTC buses went live on ONDC (One Delhi app). Press cites roughly 1.2–1.5 lakh digital tickets a day, but the figures differ by source and date. [W, snippet] — [CXOToday](https://cxotoday.com/media-coverage/digital-qr-ticketing-for-dtc-buses-now-live-on-the-ondc-network/); [Inc42](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc)
- App tickets carried a 10% discount. An incentive like that can make capture differ between user groups. [W] — [Hindustan Times via PressReader, 2021](https://www.pressreader.com/india/hindustan-times-delhi/20210718/281651078120594)
- IIT Delhi is running a 12-month route-rationalisation study (March 2026 to February 2027). It covers 121 routes in the East zone, 181 in the West and 194 in the North. [W] — [The Statesman](https://www.thestatesman.com/cities/iit-delhi-to-soon-complete-dtc-route-rationalisation-study-for-devi-buses-1503584876.html); [Tribune](https://www.tribuneindia.com/news/delhi/iit-delhi-to-study-capitals-bus-route-rationalisation-plan/)

**Estimation methods with tested accuracy**

- IPF run on APC boardings and alightings produced route OD matrices of roughly the same quality as onboard-survey matrices, which cost much more. This was checked against field ground truth (Ji, Mishalani & McCord). [M] — [WTR summary](https://www.worldtransitresearch.info/research/3545)
- Starting IPF from an iteratively improved base matrix beat starting from a null base whenever APC data covered even a small number of trips. [M] — [ASCE J. Transp. Eng. 2014](https://ascelibrary.com/doi/10.1061/%28ASCE%29TE.1943-5436.0000647)
- A Bayesian model of time-varying OD built from boarding and alighting counts beat IPF on 3 bus routes and gives uncertainty estimates. It treats alightings as multinomial, uses a Gaussian-process prior over time, and is fitted by MCMC. [M] — [arXiv 2403.04742](https://arxiv.org/abs/2403.04742)
- Full buses censor demand: ridership records "only include information for people that got on the bus". In a Pittsburgh study, the authors flagged likely full-bus cases and left them out before fitting a Poisson demand model. In simulation this removed the bias, while keeping them underestimated the demand that was turned away. [M] — [arXiv 2208.06372](https://arxiv.org/abs/2208.06372)

### Inferences

**Where the error comes from.**

- A week-to-week r of 0.78 shows the pattern across cells repeats. But both weeks use the same expansion factor, so a wrong capture rate in a particular cell cannot show up in that number.
- The cells with 700 passengers per bus are the visible part of that bias.
- So gains will come from fixing the level (bias), not from smoothing. This explains why Empirical-Bayes smoothing and the hour-shift showed no gain.

**Split the expansion factor.**

E_c = (1/π_c) × 1/(1 − f_c − p_c), where:

- π_c = e-tickets as a share of *paid* boardings in cell c
- f_c = share of free riders (pink tickets / Saheli card)
- p_c = share of pass holders

The current factor of 1/0.035 assumes f = p = 0 and a constant π.

**Consistency check.**

- The capture rate implied by the official total is π_paid = (e-tickets per day) / ((1 − f − p) × 4.08M).
- With f = 0.45 and p = 0.05:

| E-tickets per day | Implied π_paid |
|---|---|
| 60k | 2.9% |
| 85k | 4.2% |
| 120k | 5.9% |

With f between 0.40 and 0.50, the 85k/day case gives 3.8% to 4.6%.

- So the expanded total reaching "61% of the official total" is about what you would expect if the expansion covers only paid riders. It is not evidence that the expansion is too small.
- Compare expanded paid riders with the official total × the paid share, not with the full total.
- First check whether the brief's "3–4% of all tickets" includes pink tickets or Saheli taps.

**Rake to the totals you have (about 1 day).**

- Use operator × day type as the margins: DTC 25.6 lakh and cluster 15.3 lakh per day (FY24–25), times the paid share.
- The DTC/cluster split matters because the ONDC QR launch coverage is about DTC buses, so capture probably differs by operator.
- Add AC/non-AC and DEVI/other margins if totals can be obtained.
- Use bounded IPF, as in survey weighting: trim extreme weights, then re-rake.

**Pool route-level capture rates and bound them by capacity (2–3 days).**

- Model: logit π_r = α + β·X_r + u_r, with u_r ~ N(0, σ²) so that routes borrow strength from each other.
- Route covariates X_r:
  - share of AC trips
  - operator
  - DEVI flag
  - share of tickets carrying a vehicle number (a proxy for a QR code being available on board)
  - fare-slab mix
- Likelihood: e-ticket on-board count per trip-segment ~ NB(π_r·μ, k) (negative binomial).
- What fixes each part:
  - The overall level comes from the operator totals, used as a raking constraint.
  - The spread between routes comes from a soft capacity bound: P(load on the busiest segment > crush capacity) should stay at or below about 5% on every route.
- A one-day version:
  1. Compute a lower bound for each route: π_r ≥ P95(e-ticket peak on-board count per trip) / (C_crush × (1 − f − p)).
  2. Raise π for routes that break the bound.
  3. Re-rake the other routes to the operator totals.
- This replaces the cap of 100 per bus, which hides the problem, with a fix for its cause. Report the share of trips above capacity before and after as a metric.

**The single most valuable data request.**

- Ask DTC/DIMTS for one month of ETM aggregates by route × hour × ticket type (paid / Saheli / pass).
- Indian operators (KSRTC, BMTC) already build OD and loads from ETMs. Delhi's per-ticket pink reimbursement and digital Saheli taps imply the data exist.
- Even route-day totals would turn the task into the standard London-style IPF/trip-level scaling.

**Technique matrix.** The effects are taken from the cited cases or my illustrations; none has been measured on Delhi data.

| Technique | Data needed | Evidence of effect | Fit for 1 week |
|---|---|---|---|
| Split out free riders and pass holders | Free-share priors (section 4) | Free riders are about 40–50% of boardings, so loads rise ×1.7–2.0 on average | High |
| Rake to operator totals | Economic Survey DTC/cluster figures | London and Santiago scale to control totals; Santiago's 37% bus-only evasion shows how big channel bias can be | High |
| Route capture rates with a capacity bound and pooling | Bus capacity, vehicle-linked trips | Pittsburgh: ignoring capacity censoring biases demand estimates | Medium-high |
| IPF or Bayesian OD for alightings | Declared OD plus any counts | IPF is about as good as an onboard survey; the Bayesian model beats IPF | Medium |
| ETM/Saheli control totals | Request to the operators | Full-population ETM OD and loads already used in KSRTC/BMTC | Depends on access |

### Gaps

- I found no study that expands a small (<5%), self-selected app/QR ticket sample into route or trip loads, or that reports the accuracy of doing so against counts.
- I found no hierarchical Bayesian model of capture rates with capacity constraints in the transit literature. The design above is my proposal, not a tested method.
- I found no public route-level ridership for Delhi. The IIT Delhi study may hold it, but I found no source naming its data.
- I could not find how Bogotá turns validations into expansion factors; only press figures on evasion.
- I found no breakdown of Delhi's e-ticket share by AC/non-AC, operator or channel.
- The scope of "3–4% of all tickets" in the brief is unclear (whether it includes pink tickets).

## 2. Trip-level load distributions and probabilistic crowding (negative binomial / Poisson–Gamma, P(seat), P(crowded), showing uncertainty)

### Takeaway

- **Model a distribution, not a mean.** Treat the load on each trip-segment as a negative binomial distribution:
  - Its mean comes from the expanded cell estimate.
  - Its overdispersion parameter k can be estimated from the vehicle-linked e-tickets. Randomly sampling passengers from a negative binomial load leaves k unchanged, so k can be measured from e-ticket counts without knowing the capture rate π.
  - Then report P(seats) / P(standing) / P(crowded) for each trip.
- **What the evidence supports.** A Stockholm study derives P(seat) from load forecasts. HCI experiments show quantile dotplots or CDFs lead to better bus decisions than point estimates. Live crowding information shifts a minority of riders (a few percentage points).
- **Why it matters.** My worked example: with realistic overdispersion, a cell with mean 45 that is labelled "standing" still has a 16–24% chance of being crowded (>60), compared with 1% under a Poisson assumption.

### Cited Findings

- Jenelius (2020, TR-C 117:102647) [M] — [WTR](https://www.worldtransitresearch.info/research/7934)
  - Predicts the chance of getting a seat when boarding, the expected time spent standing, and the extra perceived travel time.
  - Loads and alightings come from lasso and PLS regression.
  - A probabilistic seat-allocation model and a bias-correction step turn them into seat probabilities.
  - Works with historical counts, AVL and real-time counts, and is described as "robust to varying data availability".
  - Tested on a Stockholm bus line. The abstract gives no numeric accuracy figures.
- Arabghalizi & Labrinidis frame Pittsburgh bus crowding two ways: predicting the load (regression) and predicting the crowding level within 15-minute windows (classification). [M, snippet] — [Pitt PDF](https://db.cs.pitt.edu/assets/pdf/2020.tdasci.ArabghaliziL20.pdf)
- A Bayesian regime-switching model forecasts travel time and occupancy together, as a probabilistic alternative to "deterministic models, providing only point estimates". [M, snippet] — [arXiv 2401.17387](https://arxiv.org/abs/2401.17387v1)
- Bus demand in New York "might exhibit overdispersion, making a negative binomial model more appropriate" (Pittsburgh excess-demand paper). [M, snippet] — [arXiv 2208.06372](https://arxiv.org/pdf/2208.06372)
- APC data are noisy too: in a 2026 study, about 47% of trips had at least one negative ridership reading. [W/M, snippet] — [arXiv 2605.00083](https://arxiv.org/pdf/2605.00083)
- Kay et al. (CHI 2016): quantile dotplots of bus-arrival predictions made users' probability estimates less variable than density plots did. [M] — [UW IDL](https://idl.uw.edu/papers/when-ish-is-my-bus); [PDF](https://vis.mit.edu/classes/6.859/readings/pdfs/Kay-WhenishIsMyBus.pdf)
- Fernandes et al. (CHI 2018) ran an incentivised bus-catching experiment. [M] — [MU Collective](https://mucollective.northwestern.edu/project/uncertainty-bus)
  - Quantile dotplots gave better choices than the control, with expected payoffs near the optimum and more consistent choices.
  - CDF plots did almost as well; text descriptions of uncertainty did worse.
- A 2023 study (Frans et al., cited in a hEART 2024 abstract) found no direct link between visualisation format and decision quality, so the benefit is not settled. [W] — [hEART 2024](https://transp-or.epfl.ch/heart/2024/abstracts/hEART_2024_paper_2594.pdf)
- Stockholm metro pilot of live crowding information (Zhang, Jenelius & Kottenhoff 2017). [M] — [WTR](https://www.worldtransitresearch.info/research/6591); [Springer](https://link.springer.com/doi/10.1007/s12469-016-0150-y)
  - About 25% of passengers noticed the information, understood it and found it useful.
  - On trains that were crowded on arrival, the share boarding the most crowded car fell by 4.3 percentage points and the share boarding the second car rose by 4.1.
- A follow-up simulation (Peftitsi, Jenelius & Cats 2022) found car-level crowding information spreads passengers more evenly. The benefit grows with demand but levels off. [M] — [RePEc](https://econpapers.repec.org/RePEc:eee:transa:v:166:y:2022:i:c:p:354-368)
- Google Maps ranks occupancy sources as: user feedback first, then the agency's real-time feed, then Google's own predictions. It shows 4 crowdedness levels. [S] — [Google Transit Partners](https://support.google.com/transitpartners/answer/10106342?hl=en)

### Inferences

**Estimating overdispersion without knowing the capture rate.**

- Suppose:
  - the true load is L ~ Poisson(λ) with λ ~ Gamma(k, μ/k), i.e. L ~ NB(μ, k)
  - each passenger is an e-ticket holder with probability π
- Then the e-ticket count is Y ~ NB(πμ, k): **k is unchanged by the sampling.**
- So k can be estimated from the vehicle-linked e-tickets:
  - By method of moments: Var(Y) − Ȳ = Ȳ²/k.
  - Pool k across cells (for example a regression of log k on route type and time period), because a single cell has only about 0.5–3 e-tickets per trip-segment.
- Caveat: if π differs between trips within a cell (for example, some conductors push QR tickets), the apparent dispersion rises and k is underestimated. The resulting intervals are wider, i.e. conservative.

**Illustration** (my calculation, thresholds 35 and 60):

| Cell mean μ | Dispersion | P(L ≤ 35) | P(35 < L ≤ 60) | P(L > 60) |
|---|---|---|---|---|
| 25 | k = 3 to 10 | 0.79–0.87 | 0.13–0.18 | 0.00–0.03 |
| 45 | k = 3 to 10 | 0.29–0.43 | 0.34–0.55 | 0.16–0.24 |
| 45 | Poisson | 0.07 | 0.91 | 0.01 |
| 60 | k = 3 to 10 | 0.10–0.27 | 0.31–0.45 | 0.42–0.45 |

Labelling a cell by its mean hides a large probability of being in another class. Treating the load as Poisson badly underestimates it.

**Make the mean specific to each trip using GPS.**

- At stops where passengers arrive at random, boardings grow with the gap since the previous bus (bunching).
- Fit log E[Y_trip] = cell effect + β·log(previous headway) + lateness + day-of-week on the linked trips.
- This explains part of the trip-to-trip variation, which raises k and sharpens the probabilities.

**P(seat).**

- Simple version: P(load after departing stop s ≤ seats).
- Better: Jenelius-style seat allocation, where standees can get a seat as others alight downstream.

**Carry the expansion uncertainty through.**

- Draw π_r and f_c from their priors or posteriors (for example lognormal, ±25–30%).
- Mix these draws into the predictive distribution of L.
- Report class probabilities and an 80% interval. In low-capture cells the uncertainty in the level dominates, and the output should say so.

**How to show it.**

- A 3-segment bar per trip, e.g. "Seats likely 60% / Standing 30% / Crowded 10%", or a 20-dot quantile dotplot.
- Flag low-confidence cells.
- Publish a GTFS-RT OccupancyStatus only when the top class probability is at least about 0.6. Otherwise publish nothing, or show "uncertain".

**How to score it.**

- Use the log score or CRPS on held-out e-ticket counts, through the predictive distribution of e-ticket counts.
- Use the Brier score on the class probabilities (see section 3).

### Gaps

- I could not get Jenelius's full text, so I have no numbers on how well-calibrated the P(seat) predictions are.
- I found no published overdispersion (k) values for Indian bus loads; k has to be estimated locally.
- I found no study of how Indian riders use crowding information. The live-crowding evidence is mostly from metros.
- I found no study that predicts crowding classes from a ticket sample as small as Delhi's.

## 3. Validation without APC (holdout, split-half, proxy ground truth, what reviewers accept, studies that checked ticket-based loads against counts)

### Takeaway

- **Week-to-week correlation measures repeatability, not accuracy.** It cannot detect level or bias errors.
- **Strong evidence** consists of:
  - out-of-sample proper scores on held-out trips, using the vehicle-linked tickets
  - calibration of the predicted probabilities
  - consistency with independent totals (by operator)
  - physical plausibility (how often capacity is exceeded)
  - a small ground-truth sample (stop-side point checks or ride checks) with confidence intervals
- **The standards reviewers know** come from APC certification: VDV 457 requires error within 1–2% against manual counts on at least 1,000 passengers, and the US NTD requires ±10% at 95% confidence for sampled totals.
- **Limit of the literature:** published checks of ticket-based OD against counts or surveys (London BODS, Santiago) report agreement mostly at OD or stop level, not as load errors.

### Cited Findings

- VDV 457, the German APC standard [M] — [Mass Transit](https://www.masstransitmag.com/technology/article/12128610/defining-apc-accuracy-standards-in-north-america):
  - Acceptance needs a certified third-party auditor.
  - Cumulative boardings and alightings must each be within 2% of manual counts, on a sample of more than 1,000 passengers.
  - At stop level: 85% of door cycles counted exactly, 90% of stops within ±1 passenger, 97% within ±2.
- Another source says APC systems are now expected to have "a maximal systematic error or bias of 1%" (99% accuracy). Earlier VDV versions checked this with a t-test, which controls only the type I error; an equivalence test has since replaced it. [M] — [arXiv 1802.03341](https://arxiv.org/pdf/1802.03341v3); [arXiv 2104.09697](https://arxiv.org/pdf/2104.09697)
  - These two sources conflict (2% vs 1%). They probably refer to different versions or metrics.
- In the US, no standard defines APC accuracy; tenders often ask for more than 95%. [M] — [Mass Transit](https://www.masstransitmag.com/technology/article/12128610/defining-apc-accuracy-standards-in-north-america)
- FTA's National Transit Database (NTD) [M] — [Mass Transit](https://www.masstransitmag.com/technology/article/12128610/defining-apc-accuracy-standards-in-north-america):
  - Agencies must report 100% counts where those are "available and reliable".
  - Otherwise they must sample, with at least 95% confidence and ±10% precision.
- An FTA guidebook requires agencies to show that APC data are statistically equivalent to paired manual counts. [M, snippet] — [ROSA P](https://rosap.ntl.bts.gov/view/dot/31344/dot_31344_DS1.pdf)
- An Italian test of a commercial infrared APC found small but statistically significant errors and a tendency to undercount boardings. [M, snippet] — [Olivo, Maternini & Barabino, TOTJ 13](https://www.benthamopen.com/FULLTEXT/TOTJ-13-250)
- Wi-Fi sensing on buses [M, snippet] — [PoliTo](https://iris.polito.it/retrieve/handle/11583/3000780/913141); [Aalborg Univ.](https://vbn.aau.dk/files/249577203/public_transport_occupancy_estimation_using_wlan_probing.pdf):
  - A Torino study found a mean Pearson r of 0.75 against ground truth.
  - An Aalborg study found overcounting from devices outside the bus and undercounting from passengers without devices.
- London ODX vs the BODS survey showed only "small stop-by-stop differences", and BODS undercounted when its return rates were 50–80%. [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- Wang et al. (2011) describe their study as the first known check of smart-card bus OD against manual survey data. [M] — [DSpace@MIT](https://dspace.mit.edu/handle/1721.1/110021)
- Santiago: trip stages about 90% correct; validation against large OD surveys was "still to be conducted". [W/M] — [Munizaga webinar](https://de.slideshare.net/BRTCoE/webinar-using-smart-card-and-gps-data-for-policy-and-planning-the-case-of-transantiago)
- Devillaine et al. propose endogenous and exogenous validation of passive-data OD. [M] — [Emerald](https://emerald.com/insight/content/doi/10.1108/9781781902882-038)

### Inferences

**Why the current metric cannot show gains.**

- Pearson r does not change if the estimates are multiplied by a constant or shifted. So a wrong global expansion factor cancels out completely.
- Both weeks share the same route-level factors. If some routes are over-expanded, the spread between cells grows, and the week-to-week r can actually *rise*. Errors can therefore make the metric look better.
- Report level-sensitive metrics as well: bias, MAE against totals, and the rate of capacity breaches.

**Validation protocol (fits in one week).**

1. **Split-half reliability.**
   - Split the tickets of one week at random (by ticket id) into halves A and B, and compute r_AB.
   - Reliability ρ = 2r_AB/(1 + r_AB) (Spearman–Brown).
   - If ρ is much higher than the week-to-week r, the disagreement between weeks is real weekly variation, and smoothing cannot help (consistent with the Empirical-Bayes result).
   - If ρ is close to the week-to-week r, noise dominates and more pooling would help.
2. **Trip-level holdout using the vehicle-linked tickets.**
   - Hold out week 2, or a random 20% of trips.
   - Predict each trip-segment's e-ticket count Y with NB(π̂μ̂_t, k̂), and score with the log score, CRPS and a PIT histogram.
   - Compare against a ladder of baselines: Poisson cell mean → negative binomial → plus headway → plus Empirical-Bayes.
   - This tests both the shape of the distribution and relative levels, without any APC.
3. **Checks on the level (validity).**
   - Expanded paid riders by operator vs the Economic Survey totals × the paid share.
   - Share of trips or cells above crush capacity (target about 0; report before and after the fixes).
   - Rank correlation between route boardings and scheduled frequency (GTFS trips per hour), since frequency is planned around demand. This is a weak check.
   - ETM route totals, if they can be obtained.
4. **Small ground-truth campaign.**
   - Place observers at 4–6 busy stops. For each bus they record:
     - the vehicle number
     - the time
     - the occupancy class (seats free / seats full with some standing / crowded), plus a photo if possible
   - Match each observation to its GPS trip.
   - 95% confidence intervals on classification accuracy (if accuracy is about 70%):

     | Number of checks | 95% CI |
     |---|---|
     | 50 | ±12.7 percentage points |
     | 100 | ±9.0 percentage points |
     | 200 | ±6.4 percentage points |

   - Stratify the checks by predicted class so that "crowded" predictions actually get tested.
   - Report a confusion matrix and the Brier score of P(class).
   - Ride checks on 5–10 complete trips, counting boardings and alightings, give an MAE for loads.
   - If on-board CCTV footage can be obtained, it is another source; access and privacy are unknown.

**What reviewers are likely to accept.** A hackathon cannot meet APC-style tolerances (1–2%) for loads. The strongest package is:

- out-of-sample scores against simple baselines
- a reliability diagram for P(crowded)
- an independent ground-truth sample with confidence intervals
- consistency with operator totals
- sensitivity of the outputs to π, f and p

Present repeatability and validity as two separate claims.

### Gaps

- I found no published validation of loads built from a small digital-ticket sample against counts.
- I found no Indian study comparing ETM-based loads with manual counts and reporting error statistics.
- I have no load-level error numbers for London or Santiago, only OD/stop-level statements.
- The current VDV 457 thresholds differ between secondary sources.
- I don't know whether DTC's CCTV footage or ETM data could be used for validation.

## 4. Free and concession riders (pink tickets / Pink Saheli card, passes)

### Takeaway

- **Size.** Free riders are probably 40–50% of Delhi bus boardings. The reported women's share is 33% (official, 2022–23), 42% (WRI India, 2023) and about 51% (press, Jan–Jun 2025). Leaving them out makes loads about 1.7–2× too low on average, and more where women ride most.
- **The data exist.** Pink tickets were ETM-issued and reimbursed per ticket, and Saheli card taps have been recorded digitally since November 2025. Route × hour aggregates should be requested.
- **Until then**, use a free-share prior for each cell and carry its uncertainty through.
- **Missing data.** I found no quantitative data on how the free share varies by hour or route, or on the pass-holder share.

### Cited Findings

**Women's share and pink ticket volumes in Delhi**

| Period | Women's share or pink share | Source |
|---|---|---|
| 2020–21 → 2022–23 | 25% → 33% (official) | [Ideas for India](https://www.ideasforindia.in/topics/social-identity/fighting-gender-inequality-through-mobility-assessing-delhi-s-pink-ticket-scheme.html) [M] |
| 2019 → 2023 | 33% → 42% (WRI India, March 2025) | [ThePrint](https://theprint.in/india/governance/aaps-free-bus-ride-scheme-helped-delhi-women-save-up-to-8-get-access-to-better-jobs-wri-india-paper/2536921) [W/M, snippet, page blocked]; [WRI India paper](https://wri-india.org/sites/default/files/Working-paper-WRI-India-Fare-free-bus-travel-scheme-for-women-Lessons-from-Delhi.pdf) |
| Launch, Oct–Nov 2019 | Pink share of tickets issued: 35% (day 1) → 41% (Nov 10) → 42% (Nov 19) | [Scroll](https://scroll.in/article/944568/scroll_in) [W, snippet] |
| Jan–Jun 2025 | ≈14.79 lakh women vs ≈14.25 lakh men per day (≈51% women) | [Business Standard](https://www.business-standard.com/india-news/692-cng-buses-to-go-off-road-by-year-end-after-route-rationalisation-dtc-125112200598_1.html) [W, snippet; page returned 403] |
| From Nov 2025 | Women and transgender residents ≈ half of daily ridership; more than 10 lakh women a day | [The Logical Indian](https://thelogicalindian.com/delhi-launches-pink-saheli-smart-card-for-women-and-transgenders-free-bus-travel-digital-access-and-inclusive-mobility-revolution/) [W] |

Notes on these figures:

- Ideas for India also reports more than 1,530 million pink tickets by February 2024 (government estimate). Its linked headline says 100 crore (1,000 million), so the figures are inconsistent.
- In the 2019 launch period, more pink passes were issued in DTC buses than in DIMTS cluster buses ([Scroll](https://scroll.in/article/944568/scroll_in)).
- The 2025 total in the Business Standard figure (≈29 lakh) does not match the Economic Survey's ≈40.8 lakh for FY2024–25. It is probably DTC-only or uses a different definition.
- Another report gives "35 lakh women rode DTC buses in the first six days of October" (about 5.8 lakh a day on DTC). Its date and definition are unclear, and it conflicts with the other figures. [W] — [NewKerala](https://www.newkerala.com/news/a/pink-saheli-takes-off-35-lakh-women-ride-132.htm)

**Other findings**

- The Ideas for India survey of 510 women at 50 stops [M] — [Ideas for India](https://www.ideasforindia.in/topics/social-identity/fighting-gender-inequality-through-mobility-assessing-delhi-s-pink-ticket-scheme.html):
  - 45% never use buses and 35% are regular users.
  - Among women from low-income households, 75% are regular users.
  - The scheme increased bus use for 23% of current riders.
  - Use clearly differs by income, which suggests the free share differs by route and area.
- Operators were reimbursed per pink ticket issued; about 1,000 million pink tickets were issued between October 2019 and January 2023. [M] — [Ashoka DP-105](https://dp.ashoka.edu.in/dp/RePEc/ash/wpaper/paper105_0.pdf)
- Free travel was extended to transgender passengers. [W] — [Attitude](https://www.attitude.co.uk/news/delhi-expands-free-bus-travel-scheme-transgender-passengers-516638/)
- Women, especially those from low-income groups, often travel off-peak (a qualitative statement). [W] — [Daily Pioneer](https://dailypioneer.com/news/beyond-bus-fare-subsidy-schemes-tracing-urban-women-s-access-to-gender-responsive-mobility)
- Bengaluru (Shakti scheme), from an Azim Premji University study of 2023–25 trip records [M/W] — [The Week](https://www.theweek.in/wire-updates/national/2025/11/06/mds9-ka-shakti-scheme-study.html); [Asianet Newsable](https://newsable.asianetnews.com/karnataka-news/shakti-scheme-boosts-women-public-transport-use-bengaluru-study-articleshow-n4ukg10):
  - Women's share of passengers rose from 40% to 62%.
  - Average daily female passengers rose 151%, from 5.06 to 12.72 lakh.
- DTC's May 2026 commuter survey for route rationalisation reportedly collects the type of pass held. [W, secondary] — [Swarajya](https://swarajyamag.com/amp/story/news-brief/delhi-dtc-launches-citywide-travel-survey-to-redesign-bus-routes-seeks-commuter-data-on-habits-safety-and-service-gaps)

### Inferences

**How much is missing.**

- With f ≈ 0.40–0.50 and p ≈ 0.03–0.10 (the pass share is unknown), paid-only loads need multiplying by 1/(1 − f − p), i.e. about 1.7–2.3 on average.
- Today's outputs (paid e-tickets × 28.6) are too low where π ≈ 3.5% really holds, and too high where π is higher. These errors partly cancel, which may be why the aggregate peaks "look right".

**Free share per cell, without operator data.**

- Use f_c = f_network × g(hour) × h(operator) × s(area), where:
  - f_network ≈ 0.45 (range 0.40–0.51)
  - g = time-of-day factor (no Delhi numbers found; treat as uncertain, e.g. an off-peak uplift of 1.0–1.2)
  - h = operator factor (DTC higher than cluster in 2019)
  - s = area factor (low-income areas higher, based on the survey above)
- Carry the uncertainty in f_c through to P(class) (section 2), and include a sensitivity table.

**Quick checks in the data.**

- Look for zero-fare e-tickets, or any gender or concession field.
- Press describes the Saheli card as being for residents, so non-resident women may still buy tickets. Their e-tickets are therefore not a proxy for free riders.

**Data requests.**

- Saheli card taps by route × hour; these have been digital since November 2025.
- A pass-sales or validation summary.

**Passes.** Pass use is probably concentrated in commute peaks and on student corridors (my guess, not sourced). Until data arrive, model p_c as 0.05 ± 0.05.

### Gaps

- I found no published figures for Delhi's pink/Saheli share by hour, route, depot, or distance or fare slab.
- I found no figure for the share of riders using passes.
- Reported women's shares differ by year and definition (33%, 42%, ~51%).
- I could not confirm the Saheli residency rule or its effect on paid trips by women.
- I don't know whether the ONDC channel ever issues zero-fare tickets.

## 5. Bus capacity differences and how crowding classes are defined (GTFS-RT OccupancyStatus, TCQSM)

### Takeaway

- **The fleet mixes two sizes:**
  - 9 m DEVI buses: 23 seats + 13 standing = 36
  - 12 m buses: for example the Switch EiV12 with 39 seats and up to about 63 in total
- **Fixed thresholds mislabel the 9 m bus.** The current thresholds of 35 and 60 are wrong for it: 35 is already its full legal capacity, and 60 is about 1.7 times it.
- **Define classes per bus.** Base them on the load factor (passengers per seat), using the TCQSM bands and legal capacity. Map them to the GTFS-RT OccupancyStatus values and Google's four levels.
- **Thresholds are up to the publisher.** GTFS-RT leaves the "many/few seats" thresholds to whoever produces the feed.

### Cited Findings

- GTFS-RT OccupancyStatus values and how Google displays them [S] — [Google Transit Partners](https://support.google.com/transitpartners/answer/10106342?hl=en):

| OccupancyStatus | Google level | Meaning |
|---|---|---|
| EMPTY, MANY_SEATS_AVAILABLE | 0 "not crowded" | Many seats free; "many" is set by the producer |
| FEW_SEATS_AVAILABLE | 1 "not too crowded" | Few seats free; "few" is set by the producer |
| STANDING_ROOM_ONLY | 2 "crowded" | Only standing space |
| CRUSHED_STANDING_ROOM_ONLY, FULL | 3 "very crowded" | Little standing space / full |
| NOT_ACCEPTING_PASSENGERS | not shown | Not taking passengers |

- Producers may send a subset of these values (for example 3 levels). [S] — [Google Transit Partners](https://support.google.com/transitpartners/answer/10106342?hl=en)
- The SIRI Nordic profile sets STANDING_ROOM_ONLY at fewer than about 10% of seats free. [W/M, snippet] — [OpenTripPlanner docs](https://docs.opentripplanner.org/api/dev-2.x/graphql-gtfs/types/OccupancyStatus)
- TCQSM 3rd edition load-factor bands (passengers per seat), as reproduced in a Malaysian bus study [M] — [EASTS (J-STAGE)](https://www.jstage.jst.go.jp/article/easts/13/0/13_1361/_article/-char/en):

| Level of service | Passengers per seat | Description |
|---|---|---|
| A | 0.00–0.50 | |
| B | 0.51–0.75 | |
| C | 0.76–1.00 | |
| D | 1.01–1.25 | "comfortable standee load for design" |
| E | 1.26–1.50 | "maximum schedule load" |
| F | >1.50 | crush load |

  - The F band comes from a secondary document of unclear origin and is weak evidence.
- TCQSM (p. 8-66, for rail cars): 4.3 ft² (≈0.40 m², ≈2.5 people/m²) per standee means standing without body contact; 3.2 ft² (≈0.30 m², ≈3.4/m²) means some body contact. [M] — [ITDP BRT Planning Guide](https://brtguide.itdp.org/branch/master/guide/why-brt/performance)
- DEVI 9 m electric bus: 23 seats (6 reserved for women) plus room for 13 standing. [W/M] — [Autocar Pro](https://www.autocarpro.in/news/delhi-government-introduces-devi-electric-bus-fleet-for-improved-connectivity-126223)
  - The August 2026 batch is probably PMI's Regio in the 23-seat version (Electrive's own inference). [W] — [Electrive](https://www.electrive.com/2026/08/25/india-delhi-deploys-200-new-electric-buses-for-public-transport/)
- Switch EiV12 12 m low-floor bus: 39 seats [W] — [Autocar Pro](https://www.autocarpro.in/news/switch-mobility-delivers-first-batch-of-eiv12-electric-buses-to-delhi-transport-department-128276)
  - "Up to 63 passengers including 39 seated and 24 standing", depending on layout. Only one source gives this, and I could not confirm which article. [W] — [Electrive](https://www.electrive.com/2026/02/09/india-delhi-flags-off-a-new-batch-of-500-electric-buses/)
- DTC ordered 1,500 Tata 12 m low-floor AC electric buses (no capacity given). [W] — [91trucks](https://www.91trucks.com/news/tata-motors-bags-delhi-transport-corps-order-for-1500-e-buses)
- Route rationalisation was triggered by the phased retirement of 15-year-old low-floor CNG buses. [W] — [The Statesman](https://www.thestatesman.com/cities/iit-delhi-to-soon-complete-dtc-route-rationalisation-study-for-devi-buses-1503584876.html)

### Inferences

**Class thresholds per bus type.** LF = load / seats.

| Class | GTFS-RT status | Google level | Rule | DEVI 9 m (23 seats, 36 legal) | 12 m EiV12 (39 seats, ~63 legal) |
|---|---|---|---|---|---|
| Many seats | MANY_SEATS_AVAILABLE | 0 | LF ≤ 0.75 (TCQSM A–B) | ≤17 | ≤29 |
| Few seats | FEW_SEATS_AVAILABLE | 1 | 0.75 < LF ≤ 1.0 (TCQSM C) | 18–23 | 30–39 |
| Standing | STANDING_ROOM_ONLY | 2 | seats < load ≤ legal capacity | 24–36 | 40–63 |
| Crowded / over capacity | CRUSHED_STANDING_ROOM_ONLY or FULL | 3 | load > legal capacity | >36 | >63 |

**How the current 35/60 thresholds compare.**

- 12 m buses: they roughly fit (35 ≈ LF 0.9; 60 ≈ legal capacity).
- DEVI buses: they badly under-report crowding. A completely full DEVI (about 35 people) would be labelled "seats available", and "crowded" (over 60) is physically near-impossible.

**Replace the global cap of 100.**

- Use a crush capacity per bus type, for example legal capacity × 1.3–1.5. This is my choice; I found no Indian standard.
- Use it in three places:
  - to truncate the negative binomial
  - as the constraint in section 1
  - in the capacity-breach metric

**Telling bus types apart.**

- Map the GPS vehicle id (registration) to a fleet list (DEVI/9 m vs 12 m, AC, operator), from procurement lists, depot lists or the GPS feed's metadata.
- Tickets without a vehicle number: use the route's fleet mix as a probability weight.
- DEVI buses run on specific feeder routes, so the route is also informative (not verified).

### Gaps

- I could not verify the Indian bus-body code (AIS-052) or the Urban Bus Specifications (UBS-II) values for standing area or density per passenger.
- I could not find official capacities for the 12 m CNG low-floor buses or the Tata/JBM electric buses.
- I did not retrieve the TCQSM's standing-area bands for buses (only the rail figures), and I don't know whether the 4th edition changed the bands.
- Delhi has no published OccupancyStatus convention.

## 6. Declared destination vs actual alighting (over- and under-riding) and assigning segments to times

### Takeaway

- **No direct evidence.** I found no published measurement of over- or under-riding for Indian app tickets or conductor tickets. The nearest evidence is destination-inference validation:
  - London: 74.6% of destinations inferred, using 750 m–1 km tolerances
  - Santiago: about 90% of trip stages correct
- **What to do instead:**
  - Test declared destinations for heaping (bunching on terminals or fare-slab end stops), and with trip chaining if there is a user or device id.
  - Spread heaped destinations out using a multinomial alighting model.
  - Put segment loads on the times the bus actually passes them (GPS).
  - Assign unlinked tickets to candidate trips with soft weights, using a boarding-lag distribution learned from linked tickets. This pays off at trip level, not in hourly cells.

### Cited Findings

- London ODX destination inference [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf):
  - 74.5% of alighting times and locations inferred within 1 km of the next Oyster tap.
  - 5% were the rider's only transaction that day.
  - 6.7% were beyond the maximum distance of 750 m.
  - 3.2–3.6% were on buses heading away from the origin.
- London origin times: 96% within ±5 min of the matched iBus record. [S] — [MIT lecture](https://ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/885a09028bf362983423907d32d179d5_MIT1_258JS17_lec10.pdf)
- Santiago: trip-stage estimates about 90% correct. [W/M] — [Munizaga webinar](https://de.slideshare.net/BRTCoE/webinar-using-smart-card-and-gps-data-for-policy-and-planning-the-case-of-transantiago)
- Bogotá validates only on entry, so destinations must be inferred. [M] — [arXiv 2112.04009](https://arxiv.org/html/2112.04009v2)
- Alightings modelled as multinomial given the boarding stop, with uncertainty, beat IPF on 3 routes. [M] — [arXiv 2403.04742](https://arxiv.org/abs/2403.04742)
- IPF with an iteratively improved base matrix beats null-base IPF. [M] — [ASCE 2014](https://ascelibrary.com/doi/10.1061/%28ASCE%29TE.1943-5436.0000647)

### Inferences

**Ways a declared destination can be wrong.** Delhi fares come in a few distance slabs, so a declared destination may not be where the rider gets off:

- Riders may choose the terminal or the last stop in their slab.
- Riders may declare a nearer stop to pay less, then ride further.

Both distort loads on the last segments of a route.

**Tests to run.**

- **Heaping index:** the share of destinations at terminals or slab-end stops, compared with the smooth shape of the other stops.
- **Trip chaining**, if a user or device id exists: the distance from the declared destination to the same user's next boarding that day. The share within 750 m–1 km gives a consistency rate; London's 74.5% within 1 km for inferred destinations is a benchmark.
- **Validity check on linked tickets:** if tickets expire after a set time, compare that with when the bus reaches the declared stop.

**Corrections.**

- Spread heaped destinations out using the alighting distribution of tickets that are not heaped, from the same origin and hour (multinomial or Bayesian OD).
- Report the change in the busiest segment's load under "declared" vs "redistributed" destinations as an uncertainty band.

**Assigning segments to times.**

- Vehicle-linked tickets: use the GPS trajectory of that trip, which is exact.
- Unlinked tickets:
  1. Learn the lag from purchase time to boarding using linked tickets (purchase timestamp vs when the linked bus passes the origin stop).
  2. Assign each ticket to candidate trips on the same route and direction, with weights proportional to the lag density.
  3. Count the ticket on each segment at the time the bus passes it.
- Expect gains at trip level (bunching, shoulders of the peak, long routes), not in the hourly week-to-week metric.

**Check for selection bias.**

- Compare the OD length, fare slab and time-of-day mix of tickets with and without a vehicle number.
- If they look alike, the linked half can be used to calibrate lag and dispersion for all tickets. If they differ, weight the two groups separately.
- I could not confirm that tickets with a vehicle number come from scanning a QR code on board.

### Gaps

- I found no data on over- or under-riding for Delhi e-tickets or Indian conductor tickets.
- I could not confirm whether Delhi QR tickets expire after a set time, how they are inspected, or whether they carry a persistent user id, so I can't say whether trip chaining is possible.
- I found no study of the lag from purchase to boarding for Indian mobile bus tickets.
