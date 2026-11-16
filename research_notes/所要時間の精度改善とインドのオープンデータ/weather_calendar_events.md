# External day/hour covariates for Delhi bus travel times, Oct–Nov 2026 (weather, AQ/GRAP, holidays, events)

Research date: 2026-11-17. Weekday check: 1 Oct 2026 = Thursday, so 18 Oct = Sun, 20 Oct = Tue, 29 Oct = Thu, 2 Nov = Mon, 8 Nov = Sun, 16 Nov = Mon, 24 Nov = Tue.
Labels: **[VERIFIED]** = read from the fetched source this session. **[API-PULLED]** = pulled from the open API this session. **[BACKGROUND, not re-verified]** = from general knowledge, so check it before relying on it. **[INFERRED]** = my reasoning.

## Q1. Weather: sources and what happened in Delhi in Oct 2026

### Takeaway
Two rain events in October 2026 matter. The first was on Sun 11 → Mon 12 Oct (training period): 41.6 mm at Safdarjung, with waterlogging during the Monday morning rush. The second was on Thu 29 → Fri 30 Oct (test period): 61.4 mm at Safdarjung. The rest of October and 1–15 Nov were essentially dry. Open-Meteo's free archive picks up the 29–30 Oct event well, but it **misses or shifts the 11–12 Oct event** (it puts about 19 mm on 15 Oct instead). Station (IMD) data or news reports should therefore override reanalysis for event flags.

