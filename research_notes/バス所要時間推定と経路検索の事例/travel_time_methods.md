# Bus travel-time / ETA estimation from AVL/GPS: methods, accuracy, preprocessing, tools

Context: Delhi Transport Stack Hackathon Problem 1. The journey planner's in-vehicle times come from observed GPS speeds that vary by time of day and day of week, and it is judged against actual trip times and against Google Maps. The notes are organised by the four key questions. A method-landscape table comes first under Q1.

Metric caveat: studies report MAPE, MAE or RMSE at very different scales (one link, a 500 m section, a whole 32-link journey, or a 1–5 km "shingle"). The numbers below are not directly comparable across papers. Compare only within a paper.

---

## Q1. How accurate are simple baselines (historical mean or median by segment × time bin) compared with ML and deep models, and how big is the gain?

### Takeaway
When the comparison is fair, a historical average by link × day-of-week × time-of-day is a strong baseline. On a congested Copenhagen line it scored 6.5% journey-level MAPE, roughly as good as Google Traffic (6.3%). It also beat the agency's own production model at short horizons. Deep models (ConvLSTM) gain about 2 percentage points of MAPE, or about 1.2 minutes of MAE on a roughly 50-minute journey. The largest gain comes from real-time information about the current day, not from the model class. For predicting bus times from car traffic, Google's BusTr found that "car-traffic ETA only" gives 35.6% MAPE, linear regression gives 22.9% and the full model gives 13.2%. So naively using car ETAs for buses is poor.

### Cited Findings

