# Improving bus in-vehicle travel-time prediction beyond a strong historical + real-time GBDT baseline (Delhi DTC context)

Evidence tags used below: **[FT]** = full text / full HTML read in this session; **[AB]** = abstract or metadata page only; **[SN]** = search-engine snippet or secondary summary, not checked against the paper (treat numbers as provisional). Comparability note: most papers report MAPE (mean of APE) or RMSE; our KPI is MedAPE (median APE), which is normally lower than MAPE for the same model, so literature levels are not directly comparable to our 10.4%. Our reference points: Baseline A 11.5% → Baseline B 10.8% → LightGBM (with real-time ratios) 10.4% (history-only LightGBM 12.0%). Bias: mean −2 to −3 min, median −0.5 min, on rides averaging 21 min.

## 1. Real-time + historical fusion (Kalman / time-decay smoothing, preceding-bus features, k-NN pattern matching, upstream-congestion propagation)

### Takeaway
Real-time information is consistently the largest gain after historical profiles. In BusTr, removing real-time traffic raised MAPE from 13.24% to 15.44% (+16%). That is close to the 13% relative gain we already get going from history-only LightGBM (12.0%) to the real-time version (10.4%). So further gains will come from *how* recent data is used, not from simply adding it:
- the previous bus's time on each downstream link, decayed by how old the observation is and how far ahead the link is;
- the state of neighbouring links, including congestion spreading upstream from downstream links;
- separate handling of rare congestion peaks.

On a Delhi route, a sequence model that used previous-bus times on upcoming sections beat Kalman-filter baselines. In Copenhagen, the agency's rule-based real-time adjustment scored worse than a plain historical average.

### Cited Findings
- **BusTr (Google, KDD 2020) [FT].**
  - Design: a trip's time is the sum of per-road-segment and per-stop units. Each segment unit is ReLU(α·d/s + β·d), where s is the road-traffic speed forecast for the time the bus is *expected to reach* that segment (extrapolated along earlier legs).
  - Results (test MAPE): BusTr 13.240%, car-traffic estimate alone 35.616%, linear regression 22.944%, DeepTTE 31.466%.
  - Ablations: no road traffic 15.443% (+16%); no time-of-week 13.865% (+5%); no route IDs 13.602% (+3%).
  - Source: [BusTr, ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882)
