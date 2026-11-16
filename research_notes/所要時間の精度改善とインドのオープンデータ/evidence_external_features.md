# Evidence on external data sources for bus travel-time / ETA / waiting-time prediction (India focus)

Compiled 2026-11-17. Labels: **[V]** = verified this session (read the abstract, full text or search-returned text); **[S]** = only seen in a search snippet or summary, figures not checked against the paper; **[P]** = from prior knowledge, not re-checked this session (treat as a lead). About 18 tool calls; several publisher pages (ScienceDirect, IIIT-D repository) refused or reset the fetch.

Team baseline for context: in-vehicle median abs error 10% (LightGBM with time of day, day type and recent preceding-bus speeds), waiting 33%, door-to-door 23.5%, multi-leg 35.5%.

## Q1. Indian studies: which features, which gains?

### Takeaway
Indian work (mostly IIT Madras on Chennai MTC) gets its accuracy from **recent same-segment travel times of preceding buses** plus time discretization. None of the studies found tests weather, map-API speeds or OSM features with an ablation. Delhi research on OTD GTFS-RT is descriptive (variability, schedule adherence) or uses deep spatio-temporal models. No Indian paper found isolates the gain from an external data source.

### Cited Findings
- **Chennai, IIT Madras (Vanajakshi group).** Model-based Kalman filter with space discretization, followed by a pattern-based *time*-discretized method that reported "a clear improvement" over space discretization. Inputs are travel times of preceding buses on the same segment, e.g. "the previous four significant trips' travel time on the same segment". Test route was MTC 19B (25 stops, 14 signalized intersections). **[S]** — [Pattern-Based Bus Travel Time Prediction under Heterogeneous Traffic](https://www.researchgate.net/publication/259483762_Pattern-Based_Bus_Travel_Time_Prediction_under_HeterogeneousTraffic_Conditions); [Pattern-Based Time-Discretized Method](https://www.researchgate.net/publication/313739795_Pattern-Based_Time-Discretized_Method_for_Bus_Travel_Time_Prediction); [Vanajakshi et al., GPS data from buses](https://www.semanticscholar.org/paper/Travel-time-prediction-under-heterogeneous-traffic-Vanajakshi-Subramanian/e370ba212ed96d71e7272942d20712aea08bd781)
- **IIT Madras CoEUT APTS final report (2016).** Prediction accuracy is reported as "in the range of 1–2 minutes"; the snippet does not say which model this refers to. **[S]** — [APTS Final Report 2016](https://coeut.iitm.ac.in/APTS_Finalreport_2016.pdf)
- **IIT Madras SVR work.** ν-SVR with a linear kernel for "high variance conditions". A MAPE of 18.72% appears for a model that "captured travel time better than KFT" (Kalman filter); which model it belongs to is unclear. **[S]** — [SVM for high variance conditions (Transport, VilniusTech)](https://journals.vilniustech.lt/index.php/Transport/article/download/15220/10653)
- **Lognormal AR model (Achar et al., arXiv 2019).** Uses 34 days of 5-second GPS on MTC route 19B (about 30 km) in Chennai, with only the bus's own spatio-temporal history and no external data. **[S]** — [arXiv 1904.03444](https://arxiv.org/pdf/1904.03444)
- **Physics-informed ML (PINN / PI-LSTM vs ANN, LSTM, Godunov scheme).** Uses 34 days of GPS from heterogeneous Indian traffic. Goal: the "peak prediction problem". Figures not seen. **[S]** — [Adaptive physics-informed ML for bus travel time (Applied Soft Computing, 2026)](https://www.sciencedirect.com/science/article/pii/S1568494626008835)
- **Real-time system under Indian traffic (Dhivyabharathi et al.).** **[S]** — [Semantic Scholar](https://www.semanticscholar.org/paper/Real-time-bus-arrival-time-prediction-system-under-Dhivyabharathi-Kumar/c6adc08ef38581be2ecbe037886c77e77fcdf9fe)
- **Mysore (KSRTC MITRA ITS GPS).** Routes 94 and 260; compares ARIMA, SVM, LSTM and ANN. No external features are mentioned. **[S]** — [Prediction Models for Bus Travel Time Using GPS Data (Springer, 2025)](https://link.springer.com/chapter/10.1007/978-981-96-8444-1_10). The MITRA system shows next-bus ETAs at stops and over SMS/IVR **[S]** — [MITRA overview](http://mitra.ksrtc.in/MysoreMBus/index_e.jsp). An IISc-affiliated RTPI prototype (arXiv 2012) **[S]** — [arXiv 1206.0447](https://arxiv.org/pdf/1206.0447)
- **Delhi, IIIT-Delhi M.Tech thesis (Karan Dhingra, MT19025).** Converts a day of GTFS(-RT) into a tensor and uses an RNN + graph-convolution encoder with GRU-D to impute missing data. Argues that underestimating ETA hurts riders more than overestimating. Metrics not retrieved because the repository fetch failed. **[S]** — [IIIT-D repository](https://repository.iiitd.edu.in/xmlui/handle/123456789/1094); [PDF](https://repository.iiitd.edu.in/jspui/bitstream/handle/123456789/1094/Karan%20Dhingra%20MT19025.pdf?sequence=1&isAllowed=y)
- **Delhi, COMSNETS 2024 (Santhosh Kumar B V, Fedujwar, Agarwal).** "Travel Time Variability of Bus Routes in Delhi Using Real-Time GTFS Data". One month of GTFS-RT; TTV is highest on Thursday and lowest on Monday. Day of week and time of day are significant. Descriptive, no prediction gain. **[S]** — [dblp](https://dblp1.uni-trier.de/rec/conf/comsnets/VFA24.html); [Bohrium summary](https://www.bohrium.com/paper-details/travel-time-variability-of-bus-routes-in-delhi-using-real-time-gtfs-data/1172774695414530048-2000000)
- **Delhi, schedule adherence with OTD (Tarar, Mukherjee, Rao 2021).** Measures how accurate Delhi's static schedule is. **[S]** — [Sci. J. Silesian Univ. Technol. 111 (2021)](https://sjsutst.polsl.pl/archives/2021/vol111/169_SJSUTST111_2021_Tarar_Mukherjee_Rao.htm)
- **Delhi DTC route 832 ANN (about 2016).** Evaluated with MAE/RMSE on manual/GPS data. **[S]** — [Prediction of Bus Travel Time Using ANN: A Case Study in Delhi (Transp. Res. Procedia)](https://www.sciencedirect.com/science/article/pii/S2352146516307062)
- **Delhi OTD feed.** Publishes VehiclePositions about every 10 s and **no TripUpdates**, per a GitHub project dated July 2026, so any ETA has to be built from positions. **[S]** — [Swarajya report](https://swarajyamag.com/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus); [DTC-Tracker](https://github.com/saranshgemini18-del/DTC-Tracker)
- **Indian rainfall evidence (not ML ablations).** Mumbai field study (WCTR 2019): travel time **+10–130%** under rain depending on intensity and road **[S]** — [WCTR2019 Mumbai 526](https://www.wctrs-society.com/wp-content/uploads/abstracts/mumbai/WCTR2019_Mumbai_526.pdf). BMTC passengers in extreme rain report waiting time **+45%** (survey) **[S]** — [NITK](https://idr.nitk.ac.in/items/9a06c145-8b89-4bc6-8c2a-8074ac6a48cb/full). Bengaluru office commutes up to +62% in August rain (industry, not peer-reviewed) **[S]** — [The News Minute](https://www.thenewsminute.com/article/bengaluru-rains-pushed-average-commute-time-62-august-167433)
- **[P]** Achar, Bharathi, Kumar, Vanajakshi, "Bus Arrival Time Prediction: A Spatial Kalman Filter Approach", IEEE T-ITS (~2020). Also Kumar, Vanajakshi, Subramanian, "Bus travel time prediction using a time-space discretization approach", Transportation Research Part C (2017). In both, inputs are the bus's own and preceding buses' segment times. Not re-verified here.

### Inferences
- The team's feature set (time of day, day type, preceding-bus speeds) is already the "Indian best practice" core. Indian literature gives no evidence that weather, OSM or events add measurable accuracy on top of it.
- Monsoon rain (Delhi: July–September) is the one external factor with large documented effects in India (+10–130% travel time in Mumbai). A November Delhi evaluation window will contain almost no rain, so a weather feature would likely show ~0 gain there. Expect the gain to show up only in a monsoon test set.
- Delhi winter smog/fog days (GRAP restrictions, low visibility) are a plausible Delhi-specific "event" feature. No study found tests it.

### Gaps
- None of the requested "Kapoor/Rathore" Delhi papers on OTD GTFS-RT were found; they may not exist under those names.
- No Hyderabad (TSRTC) or Pune (PMPML) bus ETA paper with external-feature ablations was found.
- Exact MAPE values for the IIT Madras methods and the IIIT-D thesis are not verified (fetch failures).

## Q2. International: weather, map-API traffic speeds, OSM features, events

### Takeaway
**Live road-traffic speeds** are the only external source with a clean, large, verified ablation: −14% relative MAPE in Google BusTr. That gain is in a setting *without* live bus positions, so it overlaps heavily with the team's preceding-bus-speed feature. **Weather** results are mixed: often "minimal" when recent bus speeds are present, and "unsuccessfully tried" in Warsaw. **OSM** features help mostly for transfer to new routes or networks (up to −10% MAPE), not much for in-network prediction. **Events/holidays** are usually folded into day type.

### Cited Findings
- **BusTr (Google, KDD 2020; Barbour et al.).** Inputs are Google Maps real-time road-traffic forecasts, route ID, S2 spatial cells and time of week, trained on GTFS-RT VehiclePositions (multi-city; partner agencies). **[V]** — [arXiv 2007.00882](https://arxiv.org/abs/2007.00882) (full PDF read)
  - Full model test MAPE **13.24%**. **Removing road traffic raises it to 15.44% (+16% relative)**. Removing time of week: 13.87% (+5%). Removing route ID: 13.60% (+3%). Removing all spatial cells and route ID: 22.19% (+69%). **[V]**
  - Baselines: car traffic ETA alone used as bus ETA gives MAPE **35.6%**. Linear regression on stops + distance + car-traffic time gives **22.9%**. DeepTTE: 31.5% (21.2% if non-converged runs are excluded). **[V]**
  - Important caveat: BusTr targets bus lines **without** real-time bus feeds and predicts from endpoint pairs, not from live preceding buses. **[V]**
- **Weather, Trondheim (Norway) RNN.** A leave-one-feature-out ablation found that including weather improved accuracy. The paper cites another LSTM work that reported a 48% gain from weather (figure unverified and probably dataset-specific). **[S]** — [Predicting Irregularities in Arrival Times… GPS and Weather Data](https://www.researchgate.net/publication/343917790_Predicting_Irregularities_in_Arrival_Times_for_Transit_Buses_with_Recurrent_Neural_Networks_Using_GPS_Coordinates_and_Weather_Data)
- **Weather, Changsha SVM/AVL.** Variable importance put instantaneous speed and recent travel history first; **weather had minimal short-term impact**. **[S]** — [SVM high variance conditions](https://www.researchgate.net/publication/354033459_BUS_TRAVEL_TIME_PREDICTION_USING_SUPPORT_VECTOR_MACHINES_FOR_HIGH_VARIANCE_CONDITIONS)
- **Weather and events, Warsaw.** "games or weather have been (unsuccessfully) tried". **[S]** — [arXiv 2204.04515](https://arxiv.org/pdf/2204.04515)
- **GCN with attention (MDPI Applied Sciences 2026).** Ablation says weather, time of day and holiday features "improve adaptability". No figure seen. **[S]** — [MDPI](https://www.mdpi.com/2076-3417/16/17/8764)
- **Weather on AVL journey times (French & O'Mahony, Dublin).** Rain, wind and temperature effects vary by season and route type. **[S]** — via [hrcak.srce.hr](https://hrcak.srce.hr/file/473496)
- **OSM generalization across 33 bus networks (2024).** Features built on schedule data, real-time positions or OSM embeddings improved transfer to new networks, with **up to 10% lower MAPE**. **[S]** (publisher fetch 403) — [Generalization strategies… (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S222658562400061X)
- **OSM features, Dublin.** Regression on large-scale OSM extraction: departure delay, **number of signalized intersections**, pedestrian-crossing phases and stop spacing explain bus delay (explanatory, not a predictive ablation). **[S]** — [ResearchGate](https://www.researchgate.net/publication/364579712_A_LARGE_SCALE_METHOD_FOR_EXTRACTING_GEOGRAPHICAL_FEATURES_ON_BUS_ROUTES_FROM_OPENSTREETMAP_AND_ASSESSMENT_OF_THEIR_IMPACT_ON_BUS_SPEED_AND_RELIABILITY)
- **Hybrid Markov model (Gainesville, 2025).** Splits link time into road, dwell and intersection components (intersections from OSM in the full text, per snippet). Beats historical mean, statistical and AI baselines, with no figures in the abstract. **[V abstract]** — [arXiv 2503.05907](https://arxiv.org/abs/2503.05907)
- **Montréal STM (2026).** 1,683 spatio-temporal features compressed with PCA. A global LSTM with cluster-aware features beats transformers by 18–52%. The abstract does not mention weather, OSM or events. **[V abstract]** — [arXiv 2601.18521](https://arxiv.org/abs/2601.18521)
- **Literature in the BusTr review:** an RBF model using intersection counts (with/without lights) reached MAPE 9% vs MLP 34%. A model using traffic flow cut prediction errors by 25% on average and 15-minute errors by 47% (source papers not identified). **[V, as cited inside BusTr]** — [arXiv 2007.00882](https://arxiv.org/abs/2007.00882)

### Inferences
- **Map-API speeds** (Google Routes/Distance Matrix with traffic, TomTom, HERE) are most valuable where preceding-bus data is stale or missing: long headways, first trip of the day, sparse routes, or segments no bus has crossed in the last N minutes. On dense Delhi corridors, recent preceding-bus speeds already capture "today's traffic". The marginal gain is likely well below BusTr's 14% and could be near zero for in-vehicle error. Cost and rate limits matter: segment-level polling across Delhi is expensive, and ToS usually forbid storing results for training.
- **Cheap substitute:** fleet-wide GPS from all ~6,000+ Delhi buses as a "traffic layer" (speeds of *any* route on the same road segment in the last 10–15 min). This is the same signal as BusTr but free, and fills gaps on low-frequency routes.
- **OSM static features** (signals, junction count, stop spacing, road class) mainly help cold-start or unseen segments. Expect small gains for routes already in training data.
- **Weather:** likely ≈0 on a November Delhi test set. Worth a single binary/rain-mm feature (IMD or Open-Meteo, hourly) only if the evaluation covers monsoon days.
- **Holidays/events** (Diwali, Chhath, gazetted holidays, Republic Day rehearsals in January, cricket matches, VIP movements): add as day-type flags. These are low effort, but no quantified gain was found for bus ETA.

### Gaps
- No study found tests map-API traffic speeds *on top of* preceding-bus speeds (the team's exact situation).
- No verified per-feature MAE/MAPE numbers for weather besides qualitative claims.

## Q3. Waiting time: headway-based prediction, bunching, cancellations and ghost buses

### Takeaway
For high-frequency, irregular service, waiting-time error is dominated by **whether the next bus actually exists and when it is truly coming**, not by link-speed accuracy. Evidence: real-time predictions roughly halve wait-estimate error vs the timetable in Stockholm, but one US study found real-time strategies no better than following the schedule when prediction error causes missed buses. Ghost-bus handling is largely an industry/data-quality practice with few quantified academic results.

### Cited Findings
- **Stockholm empirical evaluation (Cats & Loutos).** Real-time arrival information was about **2× closer to actual waiting time than the timetable**. The scheme **underestimated remaining wait by ~6.2%** on average. Headway irregularity made actual waits **57% longer** than with perfectly regular service. **[S]** — [Real-Time Bus Arrival Information System – An Empirical Evaluation](https://www.researchgate.net/publication/262684379_Real-Time_Bus_Arrival_Information_System_-_An_Empirical_Evaluation); [KTH thesis](https://www.diva-portal.org/smash/get/diva2:732548/FULLTEXT01.pdf)
- **"Does real-time transit information reduce waiting time?" (TR-A 2021, mid-size US city).** The best real-time strategy performs **about the same as following the schedule**. Prediction errors can cause missed buses costing up to a full headway. Effects vary by time of day, distance to stop and stop location. **[S]** — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0965856420307229)
- **Review of waiting time and headway modelling (Ingvardson et al., Transport Reviews 2020).** Critical review and proposed approach. **[S]** — [T&F](https://www.tandfonline.com/doi/full/10.1080/01441647.2020.1806942). Unreliability modeling: without perfect real-time headway information, passengers wait longer **[S]** — [TR-A 2021](https://www.sciencedirect.com/science/article/pii/S0965856421003001)
- **Headway-based bunching prediction.** LS-SVM on smart-card data detects **>95% of bunching events**, with little decay over lead time **[S]** — [TR-C 2016](https://www.sciencedirect.com/science/article/abs/pii/S0968090X16301747). An LSTM with attention on headways beats arrival-time-based methods, especially for multi-stop horizons **[S]** — [ResearchGate](https://www.researchgate.net/publication/385479309_Headway-Based_Bus_Bunching_Prediction_Using_LSTM_with_Attention). An LSTM ETA on sparse MTA SIRI polling reports a **28.5% improvement over its baseline** (baseline/metric unverified) **[S]** — [Frontiers Built Env. 2026](https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2026.1894212/full)
- **Bunching and waiting time.** Theoretical/simulation argument on whether bunching can reduce waits. **[S]** — [arXiv 2201.02343](https://arxiv.org/pdf/2201.02343)
- **Ghost buses / cancellations (industry).**
  - The Swiftly "ETA Completeness" benchmark (June 2026) classifies trips, including ghost trips (did not run / no info). **[S]** — [Swiftly](https://www.goswift.ly/blog/eta-completeness-benchmark)
  - Cal-ITP publishes monthly per-agency shares of scheduled trips with no real-time prediction. **[S]** — via the same search
  - RTIG (UK) lists causes such as physical cancellation not mirrored electronically, and breakdowns. **[S]** — [RTIG T054 Ghost Buses](https://www.rtig.org.uk/system/files/documents/RTIGT054-1.0%20Ghost%20Buses.pdf); [RTIG T041 accuracy](https://www.rtig.org.uk/system/files/documents/RTIGT041-1.0%20Accuracy%20and%20Quality%20of%20Real%20Time%20Predictions.pdf)
  - SEPTA found its ghost-bus issue was largely a data pipeline / cancellation-entry problem. **[S]** — [Billy Penn 2024](https://billypenn.com/2024/11/05/septa-ghost-bus-cancel-fix-app/)
  - OneBusAway does not yet show cancellation indications. **[S]** — [OTSF data errors](https://opentransitsoftwarefoundation.org/onebusaway/documentation/data-errors)
- **[P]** OneBusAway Seattle studies (Watkins et al. 2011, TR-A): RTI users perceived waits about 30% shorter, and measured waits were about 2 min shorter for app users. Brakewood et al. (Tampa, NYC) found similar results. Not re-verified.

### Inferences (method recommendations for the 33% waiting error)
1. **Predict waiting time from the actual approaching vehicles, not the schedule.** For each stop, take the set of buses currently upstream on the route (from VehiclePositions) and predict each one's ETA with the 10%-error in-vehicle model. Waiting time = min over those ETAs after the passenger's arrival time. Fall back to schedule-based headway only beyond the visible horizon (e.g. >30–45 min).
2. **Ghost and missing-trip handling with VehiclePositions only (Delhi has no TripUpdates):**
   - Mark a scheduled trip as *likely cancelled* if no vehicle is block-matched to it within X min of scheduled departure.
   - Mark a vehicle as *stale* if no ping has arrived for more than about 2–3 min or it shows zero progress for more than N min away from a terminal. Exclude it from candidate ETAs, or down-weight it with a survival probability.
   - Learn an empirical "trip actually operates" probability by route × hour from history (Delhi missing-trip rates are high). Use it to inflate schedule-fallback headways: effective headway ≈ scheduled headway / P(operate).
3. **Bunching:** predict the *headway* (gap to leader) rather than absolute arrival times. Headway-based ML detects >95% of bunching in the literature. When the leader is close, the follower's ETA is strongly correlated with it, so model the pair.
4. **Report distributions.** Give P50/P80 of waiting time. Underestimation is costlier (Stockholm −6.2% bias; IIIT-D thesis argument), so consider a quantile/asymmetric loss.
5. **Evaluate against realized waits** from replayed GPS (first actual arrival after a random passenger arrival time), stratified by headway-regularity regime.
- None of these specific gains are measured for Delhi. Expected gains are inferences.

### Gaps
- No peer-reviewed quantitative study found on GPS-only trip-cancellation detection accuracy.
- No Indian study quantifying waiting-time prediction error vs schedule.

## Q4. Open benchmark datasets of Indian bus GPS

### Takeaway
There is no standard, public Indian bus-GPS ETA benchmark. The most usable source is **Delhi OTD** (live VehiclePositions about every 10 s plus static GTFS, registration required), which teams archive themselves. Chennai and Bengaluru have only unofficial, scraped data.

### Cited Findings
- **Delhi OTD** (IIIT-Delhi + DIMTS / Delhi Transport Dept.): stops, routes, timetables, and real-time GPS about every 10 s in GTFS/GTFS-RT. No TripUpdates. **[S]** — [Swarajya](https://swarajyamag.com/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus); portal otd.delhi.gov.in
- **"how-Delhi-buses-move"**: 6 hours of live GPS from 6,000+ Delhi buses, with bunching analysis and an arrival-time model (GitHub, not peer-reviewed). **[S]** — [GitHub](https://github.com/rishabhjain9196/how-Delhi-buses-move)
- **Transport Stack Hackathon 2026 repo** (IIIT-Delhi / JICA): historical and real-time GTFS-RT to travel-time predictions. **[S]** — [GitHub](https://github.com/Aryanban/transport-stack-hackathon-2026)
- **Chennai:** reclaimchennai/mtc-bus-map provides live MTC positions and observed road speeds from consecutive GPS fixes (ODbL; the upstream source is MTC's app, so check its terms) **[S]** — [GitHub](https://github.com/reclaimchennai/mtc-bus-map/blob/main/README.md). The IIT Madras 19B data (34 days, 5 s) is described in papers, and public release was not confirmed **[S]** — [arXiv 1904.03444](https://arxiv.org/pdf/1904.03444)
- **Bengaluru:** unofficial BMTC GTFS scraped from the Namma BMTC app, whose creator warns the timetables are inaccurate **[S]** — [Vonter/bmtc-gtfs](https://github.com/Vonter/bmtc-gtfs). Static stops and timings on OpenCity **[S]** — [data.opencity.in](https://data.opencity.in/dataset/bengaluru-public-transport-infrastructure). A Kaggle BMTC dataset is schedule-only **[S]** — [Kaggle](https://www.kaggle.com/datasets/shivamishra2112/bmtc-bus-transportation-dataset)
- **Non-Indian reference:** UK BODS national GTFS-RT with the open rt2gtfs tool (2026) to build observed timetables. **[V abstract]** — [arXiv 2603.11477](https://arxiv.org/abs/2603.11477)

### Inferences
- For credibility, the team can publish its own archived OTD slice with a fixed train/test split as a mini-benchmark. Nothing equivalent appears to exist.

### Gaps
- Whether IIT Madras or IIIT-D have released their GPS datasets publicly is unconfirmed.

## Priority summary (inference, for the team)
| Data source | Evidence strength | Expected gain for this team | Effort |
|---|---|---|---|
| Fleet-wide bus GPS as a traffic layer (other routes on the same segment, last 10–15 min) | Strong by analogy (BusTr −14% from live traffic) | Medium on low-frequency routes; small on dense ones | Low (data in hand) |
| Ghost/cancelled-trip detection + approaching-vehicle waiting model | Moderate (Stockholm ~2× better than timetable; one US null result) | **Largest lever for the 33% waiting and 35.5% multi-leg error** | Medium |
| Holiday/event/day-type flags (incl. Delhi festivals, GRAP/smog days) | Weak (qualitative) | Small; tail days only | Low |
| Map-API live speeds (Google/TomTom) | Strong in BusTr, but without bus feeds | Small on top of preceding-bus speeds; cost/ToS issues | Medium-high |
| OSM signals/junctions/stop spacing | Moderate for transfer (≤10% MAPE) | Small in-network; helps unseen segments | Low-medium |
| Weather (rain) | Mixed internationally; large raw effect in Indian monsoon | ≈0 in a November test; possibly meaningful in monsoon | Low |
| Metro data (DMRC) | None found | Unknown; possible for feeder demand/dwell | Medium |
| GTFS-RT TripUpdates | Not available in Delhi OTD | n/a (must self-generate) | — |