**Head-to-head with a historical baseline (the most useful evidence)**
- Petersen, Rodrigues and Pereira (Movia/DTU, arXiv 1903.02791; published in Expert Systems with Applications 2019) used 1.2M AVL link travel-time observations for Copenhagen bus line 4A, May–Oct 2017, over the first 32 links. Data were aggregated into 15-minute bins (about 1.7 observations per bin; headway 7.5 min). They trained on 23 weeks and tested on 1 week with a sliding window, over 4 test weeks. Errors are summed over all 32 links, which is equivalent to a whole-journey ETA, daytime 06–22 only. — [arXiv 1903.02791](https://arxiv.org/pdf/1903.02791)
  - Historical average (mean per link × day of week × time of day): RMSE 4.35 min, MAE 3.23 min, MAPE 6.51%. It does not depend on the horizon.
  - Movia's deployed "current model" (historical average plus rule-based overrides): MAE 3.90, 3.46 and 4.15 min at +15, +30 and +45 min. This is worse than the plain historical average.
  - Pure LSTM: MAE 2.48, 2.51 and 2.62 min; MAPE 5.02–5.34%.
  - Google Traffic (Google Maps) at +15 min: MAE 2.96 min, MAPE 6.32%.
  - ConvLSTM, multi-link and multi-step: MAE 1.99, 2.11 and 2.27 min; MAPE 4.19–4.75%; RMSE 2.66–3.11 min.
  - Gain of the best deep model over the historical average: about 38% lower MAE (3.23 to 1.99 min), and 2.3 percentage points of MAPE.
- Google BusTr (KDD 2020, arXiv 2007.00882) predicts bus travel time over 1–5 km route "shingles" from real-time road-traffic forecasts plus route and stop context. It is deployed in Google Maps for cities without real-time bus feeds. — [arXiv 2007.00882](https://arxiv.org/pdf/2007.00882)
  - "Zero-th order" baseline, which uses car-traffic ETA as the bus ETA: MAPE 35.6%.
  - Linear regression on three features (number of stops, distance, car-traffic time estimate): MAPE 22.9%.
  - BusTr full model: MAPE 13.24% (std 0.045 over 20 runs).
  - DeepTTE retuned in the same setting: mean MAPE 31.5% (21.2% excluding non-converging runs).
  - Ablations: removing road traffic gives 15.4% MAPE (+16%). Removing time of week gives 13.9% (+5%). Removing route ID gives 13.6%. Removing all spatial context gives 22.2%, only about 4% better than the linear baseline.
  - Generalisation: new routes over 9 weeks give 15.5% MAPE, and new areas give 19.6%.
  - The model does not use schedules. The Google blog describes training on agency real-time bus positions aligned with car speeds on the same path, and learning time-of-day and day-of-week effects. Its Sydney example tracked real bus motion within about 1.5 minutes. — [Google Research blog](https://research.google/blog/predicting-bus-delays-with-machine-learning/)
  - The system launched first in India in 2019 and then expanded to hundreds of cities. — [Google Research blog](https://research.google/blog/predicting-bus-delays-with-machine-learning/)

**Results cited inside BusTr's literature review (secondary)**
- DeepTTE (Wang et al., AAAI 2018) is a GPS-trajectory deep model reported at 11.89% MAPE in Chengdu and 10.92% in a second city (taxi data). An attention model is reported at 14.8% MAPE. — [BusTr §2](https://arxiv.org/pdf/2007.00882)
- An MLP with k-means regime switching is reported at 14–22% MAPE. — [BusTr §2](https://arxiv.org/pdf/2007.00882)
- Dhivyabharathi et al. (IIT Madras, Chennai): seasonal AR gives 17–19% MAPE on one route, against an MLP at 20–24%. In this case the simpler time-series model beat the neural network. — [BusTr §2](https://arxiv.org/pdf/2007.00882)

**India (Chennai, IIT Madras): closest analogue to Delhi heterogeneous traffic**
- Log-normal AR paper (arXiv 1904.03444): MTC route 19B, about 30 km, 25 stops, 14 signals, headway about 20 min. Data are 34 days of GPS at 5-second intervals (27 days for training, 7 for testing). The route was cut into 500 m sections, the average inter-stop distance. Modelling travel times as log-normal improved accuracy over Gaussian. The proposed seasonal AR and non-stationary AR beat historical average, exponential smoothing, ARIMA and ANN. Exact per-method MAPE values are in figures that could not be extracted. — [arXiv 1904.03444](https://arxiv.org/pdf/1904.03444)
- IIT Madras work also found a Kalman filter significantly better than the average method. A k-NN study on Chennai bus GPS reported 11.68–29.60% MAPE across trip variations. For MTC routes 5C (15 km) and 19B (30 km), 2,227 trips over 45 days were used for a web-based predictor. — [Search summary of IITM sources](https://coeut.iitm.ac.in/APTS_Finalreport_2016.pdf); [Research Matters](https://researchmatters.in/article/predicting-unpredictable-%E2%80%93-scientists-design-system-predict-bus-timings)

**Tree ensembles (XGBoost, RF, LightGBM)**
- Guangzhou, one line, 28 days, inter-stop travel time: XGBoost MAE 137.01 against LightGBM 151.57 (units as reported). XGBoost also beat KNN and a BP neural network. — [Zhu et al. 2022, Wiley WCMC](https://onlinelibrary.wiley.com/doi/10.1155/2022/3504704)
- Phnom Penh bus arrival: XGBoost MAE 16 s, RMSE 28.03 s, MAPE 2.61% using historical bus data and weather. The very low error suggests short legs. — [ITC Cambodia journal](https://techno-srj.itc.edu.kh/public/journal/document/6-Bus%20Arrival%20Time%20Prediction%20Using%20Machine%20Learning%20Approaches.pdf)
- Bandung BRT: RF slightly better than XGBoost. One study reports RF with R² 0.789, RMSE 3.59 min and MAE 1.87 min, ahead of XGBoost and an MLP. — [MDPI IoT 7(1):22](https://www.mdpi.com/2624-831X/7/1/22)
- In a general tree-ensemble comparison, XGBoost had the best RMSE, but RF and LightGBM were only slightly worse and trained much faster. — [arXiv 2005.13818](https://arxiv.org/pdf/2005.13818)
- UTS chapter: moving average MAE 0.72, linear regression 0.55, SVR 0.54, proposed ML 0.50 (units unclear). The baseline-to-best gap is modest. — [UTS chapter](https://opus.lib.uts.edu.au/bitstream/10453/165246/2/chapter_bus_travel_time_prediction_Yuming.pdf)
- An ICCS 2022 review reports a best MAE of roughly 60–70 s for longer bus lines and notes that hybrid ANN approaches need much larger datasets. — [ICCS 2022](https://www.iccs-meeting.org/archive/iccs2022/papers/133510662.pdf)

**Kalman filters**
- TheTransitClock's Kalman filter models travel time and dwell time separately, using the last weeks, days and hours. In a one-month Minneapolis–St Paul Metro Transit deployment (900+ buses, 167 routes), its errors were more tightly distributed than the schedule-based engine's, especially at short horizons. The comparison was against schedule or regression, not a historical-average baseline. — [Springer NETS 2023](https://link.springer.com/article/10.1007/s11067-021-09541-w); [TransitClock wiki: Kalman testing](https://github.com/TheTransitClock/transitime/wiki/Prediction-Kalman-testing)
- Kalman filters "usually fail to handle abrupt change between consecutive travel times". ANN models outperformed KF in one comparison. A hybrid NN+KF reported an MSE of 1.2 min across a whole route. — [Search summary](https://www.researchgate.net/publication/306527837_Online_bus_arrival_time_prediction_using_hybrid_neural_network_and_Kalman_filter_techniques)

**Deep learning / GNN (road ETA, Google)**
- DeepMind and Google Maps GNN ETA (arXiv 2108.11482, CIKM 2021): road segments are graph nodes ("supersegments"). It reduced negative ETA outcomes by more than 40% in cities such as Sydney compared with the previous production baseline. The blog reports up to 51% in Taichung, 43% in Sydney and 37% in Osaka. This is car ETA, which feeds BusTr-style bus estimates. — [arXiv 2108.11482](https://arxiv.org/pdf/2108.11482); [DeepMind blog](https://deepmind.google/discover/blog/traffic-prediction-with-advanced-graph-neural-networks/)

**Probabilistic / reliability**
- Montréal, 41k trips on 50 routes: predicting the conditional travel-time distribution, kNN + kernel density estimation gave the best estimate of the p.d.f. Most probabilistic models beat a Random Forest baseline. — [arXiv 2102.02292](https://arxiv.org/abs/2102.02292)
- Gainesville GTFS/GTFS-RT 2023: a hybrid Markov model with heteroscedastic link-time distributions (MLE, 95% bounds from Fisher information) outperformed historical mean, statistical and AI baselines with narrower bounds. The abstract gives no numbers. — [arXiv 2503.05907](https://arxiv.org/abs/2503.05907)
- Stockholm high-frequency buses: Bayesian models with Student-t errors beat Gaussian ones on log predictive density for stop delays. They use Gaussian processes on date and time for long-run effects. — [arXiv 2106.13576](https://arxiv.org/abs/2106.13576)
- Chennai: travel times per 500 m section fit log-normal (KS tests), and log-domain modelling improved accuracy. — [arXiv 1904.03444](https://arxiv.org/pdf/1904.03444)

### Inferences
- For a schedule-free journey planner (which is not real-time ETA from the current bus position), the realistic target is a historical profile by segment × day type × time bin. In the Copenhagen data this matched Google Traffic's journey MAPE (6.5% vs 6.3%). ML or deep models mainly help when they ingest same-day real-time state. Planning a trip hours ahead gets most of the achievable accuracy from a well-built historical profile.
- BusTr's 35.6% MAPE for "car ETA as bus ETA" implies that a Google Maps driving time is a weak benchmark for bus in-vehicle time. Google Maps transit mode in Delhi, however, uses BusTr-like modelling (launched in India first). A team should compare against Google's transit ETA, not its driving ETA.
- Expected gains from GBDT over a good historical median are typically 10–25% relative MAE in these papers. That makes a LightGBM residual model a plausible "stretch" component, not the core.
- Use median, or the mean in the log domain, rather than the arithmetic mean, because travel times are log-normal and right-skewed.

### Gaps
- Exact MAPE values for the Chennai log-normal AR paper and its baselines are in figures that could not be extracted.
- No study found that compares a historical median against XGBoost on the same Indian dataset with MAE in seconds.
- No Delhi-specific (DTC/DIMTS) published travel-time accuracy study was found.
- There is no published accuracy for Swiftly or the Transit app; nothing was found in the searches.

---

## Q2. What GPS sampling interval and preprocessing are needed, and how do studies handle noisy, irregular, off-road and delayed pings?

### Takeaway
Typical inputs are 5–30 s AVL pings. Off-the-shelf HMM map matchers work well below about 30 s intervals. Standard steps are: trip and direction segmentation, linear referencing onto the route shape, segment cutting at stops or fixed lengths (around 500 m), speed bounds for outliers, gap filters, and geofence-based stop arrival and departure (around 20 m buffer). Google deliberately does not interpolate between pings. It drops samples with large gaps or implausible speeds.

### Cited Findings
- Chennai (IITM) pipeline, 5 s GPS: trip identification (multiple daily trips; separating onward and return), lat/lon to distance via Haversine, 500 m sections (equal to the mean inter-stop distance). Outliers are clipped to a 30 s lower bound (60 km/h free flow) and to the 95th-percentile upper bound per section. — [arXiv 1904.03444](https://arxiv.org/pdf/1904.03444)
- Google BusTr filtering:
  - Samples ("shingles") are 1–5 km. Starts are spaced at least 30 s apart to reduce redundancy from dense trajectories.
  - Any shingle with a gap between consecutive reports above 5 min or 3 km is dropped.
  - Shingles with average speed outside 0.7–140 km/h are excluded.
  - BusTr intentionally does not resample or interpolate between pings, because bus motion between two reports is non-uniform (stops, red lights, local jams).
  - It cites a "typical 30-second reporting interval".
  - [arXiv 2007.00882](https://arxiv.org/pdf/2007.00882)
- GTFS-RT stop events, Gainesville: arrival is the first ping inside a 20 m buffer around the stop, departure is the exit ping, and dwell is departure minus arrival. Link travel times combine GTFS static, GTFS-RT and OSM road segments. — [arXiv 2503.05907](https://arxiv.org/pdf/2503.05907)
- Anita Graser's analysis of GTFS-RT: updates are sparse and irregular, so you may not "see" every stop. You cannot rely on stop detection alone because buses sometimes do not halt at stops. Her approach splits trajectories at changes of stop ID, using the Trajectools library. — [anitagraser.com 2025](https://anitagraser.com/2025/03/10/analyzing-gtfs-realtime-data-for-public-transport-insights/)
- GTFS-RT spec caveats: `speed` is a momentary measurement in m/s. `current_status` (INCOMING_AT, STOPPED_AT, IN_TRANSIT_TO) depends on what the vehicle reports. Do not trust it blindly. — [GTFS-RT reference](https://gtfs.org/documentation/realtime/reference/)
- Map matching performs well when the GPS interval is under 30 s. Methods are sensitive to GPS error, sampling rate and initialisation. Ground truth for evaluating matching is usually unknown. — [Springer SN CS 2022](https://link.springer.com/article/10.1007/s42979-022-01340-5); [FMM paper](https://people.kth.se/%7Ecyang/bib/fmm.pdf)
- The Copenhagen ConvLSTM study used 15-minute aggregation bins, chosen against headway (7.5 min). Finer bins sharply increase the missing-value ratio. — [arXiv 1903.02791](https://arxiv.org/pdf/1903.02791)
- Patent-level practice (China) removes points with excessive error and depot entry/exit points before prediction. — [CN102157075A](https://patents.google.com/patent/CN102157075A/en)

### Inferences
- For a bus that follows a known GTFS shape, full road-network map matching is usually unnecessary. Projecting each ping onto the route shape polyline (linear referencing) gives distance along route. Reject pings that are more than about 50–100 m off the shape, or that move backwards. Monotonic distance along route then gives segment entry times by linear interpolation in time–distance space at stop or segment boundaries. This interpolation is a deliberate simplification that BusTr avoids. For 10–30 s pings it is generally acceptable for segments of 500 m or more.
- Delayed or out-of-order pings: sort by device timestamp, deduplicate, and drop non-monotonic distance-along-route jumps.

### Gaps
- No published quantitative benchmark was found comparing FMM, Valhalla Meili and OSRM on sparse (over 30 s) bus traces.
- The Delhi feed's actual ping interval and latency need to be measured from the hackathon data. No published Delhi figure was found.

---

## Q3. How do studies handle sparse segments and time bins (fallbacks, hierarchical pooling, shrinkage)?

### Takeaway
Explicit literature on shrinkage is thin in the bus-ETA papers reviewed. Practical patterns are coarser time bins chosen against headway (Copenhagen's 15-minute bins had about 1.7 observations each), multi-level spatial embeddings that fall back to coarser cells (BusTr), and cross-route pooling on shared road segments.

### Cited Findings
- BusTr uses hierarchical spatial context: S2 cells at several levels (fine level 15 up to metro and country) plus route-ID embeddings. Removing coarse cells hurt new-area generalisation (19.6% to 23.6% MAPE), showing that coarse-level pooling acts as a fallback for unseen places. — [arXiv 2007.00882](https://arxiv.org/pdf/2007.00882)
- BusTr: with route ID ablated, MAPE rises only from 13.2% to 13.6%. Most routes sharing a road behave alike, apart from bus lanes and express vs local services. This supports pooling observations across routes on shared segments. — [arXiv 2007.00882](https://arxiv.org/pdf/2007.00882)
- Copenhagen: the time-bin choice trades training time against missing-value ratio (Fig. 8). Normalisation uses the per-link mean for each day of week and time of day computed only on the training set. — [arXiv 1903.02791](https://arxiv.org/pdf/1903.02791)
- TheTransitClock combines past weeks, days and hours of data in its Kalman filter, a form of temporal pooling. — [Springer NETS 2023](https://link.springer.com/article/10.1007/s11067-021-09541-w)

### Inferences
- A practical fallback hierarchy for the hackathon:
  1. segment × day type (weekday, Saturday, Sunday or holiday) × 30-minute bin;
  2. segment × day type × 1–2 h period (AM peak, midday, PM peak, evening, night);
  3. segment × all days × period;
  4. corridor or road-class speed by period (pooled across routes);
  5. GTFS schedule or free-flow speed.
- Require a minimum count (for example n ≥ 5–10 traversals) before trusting a level. Otherwise use empirical-Bayes shrinkage of the log travel time: `(n·x̄ + k·parent)/(n + k)`.
- Pool across all routes that traverse the same stop-to-stop pair or road segment.

### Gaps
- No bus-specific paper was found that quantifies the accuracy gain from hierarchical or empirical-Bayes pooling against a naive cell mean.

---

## Q4. What open-source tools exist?

### Takeaway
TheTransitClock (Java, GPL-3.0) is the only mature open-source end-to-end engine (GTFS + AVL/GTFS-RT to predictions using historical averages or a Kalman filter). For an analytics pipeline, tsdataclinic/gtfs-realtime-performance gives stop-to-stop segment speeds from archived GTFS-RT. FMM, Valhalla/Meili and OSRM `/match` are the standard HMM map matchers.

### Cited Findings
- **TheTransitClock/transitime**: real-time transit information system from "any type of real-time GPS data". It reads GTFS, has core, REST API and web modules, and is GPL-3.0, forked from Transitime/core (3,121 commits, 87 stars). Its Kalman module and the comparison against historical average are documented in its wiki. — [GitHub](https://github.com/TheTransitClock/transitime); [Kalman testing wiki](https://github.com/TheTransitClock/transitime/wiki/Prediction-Kalman-testing)
- **tsdataclinic/gtfs-realtime-performance**: segments GTFS shapes into consecutive stop pairs and computes trip-level speeds per segment from archived GTFS-RT. It is designed to pair with the **gtfs-realtime-capsule** archiver. — [GitHub](https://github.com/tsdataclinic/gtfs-realtime-performance)
- **Trajectools / MovingPandas** (Anita Graser): trajectory splitting and analysis of GTFS-RT positions. — [anitagraser.com](https://anitagraser.com/2025/03/10/analyzing-gtfs-realtime-data-for-public-transport-insights/)
- **FMM (Fast Map Matching)**: HMM with precomputation (UBODT), focused on speed. — [Yang & Gidófalvi, IJGIS 2018](https://people.kth.se/%7Ecyang/bib/fmm.pdf)
- **Valhalla Meili**: Valhalla's map-matching module, evaluated as an adequate open-source alternative to commercial services. — [TDS: Map matching with Meili](https://towardsdatascience.com/map-matching-done-right-using-valhallas-meili-f635ebd17053/); [Springer 2022](https://link.springer.com/article/10.1007/s42979-022-01340-5)
- **Copenhagen ConvLSTM**: code and trained models are on GitHub, per the paper. — [arXiv 1903.02791](https://arxiv.org/pdf/1903.02791)
- **gtfs.zone**: GTFS and GTFS-RT visualiser and management tool. It is not for speed inference. — [gtfs.zone](https://gtfs.zone/)

### Inferences: practical 10-day build plan
1. **Days 1–2, ingest and clean.** Load GTFS and the GPS/GTFS-RT archive.
   - Sort pings by vehicle and timestamp, deduplicate, and drop stale or delayed pings (receive time much later than the device time).
   - Match pings to trip and direction, then project onto the GTFS shape (for example, shapely `project`).
   - Drop pings more than about 75 m off the shape, backward jumps, and segment speeds outside about 1–80 km/h (city bus).
   - Use a gap filter of more than 3–5 min or more than 3 km, as in BusTr.
2. **Days 2–3, stop events.** Get stop-arrival times by time–distance interpolation at each stop's shape distance, or with a 20 m geofence when pings are dense. The result is stop-to-stop link times per traversal.
3. **Days 3–4, baseline profile.** Compute the median (or log-mean) link time per stop-pair × day type × 30-minute bin. Use the hierarchical fallback with shrinkage from Q3. Keep p50, p85 and p95 for reliability or buffer times.
4. **Days 4–6, routing.** Feed time-dependent link times into RAPTOR or CSA, or a time-dependent graph. In-vehicle time is the sum of the link medians, looked up by the bin at which the bus reaches each link (time propagation).
5. **Days 6–8, evaluation.** Hold out the last week. Report MAE (seconds), MAPE and P(|error| < 2 min) at journey level against observed trips and against Google transit times. Optional: a LightGBM residual model (features: hour, day of week, segment length, stops, previous-segment delay) if time allows.
6. Expect a well-built historical profile to land in the same ballpark as Google Maps on journey-level MAPE, consistent with the Copenhagen result. Deep models are not needed to be competitive.

### Gaps
- Swiftly and Transit app methodology and accuracy blogs were not retrieved.
- An OSRM `/match` documentation or benchmark on bus data was not retrieved.
- The maintenance status of TheTransitClock in 2025–26 was not verified beyond the repository statistics.