- Google Maps reportedly uses BusTr for most transit systems that lack official real-time feeds — [CatalyzeX summary](https://www.catalyzex.com/paper/arxiv:2007.00882) [SN]
- **Delhi route 399 (TCS Research) [FT].**
  - Data: Sep–Oct 2019, 34 uniform 800-m sections, Mon–Sat only (Sunday excluded); 7 weeks train, 1 week test.
  - Inputs: the encoder takes the current bus's times on sections it has already covered. The decoder takes the closest previous bus's times and entry times on each *upcoming* section, plus the closest same-weekday trip from the previous week as a seasonal input. All remaining sections are predicted together as one vector.
  - Results: the bidirectional model (EDB) is reported only as *best-case* MAPE improvements over each baseline. The paper calls these "improvements"; units are probably percentage points but not confirmed. Results appear only in figures, with significance via a Z-test at α=0.1.

    | EDB improvement vs. | 2 steps | 5 steps | 10 steps | 15 steps |
    |---|---|---|---|---|
    | Linear Kalman filter (LNKF) | 10.21 | 12.49 | 9.83 | 8.00 |
    | SVKF | 12.54 | 12.92 | 9.64 | 7.93 |
    | DpAR | 4.03 | 5.71 | 8.45 | 3.94 |
    | ConvLSTM (CLSTM) | 7.78 | 3.71 | 3.45 | 2.61 |
    | Unidirectional EDU | 8.93 | 8.61 | 7.08 | 6.59 |

  - The largest MAE improvement is 146.78 s, vs LNKF at 15 steps.
  - Source: [Bhutani, Pachal, Achar, arXiv 2210.01655v2](https://arxiv.org/html/2210.01655v2)
- **Same paper, reasoning (stated, not measured) [FT].**
  - The previous bus's relevance falls as the gap between its entry time and now grows.
  - Recursive Kalman-filter multi-step prediction is "prone to error accumulation".
  - The bidirectional decoder is meant to capture congestion spreading from downstream to upstream sections. The unidirectional version did poorly against some baselines.
  - Source: [arXiv 2210.01655v2](https://arxiv.org/html/2210.01655v2)
- The paper's introduction says Google Maps bus travel-time queries in Delhi mostly returned fixed predictions regardless of time of day — [arXiv 2210.01655v1](https://arxiv.org/pdf/2210.01655v1.pdf) [SN]
- **Copenhagen line 4A, ConvLSTM [FT].**
  - Data: Movia AVL, May–Oct 2017, about 1.2M link observations, 32 links, 15-min bins, 23 training weeks.
  - Evaluation is on the whole journey (sum of the 32 links), daytime MAPE:
    - historical average (HA) 6.51%;
    - Movia's deployed real-time model 8.05 / 6.82 / 8.68% (t+1 / t+2 / t+3), worse than the historical average it is built on;
    - pure LSTM 5.02 / 5.08 / 5.34%;
    - Google Traffic 6.32% (t+1 only);
    - ConvLSTM 4.19 / 4.44 / 4.75%.
  - MAE fell from 3.23 min (HA) to 1.99 min (ConvLSTM).
  - Peaks: morning (7–9h) MAPE 10.62% → 4.04%; afternoon (14–18h) 8.28% → 5.61% (Google Traffic 6.21%).
  - Source: [Petersen et al. 2019, ar5iv 1903.02791](https://ar5iv.labs.arxiv.org/html/1903.02791)
- **Copenhagen 300S express line [FT].** 39 links, 13 training weeks. RMSE at 15 / 30 / 45 min (values approximate; table extraction partly misaligned):
  - deep quantile ConvLSTM (DQR): 152.75 / 164.58 / 168.91 s;
  - linear Kalman filter: 156.92 / 177.47 / 182.70 s.
  - Source: [Petersen et al. 2021, ar5iv 2104.06819](https://ar5iv.labs.arxiv.org/html/2104.06819)
- **TransitClock Kalman filter at Metro Transit (Twin Cities).** A one-month test on the whole network found it "more accurate and stable", especially at hard-to-predict times and places. No numbers were accessible — [Crudden & Berrebi 2023, Networks and Spatial Economics (IDEAS listing)](https://ideas.repec.org/a/kap/netspa/v23y2023i2d10.1007_s11067-021-09541-w.html) [SN]
- **TransitClock Kalman test log [FT].** The filter uses the last vehicle on the same segment, which must match direction. The authors asked whether to ignore a previous vehicle older than, say, 1 h. Test configurations used 1–2 days of history for travel times and historical averages for dwell. No results are given — [TransitClock wiki](https://github.com/TheTransitClock/transitime/wiki/Prediction-Kalman-testing)
- **IIT Madras (Chennai).**
  - Exponential smoothing combined with a Kalman filter had lower MAPE than exponential smoothing alone in 100 of 105 trips — [IIT Madras CoEUT PDF (URL now returns 404)](https://coeut.iitm.ac.in/umcsp/pdfweb/3a3vasanth.pdf) [SN]
  - A Kalman filter fed GPS from the previous two bus trips to predict the next bus — [i-scholar](https://i-scholar.in/index.php/CURS/article/download/120519/109023) [SN; exact attribution uncertain]
  - Temporal SVM models beat spatial ones in high-mean, high-variance sections, with a rule that switches between them based on current travel time — [Transport 2021 record](https://nufind.nu.edu.sa/EdsRecord/edsair,edsair.doi.dedup.....f99e21022142f83793e6e0051f40b611) [SN]
- A Shenzhen multi-route Kalman model uses both a weighted average over preceding buses of all routes on the road and the preceding bus of the same route; evaluated by MAE/MAPE/RMSE, but no numbers seen — [Bohrium listing](https://www.bohrium.com/paper-details/dynamic-bus-travel-time-prediction-models-on-road-with-multiple-bus-routes/814609769892413441-4389) [SN]
- Combining profile similarity (k-medoids) with a Kalman filter on preceding vehicles over the same links "improves the quality of the predictions" — [RWTH Hybrid.pdf](https://dbis.rwth-aachen.de/dbis/wp-content/uploads/2021/12/Hybrid.pdf) [SN]
- **k-NN (Dublin line 46A, BusTime) [FT].** 4,311 trips, about 30-s GPS, Nov 2012 and Jan 2013. MAPE, stop-based / distance-based:
  - delay model 8.68 / 7.54%;
  - k-NN 8.03 / 7.12%;
  - kernel regression 7.63 / 6.47%;
  - simplified additive model (time and distance only) 29.85 / 20.15%.
  - k-NN prediction took about 1 min for all test trips at full data, or under 15 s with the stop-based reduction.
  - Source: [BusTime, ar5iv 2003.10373](https://ar5iv.labs.arxiv.org/html/2003.10373)
- k-NN used to find similar historical patterns, then fed into a Kalman filter, beat static-input methods (Kumar et al., Transportation Letters 2019, Indian data) — [WTR record](https://www.worldtransitresearch.info/research/7533) [SN]
- Random forests on nearest neighbours (RFNN) reached MAPE 6.90% and 7.58% on two routes against LR, k-NN, SVM and RF; the k-NN figures were not visible — [Yu et al. 2018, BUAA record](https://research.buaa.edu.cn/en/publications/prediction-of-bus-travel-time-using-random-forests-based-on-near-/) [SN]
- A k-NN classifier was compared with a Kalman filter and ARIMA across Surat, Mysore and Chennai (Jairam, Kumar, Arkatkar, Vanajakshi, TRR 2018). No numbers in the abstract, and the page title and citation title do not match — [WTR 7355](https://www.worldtransitresearch.info/research/7355) [AB]
- **Spatio-temporal correlation.**
  - Link travel times on one bus route show both local and long-range correlation — [Chen et al., arXiv 2202.09485](https://arxiv.org/abs/2202.09485) [AB]
  - Modelling two adjacent buses' link-time vectors together with their headway (Guangzhou, 20-link route) "significantly outperforms" models that ignore bus-to-bus interaction, for both means and distributions — [Chen et al., arXiv 2206.06915](https://arxiv.org/abs/2206.06915) [AB]
- Combining real-time taxi data with bus data (Xi'an, June 2017), with routes split into dwell and transit segments each modelled separately, improved accuracy "especially under abnormal traffic conditions" — [Ma et al. 2019, TR-C, WTR record](https://www.worldtransitresearch.info/research/7568) [SN]
- **IIT Madras "Generalist–Specialist" framework (news article; underlying paper not read).**
  - A physics-informed LSTM handles most sections; XGBoost takes over on sections whose travel time exceeds a data-derived threshold.
  - High-magnitude peaks are under 1.8% of training data, so models treat them as noise.
  - If a section peaks on one trip, there is about a 25.9% chance it peaks on the next trip; this triggers the specialist.
  - A collaborator is quoted saying it cut error on extreme events by about 80%.
  - Source: [IIT Madras Tech Talk](https://tech-talk.iitm.ac.in/wheres-the-bus-theres-the-bus/)

### Inferences
- **Our ratios are a crude Kalman/EWMA.** Baseline B and the LightGBM "last-30-min link/route ratio" weight every observation in a fixed window equally. The literature points to three upgrades, best added as GBDT features rather than a hand-tuned filter:
  - (a) for each downstream link, the latest traversal ratio and its *age*;
  - (b) exponentially time-decayed ratios at several half-lives (e.g. 5 / 15 / 45 min), letting the model choose;
  - (c) a horizon feature: the predicted time until our bus reaches that link, as BusTr does by evaluating traffic at the extrapolated arrival time.
- **Expected size of that gain.** No paper isolates it. Given BusTr's total real-time effect (~16%) and the ~13% we already capture, the remaining gain is perhaps 0.1–0.4 pp MedAPE (speculative).
- **Shrink the real-time ratio.** Movia's rule-based adjustment did worse than the historical average. So the ratio should move back toward 1 when it rests on few or old observations; a Kalman-style gain is roughly var_hist / (var_hist + var_obs/n). GBDT only does this if count and age are features.
- **Use buses still on a link (not found in the literature; speculative).** A bus currently on a downstream link whose elapsed time already exceeds the historical median signals congestion before any completed traversal exists. This is cheap to compute from 11-s pings.
- **Use downstream state, not just upstream.** EDB beat the unidirectional version by up to about 6.6–8.9 MAPE points (best case). Add recent ratios from adjacent links (±1–3) and a distance-weighted "corridor ratio" over the ride's downstream links. Our multi-route links also suit the Shenzhen design: a weighted average over all routes plus the same-route previous bus.
- **Analog-day k-NN is low priority.** With 3–4 weeks of history the pool of similar past days is small. In Dublin, kernel regression beat k-NN by only 0.65 pp MAPE, and neither was compared with GBDT using real-time features.
- **Add a cheap peak specialist.** Our errors are skewed (mean −2 to −3 min vs median −0.5 min), which suggests that tail peaks are being treated as noise, as the IIT Madras work found. A simple analogue: a "peak state" flag (e.g. the previous bus on the link exceeded the historical P90), plus a separate model or upper-quantile output for flagged links.

### Gaps
- No paper isolates "previous bus on the same downstream link" against a fixed-window average with a clean ablation number.
- Crudden & Berrebi's accuracy figures were not accessible (Springer login redirect).
- The TCS Delhi results are best-case improvements read from figures; averages and absolute MAPE are not given, and the units are ambiguous.
- No Delhi-wide, multi-route evaluation of real-time fusion was found.

## 2. Segment-level (direct multi-link) vs link-level summation

### Takeaway
There is no clean bus-data ablation of "direct segment model vs sum of link predictions". The evidence is a theoretical result, design arguments and indirect head-to-heads:
- **Theory.** The route estimate that minimises MAE is a mix of segment means and medians, and the mix depends on how many segments the route has. So a sum of link medians is biased low for right-skewed links.
- **Joint models win.** Models that predict all downstream links together (ConvLSTM, seq2seq) and are scored on the sum beat per-link or recursive methods.
- **Correlation.** Link times are correlated over both short and long ranges, so summing independent link predictions misstates the ride's distribution.
- **Additive can still work.** BusTr is additive yet strong, probably because its units are trained on whole multi-segment trips.

### Cited Findings
- Zliobaite & Khokhlov (St Petersburg, one year of route-planner GPS data): to minimise expected route MAE, the optimal estimate is "a combination of the mean and the median travel times on each segment", and the combination "depends on the number of segments in the route" — [arXiv 1507.08444](https://arxiv.org/abs/1507.08444) [AB; numeric gains not seen]
- DeepTravel: in segment-based estimation "the error of the estimated travel time will be accumulated along each road segment", so it estimates the whole path instead. It has no direct sum-vs-whole comparison — [ar5iv 1802.02147](https://ar5iv.labs.arxiv.org/html/1802.02147) [FT]
- The TCS Delhi model predicts all later sections together as one vector, to avoid the error accumulation of recursive multi-step Kalman filters. This is argued, not measured — [arXiv 2210.01655v2](https://arxiv.org/html/2210.01655v2) [FT]
- Copenhagen 4A: the ConvLSTM predicts all 32 links together, then sums them for the journey. Journey MAPE 4.19%, vs 5.02% for a pure LSTM and 6.51% for HA. Cross-route correlation is not modelled; the authors propose graph convolutions as future work — [ar5iv 1903.02791](https://ar5iv.labs.arxiv.org/html/1903.02791) [FT]
- BusTr is purely additive (segment and stop units) but trained on multi-segment trip "shingles" of at least 1–5 km. It reaches 13.24% MAPE vs DeepTTE's 31.47%, or 21.24% if DeepTTE's failed runs are excluded. That trip-level training is what lets an additive model work is my reading, not the authors' — [ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882) [FT]
- Montreal STM, errors at three scales (RMSE): LSTM 2.17 min per segment and 1.85 min per trip; XGBoost 2.30 and 1.95 min — [arXiv 2601.18521](https://arxiv.org/html/2601.18521) [FT]
- **Correlation structure.**
  - Local and long-range correlations exist on a bus route — [Chen et al., arXiv 2202.09485](https://arxiv.org/abs/2202.09485) [AB]
  - Büchel & Corman (Physica A 2022) chain consecutive section running times in a hidden Markov model. Later papers say this captures only adjacent dependence — [IDEAS listing](https://ideas.repec.org/a/eee/phsmap/v592y2022ics0378437121009547.html) [SN]
  - Vienna taxi data: estimating the variance of a route's prediction error needs every covariance between link errors; driving distance between links and trip-count ratio are the main drivers — [arXiv 1808.06610](https://arxiv.org/pdf/1808.06610) [SN]
- Dublin: whole-route predictors were tested against segment-based ones. Longer routes had higher absolute error; the winner was not visible — [Springer chapter, doi 10.1007/978-3-031-30855-0_10](https://doi.org/10.1007/978-3-031-30855-0_10) [SN]
- On taxi data, whether modelling speeds or travel times directly works better "depends on the measure of accuracy" — [ETRR 2018](https://link.springer.com/article/10.1186/s12544-018-0315-7) [SN]

### Inferences
- **Our bias pattern fits the theory (my arithmetic, no source).**
  - Baseline A sums link *medians*. For right-skewed link times, the median of a sum exceeds the sum of medians, and it moves toward the sum of means as links are added, more slowly when links are positively correlated.
  - Under lognormality, mean/median = exp(σ²/2). With log-scale σ of 0.3–0.5 per link, that is 4.6–13.3% per link.
  - Diagnostic: plot signed ride error against number of links. If the bias grows with ride length, a correction factor per (number of links × hour), or a Zliobaite-style mean/median blend, is a one-hour fix.
- **Our loss doesn't match our metric.** The link-level LightGBM (L2 on log ratio) optimises per-link geometric means, not ride-level MedAPE. This may explain why history-only LightGBM (12.0%) is *worse* than the simple Baseline A (11.5%).
- **Add a ride-level second stage.**
  - Target: log(actual_ride / Σ link_pred).
  - Objective: L1, or quantile at 0.5, to match MedAPE.
  - Features: Σ link_pred; Σ historical medians, means and IQRs; number of links; km; start hour and weekday; route; mean and max recent ratio over downstream links; share of downstream links with a fresh observation; observation ages.
  - Training data: sample rides from the training weeks; tens of millions are possible, so subsample.
  - Why: it optimises what we evaluate and can learn shared congestion that independent link sums miss.
  - Expected gain (speculative): about 0.2–0.6 pp MedAPE and most of the mean bias.

### Gaps
- No bus study compares a direct segment-level model with summed link-level models on the same data using MAPE or MedAPE.
- Zliobaite & Khokhlov's numbers and the Dublin chapter's winner were not visible in the sources I could access.

## 3. Model families on bus AVL data: GBDT vs LSTM / ConvLSTM / GNN / Transformer

### Takeaway
- **Deep models win only modestly, and only with months of data.**
  - Montreal: an LSTM trained on 6 months beat XGBoost by about 5% trip RMSE (1.85 vs 1.95 min), but needed 26 min of GPU training vs 1.5 min on CPU.
  - Transformers (PatchTST, Autoformer) did *worse* than XGBoost.
  - Copenhagen: ConvLSTM on 23 weeks cut journey MAPE by 36% relative to a historical average, but had no GBDT baseline.
- **With little data, deep models lose.** In Dublin, LSTMs trained on 3,000 trips or fewer had worse MAPE than k-NN or kernel regression. DeepTTE was unstable against BusTr.
- **Implication for us.** With 31 days and a CPU, better GBDT features and targets are the better use of a week. A per-route seq2seq on Colab (as in the 7-week Delhi study) is only a stretch experiment.

### Cited Findings
- **Montreal STM (6 months of GTFS, GTFS-RT and daily weather) [FT].** Results from the paper's Tables 3–4:

  | Model | Stop-to-stop R² | Segment RMSE (min) | Trip RMSE (min) | Training |
  |---|---|---|---|---|
  | LSTM | 0.6621 | 2.17 | 1.85 | 26 min on GPU, 31k params |
  | XGBoost | 0.6194 | 2.30 | 1.95 | 1.5 min on CPU |
  | xLSTM | 0.623 | 2.38 | 2.06 | |
  | PatchTST | 0.5656 | 2.45 | 2.08 | |
  | Autoformer | 0.4345 | 2.75 | 2.35 | |

  - Inference latency: LSTM 300 ms, XGBoost 100 ms.
  - The paper calls XGBoost "admirably competitive" and a CPU-only option at about 6.9% accuracy cost; it says the LSTM beats transformers "by 18–52%".
  - Source: [arXiv 2601.18521](https://arxiv.org/html/2601.18521)
- A related ETS Montréal thesis reports the LSTM beating XGBoost by 9.3% in R² (R² = 0.7121 at the stop-to-stop level). These numbers differ from the arXiv version — [ETS thesis](https://espace2.etsmtl.ca/33721/1/Sboui-L-2026-33721.pdf) [SN]
- **Copenhagen 4A [FT].**
  - ConvLSTM 4.19% and pure LSTM 5.02% journey MAPE, vs HA 6.51%; no GBDT baseline.
  - Training took under 20 min on 8 cores and a GTX 1070 for 32 links, so daily retraining was practical.
  - Data: 23 training weeks, about 1.2M observations. At 2-min resolution 89% of time steps had no data, hence 15-min bins.
  - Source: [ar5iv 1903.02791](https://ar5iv.labs.arxiv.org/html/1903.02791)
- **Copenhagen 300S [FT].** The deep quantile ConvLSTM beat a Bayesian RNN and a Kalman filter on both point and interval accuracy, using 13 training weeks (333,118 observations on 39 links) — [ar5iv 2104.06819](https://ar5iv.labs.arxiv.org/html/2104.06819)
- **Dublin, BusTime [FT].**
  - LSTM MAPE (stop / distance): 13.69 / 16.36% with 1,000 trips; 13.87 / 10.17% with 3,000 trips.
  - k-NN 8.03 / 7.12% and kernel regression 7.63 / 6.47% with 4,311 trips.
  - LSTM training took 650–3,000 s on a laptop CPU, hyperparameters untuned.
  - The authors still rank the LSTM most accurate, citing MAE of 85.87 s at 1,000 trips, which is inconsistent with its MAPE.
  - Source: [ar5iv 2003.10373](https://ar5iv.labs.arxiv.org/html/2003.10373)
- **BusTr vs DeepTTE [FT].** BusTr is a small structured network (hidden width 32). In 37% of DeepTTE runs MAPE never fell below 40%. BusTr's MAPE improved with training up to 100k steps (13.886% at 25k → 13.240% at 100k), then plateaued — [ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882)
- **Delhi route 399 [FT].** A seq2seq model on one route with 7 weeks of training beat ConvLSTM, DpAR and two Kalman-filter baselines (best-case improvements) — [arXiv 2210.01655v2](https://arxiv.org/html/2210.01655v2)
- **GBDT wins in smaller studies [SN].**
  - Gradient boosting beat historical averages and linear regression on Dublin AVL — [TCD dissertation](https://publications.scss.tcd.ie/theses/diss/2020/TCD-SCSS-DISSERTATION-2020-078.pdf)
  - XGBoost was "significantly better" than GBM, RF and SVR on GPS bus data — [IIT Hyderabad poster](https://newslab.iith.ac.in/files/posters/buspredict.pdf)
  - XGBoost beat RF, GB and LSTM in Sri Lanka — [Univ. of Moratuwa](https://dl.lib.uom.lk/bitstreams/91390869-0d9c-4c8e-b8cf-8051b37c6182/download)
  - IIT Madras chose XGBoost over ANN, RF and EMA as its peak specialist — [IIT Madras Tech Talk](https://tech-talk.iitm.ac.in/wheres-the-bus-theres-the-bus/)
- A review of bus studies reports a best MAPE of 7.59% — [Palys et al., ICCS 2022](https://www.iccs-meeting.org/archive/iccs2022/papers/133510662.pdf) [SN]

### Inferences
- **Data needed by the deep models that won:**
  - Copenhagen: 13–23 weeks, 0.3–1.2M link observations, 32–39 links.
  - Montreal: 6 months.
  - Delhi: 7 weeks, but on a single 34-section route.
  - Our 31 days (about 3 weeks train + 1 week test) is at or below the low end, so expect little or no gain over GBDT network-wide.
- **Size of the best plausible gain.** The best head-to-head (Montreal) shows about 5% relative error reduction over XGBoost. At our level that is about 0.5 pp MedAPE, at high engineering risk. Feature, target and calibration work (sections 1, 2, 6) is the better bet this week.
- **Skip transformers.** They underperformed XGBoost on bus data.
- **If we try deep models anyway:**
  - Most proven: per-route ConvLSTM or seq2seq with 15-min bins and previous-bus decoder inputs, on the 5–10 busiest routes, on Colab.
  - Cheaper: stack the deep model's output as a feature into LightGBM.

### Gaps
- No GNN-vs-GBDT head-to-head on bus AVL data was found.
- No LightGBM-vs-deep comparison on Indian data was found.
- Montreal does not report MAPE.
- The Copenhagen studies lack a GBDT baseline.

## 4. Features with documented value (same-weekday-last-week, holidays/festivals, weather/rain, school timings, dwell vs running time, boarding counts)

### Takeaway
Quantified feature ablations are scarce:
- **BusTr ablations (MAPE increase when removed):** real-time traffic +16%, time-of-week +5%, route ID +3%, spatial identity (route IDs plus all spatial cells) +69%.
- **Rain:** strongly lengthens road travel in Indian cities (Mumbai +10–130% depending on intensity; Bengaluru commutes +30% on average on rainy days), but no bus-prediction ablation exists.
- **Same-weekday-last-week:** used as a seasonal input in the Delhi seq2seq, not separately measured.
- **Dwell vs running time:** separated in production systems (TransitClock, BusTr) and in Xi'an, but the gain is not isolated.
- **Boarding counts:** drive dwell time, but no number for prediction gain was found.
- **Holidays, festivals, school timings:** no quantified evidence found.

### Cited Findings
- **BusTr ablations (MAPE) [FT]:**
  - no road traffic 15.443 (+16%);
  - no time-of-week 13.865 (+5%);
  - no route IDs 13.602 (+3%);
  - no route IDs and no level-15 cells 14.923 (+13%);
  - no route IDs and no spatial cells 22.190 (+69%).
  - Source: [ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882)
- **Delhi route 399:** the closest same-weekday trip from the previous week is a seasonal decoder input; Sundays were excluded — [arXiv 2210.01655v2](https://arxiv.org/html/2210.01655v2) [FT]
- **Montreal:** weather was joined at daily resolution from airport stations, which the authors list as a limitation; no weather ablation is reported — [arXiv 2601.18521](https://arxiv.org/html/2601.18521) [FT]
- **Rain in Indian cities [SN]:**
  - Mumbai, two major routes: rainfall raised travel time by 10–130%. The source does not say clearly whether this was GPS data or buses — [WCTR 2019 abstract](https://www.wctrs-society.com/wp-content/uploads/abstracts/mumbai/WCTR2019_Mumbai_526.pdf)
  - Bengaluru office commutes (not buses): +30% on average on rainy days, up to +62% in some areas — [The News Minute](https://www.thenewsminute.com/article/bengaluru-rains-pushed-average-commute-time-62-august-167433)
  - Bengaluru BMTC passenger survey: waiting time at stops +45%; 70% reported longer travel in extreme rain — [NITK](https://idr.nitk.ac.in/items/9a06c145-8b89-4bc6-8c2a-8074ac6a48cb/full)
- **Chennai drift:** corridor travel time rose about 10% and its variability (IQR) about 40% between 2014 and 2016, concentrated at six critical intersections in peaks — [Khadhir, Kumar, Vanajakshi 2020, JITS](https://www.worldtransitresearch.info/research/8277) [AB]
- **Dwell vs running time:**
  - TransitClock treats travel time and dwell time separately, which it says helps predict bunching — [TransitClock site](https://thetransitclock.github.io/) [SN]
  - BusTr has separate stop (dwell) units and segment units — [ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882) [FT]
  - Xi'an: separate dwell and transit models with real-time taxi data — [WTR 7568](https://www.worldtransitresearch.info/research/7568) [SN]
  - Boston: low-frequency AVL regression splits travel time into running time, dwell at stops and signal delay — [TRID 1392256](https://trid.trb.org/View/1392256) [SN]
  - A 2025 hybrid LSTM on GPS-derived run and dwell times (15-s GPS) reports MAPE 23.45%, with no baseline visible — [SciTePress 2025](https://www.scitepress.org/publishedPapers/2025/133492/pdf/index.html) [SN]
- **Boarding counts [SN]:**
  - Dwell time is highly correlated with boardings and alightings; crowding and fare type also matter — [Reich et al. survey, arXiv 1904.05037](https://arxiv.org/pdf/1904.05037)
  - Smart cards cut individual boarding time from over 11 s to about 3 s (Queensland) — [QUT](https://eprints.qut.edu.au/63224/18/Modelling_Busway_Station_Dwell_Time_Using_Smart_Cards.pdf)

### Inferences
- **Rain.** In normal years the southwest monsoon has left Delhi by October (general climatology, not sourced here). Rain flags are therefore probably low value for the October 2026 test week, but essential for year-round use (July–September). Get hourly rainfall from IMD or Open-Meteo and check whether any test-week day had rain before investing.
- **Festivals and holidays.** October–November is India's main festival season (Navratri/Dussehra, Diwali, Chhath; general knowledge). Check 2026 dates against the official Delhi holiday list. A festival day in the held-out week would hurt any model trained on 3 weeks. A cheap fix: a day-type feature (gazetted holiday / festival eve / normal), plus error analysis by day.
- **Same-weekday-last-week.** We have only about 4 weeks. Add "same link × hour, 7 days earlier, ratio to median" as a feature. The gain is likely small, because historical medians already condition on weekday/weekend × hour.
- **Dwell vs running time.** From 11-s pings, derive per-stop dwell (speed ≈ 0 inside a stop buffer) and per-link running time, each with its own historical median. Apply real-time ratios to running time (congestion) but take dwell mainly from history and time of day (demand). This follows the TransitClock and BusTr design; the gain is unknown.
- **Boarding counts.** DTC ticket-machine or Delhi travel-card transactions by stop could predict dwell, if accessible. Availability not checked.
- **School timings.** Mostly absorbed by hour-of-week medians. Vacation periods (e.g. a Diwali break) need a day-type flag.

### Gaps
- No ablation of holiday, festival or school-timing features in bus prediction.
- No measured accuracy gain from APC or ticketing boarding data.
- No Delhi-specific study of rain and bus travel time; the Mumbai figure is a range from an abstract.

## 5. Probabilistic prediction (quantile regression, conformal prediction, distributional models; calibration; reliability buffers)

### Takeaway
- **Quantile models can be near-calibrated with enough data.** In Copenhagen, a deep quantile ConvLSTM achieved 89% coverage at a 90% target for the 15-min horizon, and 86% at 30–45 min. A Kalman filter got 75–84%, and a Bayesian RNN collapsed to about 64%.
- **Plain quantile regression tends to under-cover.** Conformalized quantile regression (CQR) adds a finite-sample coverage guarantee around any quantile model, LightGBM included.
- **Predict ride quantiles directly.** Quantiles are not additive, so ride-level quantiles should not be built by summing link quantiles.

### Cited Findings
- **Copenhagen 300S (39 links, 13 training weeks) [FT].** Coverage (ICP) / mean interval length (MIL):

  | Target | Model | 15 min | 30 min | 45 min |
  |---|---|---|---|---|
  | 90% | Deep quantile ConvLSTM (DQR) | 89% / 498 s | 86% / 498 s | 86% / 498 s |
  | 90% | Bayesian RNN (BRNN) | 86% / 493 s | 65% / 303 s | 64% / 295 s |
  | 90% | Kalman filter | 75% / 347 s | 80% / 442 s | 84% / 521 s |
  | 60% | DQR | 64% / 256 s | 61% / 255 s | 58% / 255 s |
  | 60% | BRNN | 49% / 200 s | 37% / 138 s | 37% / 135 s |
  | 60% | Kalman filter | 49% / 178 s | 55% / 227 s | 59% / 267 s |

  - DQR shows "a constant, but very small underestimation of the uncertainty interval (1-4 pp.)" at 80, 90 and 95% targets.
  - The BRNN "is not able to learn the time-dependent uncertainty".
  - Source: [ar5iv 2104.06819](https://ar5iv.labs.arxiv.org/html/2104.06819)
- CQR wraps any quantile regressor, gives distribution-free finite-sample coverage, and tends to produce shorter intervals than other conformal methods — [Romano et al. 2019, arXiv 1905.03222](https://arxiv.org/pdf/1905.03222) [SN]
- Plain quantile regression on traffic flow gives intervals that are too narrow and poorly calibrated, which motivated CQR — [ECCOMAS 2024 draft](https://scipedia.com/wd/images/1/1f/Draft_Sanchez_Pinedo_518896956pap_2475.pdf) [SN]
- QuanTraffic (IEEE T-ITS 2023) uses a CQR-based quantile function to refine prediction intervals around a deep model's travel-time or speed forecasts — [White Rose eprint](https://eprints.whiterose.ac.uk/204677/1/tits23.pdf) [SN]
- A hobby project applies group-wise ("Mondrian") conformal prediction to bus arrivals, calibrated to 90% within each route × day type × horizon bucket so coverage holds per cell, not just on average. Informal, not peer-reviewed — [Madison Metro ML](https://personalwebsite-hazel-two.vercel.app/work/madison-metro-ml) [SN]
- **Distribution models:**
  - A Bayesian Gaussian mixture over adjacent buses' link-time vectors and headway beats baselines in both mean and distribution (Guangzhou) — [arXiv 2206.06915](https://arxiv.org/abs/2206.06915) [AB]
  - A hybrid Markov model with link distributions whose spread varies by condition (Gainesville GTFS-RT, 2023) gives "narrower uncertainty bounds" than baselines; no numbers in the abstract — [arXiv 2503.05907](https://arxiv.org/abs/2503.05907) [AB]
- "Uncertainty in Bus Arrival Time Predictions: Treating Heteroscedasticity With a Meta-Model Approach" (IEEE T-ITS 2016, Koutsopoulos co-author) is a quantile-regression meta-model for intervals. Full text returned HTTP 403 — [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/1502220/1/QRbus.pdf) [SN]

### Inferences
- **A recipe for us.**
  1. Train LightGBM quantile models (α = 0.1, 0.5, 0.9) on the ride-level target from section 2.
  2. On a calibration week (the week before test), compute E = max(q_lo − y, y − q_hi) and widen the interval by the ⌈(1−α)(n+1)⌉/n empirical quantile of E.
  3. Calibrate separately by hour band × ride-length bucket (Mondrian).
  4. Report coverage (ICP) and mean width (MIL) as Copenhagen does.
  5. Publish P50 as the ETA and P90 − P50 as the "reliability buffer" for journey planners.
- **Expected width.** Copenhagen's 90% intervals were about 8.3 min wide (MIL 498 s) on 39-link journeys, a similar scale to our 21-min rides.
- **Why summing link quantiles fails.** Summed link P90s overstate the ride P90 when link deviations are weakly correlated, and are fine only under perfect correlation. Ride-level direct quantiles avoid this.
- **Drift.** With 31 days and festival-season drift, a fixed calibration week may under-cover. Re-calibrate daily (adaptive conformal) and check coverage on festival days separately.

### Gaps
- No bus study reporting coverage numbers for conformal + GBDT was found.
- The T-ITS 2016 meta-model's numbers were inaccessible.
- No evidence on how riders actually use reliability buffers.

## 6. Bias: why log-target / median models under-predict means; retransformation (smearing); when to optimize median vs mean

### Takeaway
Our short bias (mean −2 to −3 min, median −0.5 min) is expected. Three sources compound:
1. **Log-space training.** L2 regression on a log target predicts the geometric mean, roughly the median, which is below the mean by a factor exp(σ²/2) under lognormality.
2. **Summing link medians.** For right-skewed links this understates the ride's median and mean (section 2).
3. **Percentage-error metrics.** These reward under-forecasting: absolute percentage error is minimised by the "median of order −1", which "tends to support severe underforecasts" (Gneiting).

Choose the target by use:
- **Median** when the KPI is MedAPE.
- **Mean** when predictions are summed or used for operations planning (via grouped smearing or a log-link objective).
- **An upper quantile** for "don't make me late" rider ETAs.

### Cited Findings
- Gneiting (JASA 2011) [FT]:
  - squared error is consistent for the mean, absolute error for the median;
  - absolute percentage error is consistent for med^(−1), the β-median with density ∝ f(y)/y, and "tends to support severe underforecasts, as compared to the mean or median";
  - relative error corresponds to med^(1).
  - Source: [ar5iv 0912.0902](https://ar5iv.labs.arxiv.org/html/0912.0902)
- **Retransformation [SN].**
  - With log y = xb + e, E[y|x] = exp(xb)·E[exp(e)]. Duan's smearing estimates the second factor by averaging exp(residuals), which is consistent only if errors have constant variance across x — [Statalist](https://www.stata.com/statalist/archive/2002-12/msg00193.html)
  - Worked example: the naive retransformed mean was $4,853 against a true $6,516; smearing gave $6,725 — [Healthcare Economist](https://www.healthcare-economist.com/?p=4424)
  - A GLM with a log link models log E[y] directly and avoids retransformation — [Statalist 2010](https://www.stata.com/statalist/archive/2010-05/msg00977.html)
- The MAE-optimal route estimate mixes segment means and medians, depending on the number of segments — [arXiv 1507.08444](https://arxiv.org/abs/1507.08444) [AB]
- BusTr trains with MSE (which targets the mean) but picks checkpoints by validation MAPE; it reports no bias analysis — [ar5iv 2007.00882](https://ar5iv.labs.arxiv.org/html/2007.00882) [FT]
- Peaks are under 1.8% of training data and get treated as noise, a mechanism for under-predicting the tail — [IIT Madras Tech Talk](https://tech-talk.iitm.ac.in/wheres-the-bus-theres-the-bus/) [FT, news]

### Inferences
- **Size of the log-training effect (my arithmetic).** With log-scale residual σ of 0.25–0.35 at ride level, exp(σ²/2) = 1.03–1.06, which explains only about 0.7–1.3 min of the 2–3 min mean bias. The rest likely comes from heavy tails: incidents, bunching or holding, detours, and stop-event artefacts (section 7).
- **Fixes, cheapest first:**
  - (i) grouped smearing: multiply predictions by mean(actual/pred) per hour band × ride-length bucket, estimated on a calibration week, giving an unbiased mean output;
  - (ii) LightGBM 'gamma' or 'tweedie' objective on raw seconds (log link, models the conditional mean; general LightGBM knowledge);
  - (iii) L1, or quantile at α=0.5, objective at ride level to optimise the median for MedAPE;
  - (iv) publish both P50 and the mean or P80.
- **Smearing will slightly worsen MedAPE.** Keep the mean as a separate output. Don't tune only on MedAPE or MAPE if downstream consumers sum times (transfers, scheduling), because APE rewards under-forecasting.
- **Check the data first.** Before modelling the mean bias away, check whether the held-out actuals include artefacts (terminal layovers within a ride, missed stops creating long links).

### Gaps
- No transit paper measures retransformation bias for log-target travel-time models.
- No evidence on which loss (mean, median, upper quantile) riders or journey planners prefer.

## 7. Stop-event detection quality (map matching, arrival/departure detection from sparse pings) and its effect on accuracy

### Takeaway
- **Interpolation noise is small for us.** Interpolating arrival and departure times from polled positions gives errors up to about the polling interval, roughly 11 s for DTC. That is small against 21-min rides (≈0.4% typical, under 2% worst case).
- **Outliers matter more.** Skipped or missed stops, GPS gaps, map-matching tolerance and layovers create outliers. These inflate training noise, recent-ratio features and especially the mean error.
- **No measured effect.** No study was found that measures the downstream effect on prediction accuracy.

### Cited Findings
- Interpolation errors "can be almost as large as the polling interval", especially where speeds vary (congestion). Stop or timepoint records are preferred — [NAP/TCRP chapter](https://nap.nationalacademies.org/read/13907/chapter/12) [SN]
- TriMet logs arrival and departure by geofence crossing and dwell by door-open events — [TREC/PSU report](https://ppms.trec.pdx.edu/media/project_files/Exploring_Applications_of_Second-Generation_Archived_Transit_Data.pdf) [SN]
- GPS-2-GTFS rules: arrival is a near-zero speed inside a stop buffer; departure is the next non-zero speed. Failure modes are skipped stops and missing GPS (poor coverage) — [arXiv 2412.15221](https://arxiv.org/pdf/2412.15221) [SN]
- Singapore/London, from noisy ETA records:
  - exact downstream stop-passage detection above 50% precision/recall, above 80% when 1-minute error is allowed;
  - about 80% detection accuracy at 200–600 m spatial error.
  - Source: [arXiv 1907.08483](https://arxiv.org/pdf/1907.08483) [SN]
- TransitClock: cutting the map-matcher's maxDistance from 300 m to 100 m "improved things"; a max-speed constraint was also added. No numbers — [TransitClock wiki](https://github.com/TheTransitClock/transitime/wiki/Prediction-Kalman-testing) [FT]
- Copenhagen: at 2-min resolution 89% of time steps had no measurement (1.7 observations per 15-min step), so data were aggregated to 15-min bins — [ar5iv 1903.02791](https://ar5iv.labs.arxiv.org/html/1903.02791) [FT]
- An IIIT-Delhi dataset covers 500+ Delhi routes with GPS every 10 s — [ar5iv 1910.08903](https://ar5iv.arxiv.org/html/1910.08903) [SN]
- Low-frequency AVL can still split travel time into running time, dwell and signal delay — [TRID 1392256](https://trid.trb.org/View/1392256) [SN]

### Inferences
- **Noise floor (my arithmetic).** With about 11-s pings and uniform interpolation error, the SD at each ride endpoint is about 3 s, or about 4.5 s for the ride, i.e. ≈0.4% of 1,260 s. Worst case is about 22 s (1.7%). This is negligible against 10.4% MedAPE.
- **The real risks:**
  - (a) GPS gaps of 60 s or more turning link times into interpolations;
  - (b) skipped or non-served stops;
  - (c) detours and short-turns;
  - (d) layovers inside a ride.
- **Quick QA.**
  1. Tag every link traversal with its largest ping gap and an interpolation flag.
  2. Compute MedAPE and mean error separately for clean and flagged rides.
  3. Exclude flagged traversals from historical medians and real-time ratios.
  4. Use trimmed or median ratios plus counts, so one artefactual traversal in the last 30 min cannot swing a link's ratio.

### Gaps
- No study measuring how stop-detection quality affects prediction accuracy.
- No validated precision/recall for 10–15-s GPS stop-event detection in Indian mixed traffic.

## 8. Open-source implementations, reusable code and benchmark datasets

### Takeaway
Reusable code and data:
- **TheTransitClock** (Java): takes GTFS + GTFS-RT vehicle positions, separates dwell and travel time, uses a Kalman filter, outputs GTFS-RT trip updates; deployed at Metro Transit and elsewhere.
- **GPS-2-GTFS** (Python): raw GPS → stop events.
- **DeepTTE forks** (PyTorch): need adapting to bus data.
- **CQR** reference work for conformal intervals.
- **Datasets:** Dublin 46A, Copenhagen (Movia), IIIT-Delhi's Delhi GPS set, and public GTFS-RT feeds (Seattle, Trondheim, Montreal).

No public code was confirmed for BusTr, the TCS Delhi seq2seq, or the Copenhagen ConvLSTM.

### Cited Findings
- TheTransitClock takes a GTFS-RT vehicle-positions feed, outputs GTFS-RT trip updates, and treats dwell and travel time separately. Deployments include Metro Transit (2020), goEuropa (Poland), CityMovil (Chile), OmniModal (Florida) and Cambridge Systematics (Washington) — [TransitClock site](https://thetransitclock.github.io/) [SN]; the Metro Transit selection is confirmed with no accuracy figures in [CamSys blog](https://camsys.com/blog/cs-helps-metro-transit-minneapolis-better-predict-bus-arrival-times) [FT]
- Crudden & Berrebi (2023) present a scalable way to run Kalman filters on a whole live network, implemented in TheTransitClock — [IDEAS listing](https://ideas.repec.org/a/kap/netspa/v23y2023i2d10.1007_s11067-021-09541-w.html) [SN]
- **DeepTTE (AAAI 2018) code** [SN]:
  - [Dawn90/DeepTTE](https://github.com/Dawn90/DeepTTE);
  - [oscarhsu/DeepTTE](https://github.com/oscarhsu/DeepTTE): full code with Chengdu sample data, Python 2.7;
  - a Python 3.10 port listed at [github.imc.re/nadabadawi/DeepTTE](https://github.imc.re/nadabadawi/DeepTTE), a mirror URL.
  - No GTFS-RT loader exists.
- GPS-2-GTFS converts raw transit GPS into GTFS-style stop events; installable as `gps2gtfs` — [arXiv 2412.15221](https://arxiv.org/pdf/2412.15221), [libraries.io](https://libraries.io/pypi/gps2gtfs) [SN]
- Aemmer et al. 2024 (Journal of Urban Management) use 4 months of GTFS-RT from Seattle and Trondheim to study whether bus travel-time models generalise across cities. The page returned HTTP 403; code availability unknown — [DOAJ](https://doaj.org/article/5135782f26454dcf976ace01eecfa725) [SN]
- **Benchmarks [FT]:**
  - Dublin 46A (4,311 trips, Nov 2012 and Jan 2013, about 30-s GPS) — [ar5iv 2003.10373](https://ar5iv.labs.arxiv.org/html/2003.10373)
  - Copenhagen 4A (Movia, May–Oct 2017) — [ar5iv 1903.02791](https://ar5iv.labs.arxiv.org/html/1903.02791)
  - Copenhagen 300S/200S (Aug–Nov 2020) — [ar5iv 2104.06819](https://ar5iv.labs.arxiv.org/html/2104.06819)
  - Montreal STM (6 months GTFS-RT) — [arXiv 2601.18521](https://arxiv.org/html/2601.18521)
- Delhi bus GPS dataset (IIIT-Delhi; 500+ routes, 10-s GPS) — [ar5iv 1910.08903](https://ar5iv.arxiv.org/html/1910.08903) [SN]
- DeepTRANS (VLDB 2020), a deep-learning system for public-bus travel time, is a further pointer; not read — [VLDB PDF](https://www.vldb.org/pvldb/vol13/p2957-tran.pdf) [SN]

### Inferences
- **What to reuse.** TheTransitClock is the most complete open-source real-time stack, but it is Java and has its own Kalman logic. For us it is more useful as a *design reference* (direction-matched previous vehicle, cut-off age, dwell/travel split, 100-m matching tolerance) than as a drop-in.
- **Conformal intervals.** The CQR authors' reference code and general conformal libraries (e.g. MAPIE) can wrap LightGBM quantile models. These are from background knowledge, not verified this session; check repository and API before relying on them.
- **One-week plan (inference; gains speculative, each item probably ≤0.2–0.6 pp MedAPE, bias largely removable):**
  - **Day 1.** Stop-event QA and ride-level error diagnostics: bias by number of links, hour, route and day; how much of the mean bias comes from the top 5% of errors.
  - **Days 1–2.** Ride-level second-stage LightGBM (L1 for P50, plus quantile models), and grouped smearing or a log-link objective for a separate mean output.
  - **Days 2–3.** Real-time features: per-link latest traversal ratio with its age, decayed ratios at several half-lives, horizon-to-link, adjacent-link and corridor ratios, buses currently on a link, a peak-state flag, observation counts.
  - **Day 4.** CQR with per-cell (Mondrian) calibration on the last pre-test week; report coverage and interval width; publish the P90 − P50 reliability buffer.
  - **Day 5.** Calendar and weather flags (check 2026 festival dates and rain days), same-weekday-last-week ratio, dwell/running split.
  - **Optional stretch (Colab).** Per-route seq2seq or ConvLSTM, Delhi-399 style, on the busiest routes, stacked into LightGBM.

### Gaps
- No public code was found for BusTr, the TCS Delhi seq2seq, or the Copenhagen ConvLSTM / deep quantile models.
- Whether the Movia and IIIT-Delhi datasets are publicly downloadable was not confirmed.
- MAPIE / CQR code links were not verified this session.