### Cited Findings
- **11–12 Oct 2026 [VERIFIED]:** in the 24 h ending 08:30 IST Mon 12 Oct: Ridge 49 mm, Safdarjung 41.6 mm, Lodhi Road 41.4 mm, Ayanagar 39 mm, Palam 31 mm. Called "wettest October day in four years" (previous: 9 Oct 2022, ~74 mm). Safdarjung min 18.7 °C. Waterlogging at Sainik Farm and Mahipalpur "disrupted traffic during the morning rush". Delhi Traffic Police diverted traffic on Ansari Road (Dharampura–Iron Bridge) — [DD India/PTI, 12 Oct 2026](https://ddindia.co.in/2026/10/delhi-records-wettest-october-day-in-four-years-minimum-temperature-drops-to-18-7-deg-c/)
- **29–30 Oct 2026 [VERIFIED]:** Safdarjung 61.4 mm and Palam 43.1 mm in the 24 h ending 08:30 IST 30 Oct. Safdarjung max 25.4 °C (5.6 °C below normal). The article reports no specific traffic incidents — [Skymet, 30 Oct 2026](https://www.skymetweather.com/content/weather-news-and-analysis/delhi-weather-october-31-safdarjung-records-614-mm-rain-dry-weekend-ahead-as-temperatures-rise)
- Rain on 30 Oct cleaned the air: AQI was 60 on 30 Oct, "cleanest October day in four years" — [OneIndia, 2 Nov 2026](https://www.oneindia.com/new-delhi/just-two-weeks-after-grap-stage-i-stage-ii-imposed-across-delhi-ncr-as-aqi-hits-374-check-whats-c-8248871.html)
- **Open-Meteo Historical Weather API (ERA5-based archive), point 28.58N 77.20E, daily precip [API-PULLED 2026-11-17]:** 15 Oct 18.9 mm, 29 Oct 46.5 mm, 30 Oct 50.3 mm. Every other day from 1 Oct to 15 Nov was ≤1.5 mm, including only 0.5 / 1.3 mm on 11 / 12 Oct. Daily max temperature: 33–35.7 °C (1–10 Oct), ~29–31 °C (16–28 Oct), 21.2 °C on 30 Oct, ~27–29.5 °C (1–15 Nov). Endpoint: `https://archive-api.open-meteo.com/v1/archive?latitude=28.58&longitude=77.2&start_date=2026-10-01&end_date=2026-11-15&daily=precipitation_sum,...&timezone=Asia/Kolkata` (no key needed) — [Open-Meteo archive API](https://archive-api.open-meteo.com/v1/archive?latitude=28.58&longitude=77.2&start_date=2026-10-01&end_date=2026-11-15&daily=precipitation_sum&timezone=Asia%2FKolkata)
- **Open-Meteo Historical Forecast API (best_match model) [API-PULLED]:** the same pattern, rain on 15, 29 and 30 Oct with WMO code 95 (thunderstorm) on 11, 15 and 29 Oct. Minimum hourly visibility over 10–31 Oct was 140 m (this is a model value, not observed) — [historical-forecast-api.open-meteo.com](https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=28.58&longitude=77.2&start_date=2026-10-10&end_date=2026-10-31&daily=precipitation_sum&timezone=Asia%2FKolkata)
- IMD New Delhi regional centre publishes an observational table PDF (Safdarjung, Palam, Lodhi Rd, Ridge, Ayanagar etc.) — [mausam.imd.gov.in/newdelhi Observational_table.pdf](https://mausam.imd.gov.in/newdelhi/mcdata/Observational_table.pdf) (URL found in search; content not fetched)
- Mid-October forecasts (Skymet, 14–20 Oct): "pleasant", highs ~33 °C, mostly dry — [Skymet](https://skymetweather.com/content/monsoon-update/rain-likely-in-delhi-ncr-again-fresh-spells-from-october-15)

### Source inventory (weather)
| Source | Publisher | Fields | Resolution | Oct 2026 available? | Licence/access |
|---|---|---|---|---|---|
| Open-Meteo Historical Weather API (archive-api) | Open-Meteo (ERA5/ERA5-Land/ECMWF IFS) | precipitation, rain, temp, RH, wind, cloud, weather_code | hourly/daily, ~9–25 km grid | **Yes [API-PULLED]** | Free, no key. Licence CC BY 4.0, free for non-commercial use [BACKGROUND, not re-verified] |
| Open-Meteo Historical Forecast API | Open-Meteo (archived high-res model runs) | as above + **visibility** | hourly, ~2–11 km | **Yes [API-PULLED]** | same |
| ERA5 (CDS) | ECMWF/Copernicus | full reanalysis | hourly, 0.25° | ~5-day latency (ERA5T) [BACKGROUND] | Free, **needs an account** (not created, per the constraints) |
| NASA POWER | NASA LaRC | precip, T2M, RH, wind | hourly/daily, ~0.5° | Probably; near-real-time lag of a few days [BACKGROUND, not verified] | Free REST API, no key |
| IMD station data (Safdarjung 42182, Palam 42181) | IMD | hourly/3-hourly METAR/synop, 24h rain to 08:30 IST | station | Daily bulletins/PDFs on mausam.imd.gov.in; the bulk archive is on dsp.imdpune.gov.in (registration/paid for station data) [BACKGROUND] | Scraping of daily PDFs/bulletins; METAR for VIDP (Palam airport) is available from public aviation weather sites [BACKGROUND] |
| News (PTI/DD India, Skymet) | — | event-level rain amounts, waterlogging hotspots | event | Yes [VERIFIED] | Manual |

### Inferences
- [INFERRED] Use a **"heavy rain day" flag from station or news data**: 12 Oct (Mon, AM peak hit), 29 Oct afternoon/evening and 30 Oct (test period). Add an hourly precipitation feature from Open-Meteo for the test week. Do not trust Open-Meteo for the 11–12 Oct event: it has 1.3 mm where stations recorded 31–49 mm, and it shows 18.9 mm on 15 Oct, which no news report I found confirms. 15 Oct may be a false positive or a real event that went unreported.
- [INFERRED] The rain on 29–30 Oct falls on Thu–Fri of the **test week**. If the team's model under-predicts travel times on those days, rain is the likely cause. Karva Chauth (29 Oct, evening) coincides with it, so the two effects are confounded.
- [INFERRED] Fog: Oct–mid-Nov 2026 shows no reported dense-fog episodes in what I found. Fog is typically a Dec–Jan issue for Delhi, so it matters little for Nov live predictions. The model's 140 m visibility minimum is unverified and may be haze or smog.

### Gaps
- No full-month Safdarjung October 2026 total was found. Hourly timing of the 11–12 Oct and 29–30 Oct rain (which hours) is not confirmed. VIDP METAR archive could resolve it (not fetched).
- Not established whether 15 Oct had real rain in Delhi.
- No observed visibility or fog data was checked for Nov 2026.

## Q2. Air quality and GRAP: dates in Oct–Nov 2026 and traffic-relevant restrictions

### Takeaway
GRAP **Stage I from 21 Oct 2026** (training/test boundary), **Stage II from Mon 2 Nov**, and **Stage III from Fri 6 Nov** (two days before Diwali). AQI hit 483 ("severe") on the morning of 8 Nov. Stage III bans BS-III petrol and BS-IV diesel four-wheelers and moves primary schools to hybrid classes. Both cut private and school traffic. Stage II raises parking fees and increases CNG/e-bus and Metro frequency. Whether Stage III or IV was still in force after 8 Nov was not confirmed.

### Cited Findings
- **Stage I invoked 21 Oct 2026** by the CAQM GRAP sub-committee, "all actions under Stage-I … with immediate effect across the entire NCR". Delhi AQI 244 at 2 pm (Poor) — [News On AIR, 21 Oct 2026](https://newsonair.gov.in/caqm-invokes-stage-i-grap-across-ncr-as-delhi-aqi-enters-poor-category/)
- AQI was 179 on 20 Oct (Dussehra) and about 244 on 21 Oct. A revised GRAP schedule approved in late Sept 2026 reportedly moved some diesel-generator and **bus-entry** measures from Stage II to Stage I (from the search-result summary; the primary source was not opened) — [Free Press Journal](https://www.freepressjournal.in/india/delhi-ncr-air-quality-slips-to-poor-after-dussehra-caqm-imposes-grap-stage-i); [Business Today, 22 Oct 2026](https://www.businesstoday.in/india/story/delhi-aqi-pollution-air-grap-restrictions-construction-vehicles-emmissions-562944-2026-10-22)
- **Stage II invoked Mon 2 Nov 2026** with immediate effect. AQI: 31 Oct 117, 1 Nov 261, 2 Nov 307 (7:05 am) → 324 (4 pm). Measures: higher parking fees to discourage private vehicles; more CNG/electric buses and more Metro/RRTS services; traffic police at congested junctions; stricter PUC checks; coal/firewood ban; DG-set limits — [OneIndia, 2 Nov 2026](https://www.oneindia.com/new-delhi/just-two-weeks-after-grap-stage-i-stage-ii-imposed-across-delhi-ncr-as-aqi-hits-374-check-whats-c-8248871.html); [The Week/PTI, 2 Nov 2026](https://www.theweek.in/wire-updates/national/2026/11/02/grap-2-curbs-imposed-in-delhi-ncr-as-air-quality-slips-into-very-poor-category0.html)
- **Stage III invoked Fri [6 Nov] 2026**, "two days before Diwali". AQI 364 at 8 am Sat 7 Nov and **483 at 8:10 am Sun 8 Nov**. Measures: BS-III petrol and BS-IV diesel four-wheelers banned in Delhi and designated NCR districts; tighter limits on older LGV/MGV and on outside diesel commercial vehicles; non-essential construction (including road construction) suspended; **primary students to hybrid learning** — [NewKerala/IANS, 8 Nov 2026](https://www.newkerala.com/news/a/delhis-air-quality-slips-into-severe-category-overall-706.htm)
- AQI bands: Stage I 201–300, II 301–400, III 401–450, IV >450. Stages are cumulative — [Business Standard explainer](https://www.business-standard.com/india-news/grap-stage-iii-delhi-air-pollution-aqi-vehicle-entry-construction-restricted-125111100562_1.html) (2025 article; bands unchanged per search summary)
- Precedent: in the 2025–26 season, Stage II ran from 19 Oct 2025 and was revoked on 18 Feb 2026 — [CAQM PR 18-02-2026](https://caqm.nic.in/WriteReadData/LINKS/CAQM%20PR%2018022026%20(GRAP%20Stage-II%20Revocation)2a14a91a-003a-4e05-8b7c-e0f2a3c8d3a0.pdf)

### Source inventory (AQ)
| Source | Fields | Resolution | Access |
|---|---|---|---|
| CPCB CCR portal (airquality.cpcb.gov.in/ccr) | PM2.5, PM10, NO2, CO, O3, AQI, met per CAAQMS station (~40 in Delhi) | 15-min/hourly | Free web UI with CSV/XLS export, CAPTCHA-gated. Scraping is discouraged, and CAPTCHA bypass is not allowed [BACKGROUND] |
| CPCB daily AQI bulletin (4 pm city AQI) | city AQI | daily | Free PDF archive on cpcb.nic.in [BACKGROUND] |
| data.gov.in "Real time Air Quality Index from various locations" | pollutant avg/min/max per station | hourly, current snapshot only | Free API, **requires an API key (account)** under the Govt Open Data Licence – India [BACKGROUND]. Historical Oct data is not available via the snapshot API |
| OpenAQ v3 | CPCB station re-publication | hourly | Free API key [BACKGROUND] |
| Open-Meteo Air Quality API | PM2.5/PM10/AQI (CAMS model) | hourly, ~11–40 km | Free, no key [BACKGROUND, not pulled] |
| CAQM orders/press releases (caqm.nic.in) | GRAP stage invocation/revocation | event dates | Free PDFs [VERIFIED URL pattern] |

### Inferences
- [INFERRED] GRAP stage is a **day-level step covariate**: Stage 0 for 1–20 Oct, Stage I from 21 Oct, Stage II from 2 Nov, Stage III from 6 Nov. The training period (1–24 Oct) holds only 4 Stage-I days, so the effect cannot be learned from the training data and must be treated as a prior or ignored. Stage III's vehicle ban and hybrid primary schooling should reduce private traffic, which may raise bus speeds slightly. The Stage II parking-fee hike and extra buses push in a similar direction. No Indian GPS study quantifies this.
- [INFERRED] The ban on outside diesel buses and commercial vehicles may change interstate traffic on ring roads near ISBTs.

### Gaps
- Not confirmed whether Stage IV was invoked after 8 Nov 2026, or whether Stage III was revoked after Diwali. The live Nov prediction period needs this. Check the caqm.nic.in "GRAP orders" page.
- The content of the Sept 2026 GRAP revision (bus-entry measure moved to Stage I) was not read from the primary source.
- No 2026 school-closure (full, not hybrid) order was found. No odd-even scheme was found for 2026.

## Q3. Holidays and festivals, Oct–Nov 2026 (Delhi)

### Takeaway
The team's holiday list (only 2 Oct) is missing **20 Oct Dussehra (gazetted, Tue)**, which they found already. Other missing dates: **8 Nov Diwali (Sun)**, **16 Nov (Mon), a special Delhi holiday for Chhath**, and **24 Nov Guru Nanak Jayanti (Tue, gazetted)**. Restricted or "soft" days: 29 Oct Karva Chauth (evening), 7 Nov Choti Diwali/Sat shopping, 9–11 Nov Govardhan/Bhai Dooj, and 13–16 Nov Chhath (ghat traffic on the evening of 15 Nov and the dawn of 16 Nov).

### Cited Findings
- Delhi Gazette Extraordinary No. 378 (4 Dec 2025) lists the 2026 NCT holidays. Diwali is Sun 8 Nov (Kartika 17) — [Delhi Gazette PDF via advocategandhi.com](https://advocategandhi.com/wp-content/uploads/2025/12/Delhi-Gazette-Notification-Part-IV-Extraordinary-No.-378-dated-4-December-2025.pdf); [advocategandhi summary](https://advocategandhi.com/official-2026-holiday-schedule-released-for-delhi-under-ni-act/)
- Dussehra 20 Oct 2026, Diwali 8 Nov, Guru Nanak's Birthday 24 Nov are also on the central government (DoPT, OM 3 Jul 2025) list. On 24 Nov, Guru Teg Bahadur Martyrdom Day is a restricted holiday — [gconnect DoPT list](https://www.gconnect.in/news/holidays-to-be-observed-in-central-government-offices-during-the-year-2026.html); [Keka Delhi list](https://www.keka.com/compliance/public-holiday/delhi)
- Gandhi Jayanti 2 Oct is gazetted (team already has it). Note: aggregators disagree on the count (17 vs 18 gazetted) because DoPT and NCT lists differ — [search summary of hono.ai / keka](https://www.hono.ai/holiday/delhi-holiday-2026)
- **Karva Chauth Thu 29 Oct 2026** — [calendarlabs](https://calendarlabs.com/holidays/india/karva-chauth.php)
- Govardhan Puja: 9 Nov (most sources) vs 10 Nov (Drik Panchang). Bhai Dooj: 11 Nov (most) vs 10 Nov (Hindutone). These conflict, so verify with [Drik Panchang 2026](https://www.drikpanchang.com/calendars/indian/indiancalendar.html?year=2026)
- **Chhath 13–16 Nov 2026**. Delhi GAD notification of 9 Nov 2026 declared **Mon 16 Nov a public holiday** for GNCTD offices, schools, colleges, autonomous bodies and PSUs. 16 Nov is the concluding day (dawn arghya) — [Careers360, 11 Nov 2026](https://news.careers360.com/chhath-puja-2026-delhi-school-holiday-november-16-bihar-schools-closed-till-november-17/amp). Keka's pre-season list put Chhath at 15 Nov (Sun) as restricted — [Keka](https://www.keka.com/compliance/public-holiday/delhi)
- Press reported a long school holiday stretch in Nov 2026 around Diwali (headline mentions "14 days" across states; Delhi-specific dates not verified) — [news24online](https://news24online.com/trending/school-holiday-november-2026-schools-to-remain-closed-in-delhi-noida-gurugram-up-maharashtra-for-14-days-due-to-diwali-and-other-festivals-check-full-state-wise-list/949294/)

### Source inventory (calendar)
- Delhi GAD gazette (delhi.gov.in / egazette) PDF, scraped manually. DoPT OM PDF. Python `holidays` package (country IN, subdiv DL) [BACKGROUND; check its coverage of lunar festivals for 2026]. Drik Panchang for tithi-based festivals (scrape; terms restrict reuse [BACKGROUND]). timeanddate.com India holidays (manual view).

### Inferences
- [INFERRED] Suggested day-type encoding: `holiday_gazetted` = {2 Oct, 20 Oct, 8 Nov, 16 Nov (special), 24 Nov}; `festival_eve` = {19 Oct Mon (pre-Dussehra shopping; Ravan Dahan is on the evening of the 20th), 7 Nov Sat (Choti Diwali, heavy evening market traffic)}; `festival_evening` = {29 Oct Karva Chauth, 15 Nov Chhath Sandhya Arghya}; `post_diwali_week` = 9–13 Nov (reduced demand, many leaves, school break).
- [INFERRED] The test window 25–31 Oct contains no gazetted holiday. Its special days are 29 Oct (Karva Chauth plus heavy rain) and 30 Oct (rain).

### Gaps
- No Delhi University or CBSE exam calendar for Oct–Nov 2026 was found. The exact Delhi school Diwali-break dates are not verified.
- Restricted-holiday office absence rates are unknown.

## Q4. Events (marathons, cricket, rallies) and Delhi Traffic Police advisories

### Takeaway
One major confirmed event lies in the training window: **Vedanta Delhi Half Marathon, Sun 18 Oct 2026**, at Jawaharlal Nehru Stadium, 41,000+ runners, with road closures on the morning of race day. No 2026 Arun Jaitley Stadium cricket fixture, election or major rally in Oct–Nov 2026 was found in this pass. Delhi Traffic Police advisories (on X @dtptraffic and the website) are the best event proxy, but they need manual or scraped collection.

### Cited Findings
- Delhi Half Marathon 2026 scheduled for **18 Oct 2026** — [Outlook India](https://www.outlookindia.com/sports/others/delhi-half-marathon-2026-scheduled-for-october-18-registration-date-announced); [Procam race page](https://vedantadelhihalfmarathon.procam.in/race-categories/half-marathon-elite/information); record 41,000+ participants — [NewKerala](https://www.newkerala.com/news/a/record-41000-runners-set-participate-delhi-half-marathon-169.htm)
- Precedent advisory (2024 edition, 20 Oct 2024): traffic in South and Central Delhi was regulated for about 6 h until ~11 am, with cross-traffic at junctions allowed as runner density permitted — [India TV, 2024](https://www.indiatvnews.com/delhi/delhi-traffic-advisory-ahead-of-half-marathon-on-october-20-guidelines-for-commuters-routes-to-avoid-latest-updates-2024-10-17-957640)
- The 12 Oct 2026 rain led to a DTP diversion on Ansari Road, announced on X. DTP posts serve as an incident/event feed — [DD India](https://ddindia.co.in/2026/10/delhi-records-wettest-october-day-in-four-years-minimum-temperature-drops-to-18-7-deg-c/)

### Inferences
- [INFERRED] Flag 18 Oct, 05:00–11:00, for routes crossing Lodhi Rd / JLN / India Gate / Central Delhi as "event-affected". Sunday morning demand is low anyway, so the effect is route-specific rather than network-wide.
- [INFERRED] Dussehra Ramlila grounds (Ramlila Maidan, Red Fort lawns, etc.) cause evening congestion for ~10 days before 20 Oct. This is plausible but has no 2026 advisory evidence.

### Gaps
- No 2026 DTP advisory text for the half marathon was fetched. Cricket at Arun Jaitley Stadium, rallies and protests in Oct–Nov 2026 were not searched in depth, and I found no open structured event calendar for Delhi. DTP's advisories page (traffic.delhipolice.gov.in) and the X account would need scraping.

## Q5. Indian evidence on rain, festivals and pollution restrictions vs bus speed and headways

### Takeaway
Quantitative Indian evidence is thin. A Delhi study (Chakrabarty et al., 2014, cited second-hand) reports about a 10% speed drop under rainfall plus more idling. A Bengaluru BMTC survey reports bus-stop waiting times rising about 45% in extreme rain. No Indian GPS study of festivals or GRAP effects on bus speed was found.

### Cited Findings
- WCTR 2019 (Mumbai) paper: the only prior Indian rainfall–traffic study it found was in Delhi, reporting "a drop in speed by 10% due to rainfall" and increased idling time (Chakrabarty et al. 2014; original not accessed). The paper itself measured travel time and fuel on two Greater Mumbai routes, rain vs no-rain days, by IMD intensity class — [WCTR2019 Mumbai 526](https://www.wctrs-society.com/wp-content/uploads/abstracts/mumbai/WCTR2019_Mumbai_526.pdf)
- Bengaluru BMTC passenger survey (NITK, 2024): waiting time at stops +45%, and 70% of respondents saw longer travel times during extreme rainfall (survey, not GPS) — [NITK IDR](https://idr.nitk.ac.in/handle/123456789/28946)
- Bengaluru commute times up 62% in a rainy August (media / location-data claim) — [The News Minute](https://www.thenewsminute.com/article/bengaluru-rains-pushed-average-commute-time-62-august-167433)
- IISc simulation: average daily vehicle speed 27 → 13 km/h under a 2050 flooding scenario (model, not observed) — [Citizen Matters](https://citizenmatters.in/bengaluru-floods-traffic-speed-trip-cancellation-policy-solutions/)
- Non-Indian GPS analogue: Yangzhou bus GPS + rainfall remote sensing found that rainstorms significantly reduce bus speed and increase travel time — [MDPI IJGI 13(2):50](https://mdpi.com/2220-9964/13/2/50)

### Inferences
- [INFERRED] Use a prior of about 10% lower speed on rain hours, larger with waterlogging and peak-hour overlap (12 Oct AM). Headway and waiting time are likely more sensitive than in-vehicle time (BMTC +45% wait).

### Gaps
- Chakrabarty et al. 2014 (Delhi) was not retrieved, so its exact method and numbers are unverified. No Indian quantitative study was found on festival days (Diwali or Dussehra) or on GRAP/odd-even effects on bus speeds. Odd-even 2016 studies (CSE, TERI, IIT-D) exist per background knowledge but were not retrieved this session.
