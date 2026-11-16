# Digital ways to pay for or get a Delhi city-bus ticket (DTC and ex-cluster/DIMTS buses), 2024–2026: official and app-level flows, and what each channel records

How to read these notes:

- **Researched:** 16 Nov 2026.
- **Fetched vs. search summary:** Items marked "(search summary)" come from a search engine's summary, because the page itself was blocked (HTTP 402/403) or could not be rendered. Treat them as lower confidence. Everything else was fetched and read.
- **Local data checks:** Items marked "(local data check)" are counts I computed on 16 Nov 2026 from the hackathon file [October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv): 2,559,899 rows, 1–31 Oct 2026. They are not published facts.
- **Background:** Facts already in [delhi_ops.md §4](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/research_notes/所要時間と混雑推定の精度改善策/delhi_ops.md) and [etm_ticket_india.md](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/research_notes/バス車内混雑推定の事例と精度/etm_ticket_india.md) are reused only where needed, and say so.
- **Dates:** Twitter/X post dates were decoded from the post IDs.

## 1. One Delhi and the other app flows: purchase steps, "scan the bus QR" vs. "choose route/stops", when the vehicle number is captured, before vs. after boarding, validity, conductor checks

### Takeaway

Delhi's app ticketing has two flow families.

- **(a) Scan the bus.** The rider scans the QR sticker inside the bus, then picks a fare or destination and pays. The scan ties the ticket to that physical bus.
- **(b) Choose route and stops.** The rider picks route, start stop, end stop and AC/non-AC, then pays, with no bus scan. Apps with this flow include Chartr 2.0 ("Route-based ticketing", April 2026) and WhatsApp.

In 2020–2024 the documented app flows (Chartr, One Delhi, Tummoc) all involved scanning the bus QR or typing the bus number, and Tummoc explicitly did not allow pre-booking. WhatsApp (April 2024) was the exception: same-day tickets with no documented bus scan. From 2025–26, official messaging says "book anytime, anywhere".

One Delhi (Transport Dept; developer DIMTS) is still the official app. Its latest Android build is 2.1.3 (18 Oct 2026), and no rebranded successor was found. DTC also promotes Chalo (from Sept 2025) and lists ten channels in total.

Validity is short:

- Same calendar day (Tummoc).
- 30 minutes after on-board activation (Tummoc).
- "Time-bound" (Chartr).
- One Delhi needs a separate "validate" step, according to user reports.

Conductors and checkers verify by viewing or scanning the passenger's QR. ₹200 penalties are reported for unvalidated or invalid tickets.

### Cited Findings

**One Delhi (official Transport Department app)**
- iOS listing details — [App Store](https://apps.apple.com/in/app/one-delhi/id1641749010):
  - Developer: "Delhi Integrated Multi Modal Transit System Ltd". Copyright: Government of Delhi, Transport Department.
  - Description: "Buy e-tickets for all the buses and metros".
  - Version history:

    | Version | Date | Notes |
    |---|---|---|
    | 2.15 | 23 Jul 2025 | "Ticketing updates" |
    | 2.16 | 24 Aug 2025 | "Added Bus Passes" |
    | 2.18 | 6 Nov 2025 | Privacy policy, refund policy and terms-of-service pages |
    | 2.20 | 6 Jan [2026] | Bug fixes |
    | 2.21 | 9 Jun [2026] | Bug fixes |

  - Rating: 1.7/5 from 225 ratings.
  - A July 2024 review says the app fails to get the current route for a bus number.
- Android builds: 2.0.1 (28 Apr 2026), 2.0.2 (27 Jun 2026), 2.1.2 (21 Sep 2026) and 2.1.3 (18 Oct 2026). The description covers DTC and cluster buses plus metro, "Buy bus and metro QR tickets directly from the app", and a 10% discount on bus fares. — [APKPure mirror of the Play listing](https://apkpure.net/one-delhi/com.delhitransport.onedelhi)
- 2021 flow: "Passengers can book pink tickets and passes using this app by just scanning the QR Code inside the bus", then select the ticket fare or the source and destination stops. Booking through the app gives a 10% discount. — [Curly Tales, 19 Jul 2021](https://curlytales.com/delhi-book-bus-tickets-via-one-delhi-application-heres-how/amp/); [HT via PressReader, 18 Jul 2021](https://www.pressreader.com/india/hindustan-times-delhi/20210718/281651078120594)
- The DDC page says "the scan for buying a ticket will be available at each and every seat" (search summary; the page refused connection). — [DDC One Delhi](https://ddc.delhi.gov.in/our-work/6/one-delhi-app)
- Validation step:
  - A Play Store review says the user "purchased a bus ticket and paid for it, but … forgot to validate it, after which the ticket became invalid". A ticket checker then fined them ₹200 (search summary). — [Google Play listing](https://play.google.com/store/apps/details?id=com.delhitransport.onedelhi&hl=en_IN)
  - A consumer complaint reports a One Delhi ticket shown as invalid during a check, and a ₹200 on-the-spot penalty despite proof of payment (search summary). — [consumercomplaints.in](https://www.consumercomplaints.in/delhi-transport-corporation-dtc-subject-request-for-refund-of-200-penalty-due-to-app-error-on-one-delhi-app-c3535068)
- One Delhi was the first ONDC buyer app for DTC and DIMTS bus tickets, paid via UPI, from 2 Sep 2024. — [Inc42, 2 Sep 2024](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc/); [ONDC on X, 2 Sep 2024](https://x.com/ONDC_Official/status/1830615652437991612)
- January 2024: about 1.5 lakh DTC QR tickets a day and about 3 lakh active users. This predates ONDC (reused from delhi_ops.md). One Delhi also issued free pink tickets at the time, so the figure probably includes them; that is my inference, not stated in the source. — [Business Today, 6 Jan 2024](https://www.businesstoday.in/technology/news/story/delhi-metro-introduces-seamless-travel-experience-with-one-delhi-app-integration-412136-2024-01-06)

**Chartr (IIIT-Delhi spin-off; DTC's original QR-ticketing partner)**
- The 2020 trial on route 473 had two flows. Both ended with a scan of the bus QR. — [Okhla Times, 5 Aug 2020](https://theokhlatimes.com/e-ticketing-dtc-buses/)
  - "BY FARE": scan the bus QR code → "Buy New Ticket" → payment.
  - "By Destination": select bus route and source stop → destination stop → Buy → scan the bus QR code → payment.
- Phase-II pilot: 29 buses between Anand Vihar and Mehrauli, after a cluster route 473 pilot. Steps: choose the fare or destination, scan the on-board QR, pay. — [NFCW, 18 Sep 2020](https://www.nfcw.com/2020/09/18/368066/delhi-transport-corporation-trials-contactless-bus-ticketing/)
- February 2021: QR codes were pasted on the back of each seat in almost all DTC buses (search summary). — [HT via PressReader, 25 Feb 2021](https://www.pressreader.com/india/hindustan-times-st-noida/20210225/281809991618212)
- The new Chartr app's listing summarises the flow as "Scan the QR code → Enter destination → Pay → Get your ticket instantly". — [App Store, Chartr (new app)](https://apps.apple.com/us/app/-/id6747386059)

  | Version | Date | Notes |
  |---|---|---|
  | 1.0 | 12 Aug 2025 | First release |
  | 1.1.0 | 31 Aug 2025 | "Added passes" |
  | 1.4.1 | 10 Dec 2025 | DEVI buses shown in purple; route input shows all options |
  | 1.5.1 | 22 Apr [2026] | "Route-based ticketing", multi-city, YeBus |

- Chartr's product page describes the route flow: "Pick your route, enter your start and end stop, choose AC or Non-AC, and pay via Chartr Wallet". Other details on the page:
  - The QR ticket is generated instantly, and "conductors scan to verify".
  - Payment is by wallet or UPI. The wallet holds at most ₹500.
  - There is a flat 10% discount on digital bus tickets.
  - A screenshot shows a ₹9.25 Route 605 ticket with the coupon "WELCOME10".

  — [Chartr app page](https://www.chartr.in/products/chartr-app/)
- Chartr's AFCS page describes its tickets and verification. Delhi is listed for "digital tickets and passes". — [Chartr AFCS](https://chartr.in/products/afcs/)
  - Mobile QR tickets are "time-bound, prevents reuse".
  - "Conductors and inspectors scan the QR to verify."
  - "Same QR scanned in different buses at impossible time intervals → immediate fraud alert."

**Tummoc (third-party; on DTC's official channel list)**
- FAQ, 20 Jan 2024 — [Tummoc FAQ](https://blog.tummoc.com/dtc-ticket-and-pass-faqs/):
  - "No, you cannot pre-book DTC tickets and passes. You must board the bus to book a ticket."
  - "By default, tickets are valid only for the same calendar day as the date of purchase."
  - Riders validate by scanning "the QR pasted on the bus". The app then shows "the last validated time, bus number and route number".
  - Riders show the digital ticket or QR "to the conductor or line checker".
  - "You can book a maximum of three tickets at a time."
- Validation guide, 10 Jun 2024 — [Tummoc validation guide](https://blog.tummoc.com/?p=2344):
  - Once on the bus, the rider activates the ticket: "Your ticket will be active for 30 minutes after this".
  - "Validate Ticket" works with either the bus QR code or the bus number. If no Tummoc QR is posted in the bus, the rider types the bus number.
  - Passes are validated the same way, by bus number or bus QR.

**WhatsApp (DTC-listed number +91 8744073223)**
- Flow, April 2024 (search summary):
  - Start by sending "Hi" or scanning a QR code, then choose a language and "Book Ticket".
  - Choose AC or non-AC and the number of tickets.
  - Pay via WhatsApp Pay or any UPI app. The ticket arrives in the chat.
  - Single-journey QR tickets cover DTC and DIMTS routes.
  - Bookings are for the current day only, with no advance booking.
  - Up to 6 tickets per booking, and a small convenience fee applies.
  - The summaries describe no stop-selection or bus-scan step.

  — [Zeebiz](https://www.zeebiz.com/india/news-dtc-bus-ticket-online-booking-on-whatsapp-how-to-book-delhi-ncr-latest-update-283627); [NewsBytes](https://www.newsbytesapp.com/news/science/book-dtc-bus-tickets-on-whatsapp-using-these-steps/story); [Business Today, 11 Apr 2024](https://www.businesstoday.in/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11)

**Chalo (DTC-promoted from Sept 2025)**
- 23 Sep 2025: the Chief Minister launched the "Chalo App on ONDC" alongside the new AFCS, with a 10% discount "to encourage adoption". — [Impressive Times, 23 Sep 2025](https://impressivetimes.com/latest/delhi-inter-state-ac-bus-service-2025-afcs-chalo-app/)
- "DTC has integrated Chalo app", which lets passengers book tickets from anywhere and track buses, with 10% off app bookings. — [ETV Bharat, 5 Oct 2025](https://www.etvbharat.com/en/!state/dtc-cashless-ticketing-system-now-implemented-on-all-delhi-buses-enn25100503259)
- No public step-by-step Chalo flow for Delhi was found.

**DTC's official channel list**
- The DTC page is headed "Skip the queue. Book your ride, anytime, anywhere!". It lists ten channels: One Delhi, DMRC, Chartr, Tummoc, WhatsApp, Chalo, Rapido, Redbus (link `m6pe.app.link/DTCQR`), Tocxi and Katch Go. The page is undated (read Nov 2026). — [DTC Digital Ticketing](https://dtc.delhi.gov.in/dtc-digital-ticket/)
- DTC post, 14 Jan 2025: "Scan QR codes on DTC buses via One Delhi, Chartr, Tummoc, or WhatsApp for instant tickets … 10% discount". — [DTC on X](https://x.com/dtchq_delhi/status/1879098686447513733)

**Dataset patterns that bear on the flows (local data checks)**
- Share of rows with a blank vehicle_number, by day:
  - Normal days: 0.47–0.52.
  - 17 Oct: 0.350. 18 Oct: 0.148. 19 Oct: 0.382. 20 Oct: 0.437.
- On 13–16 Oct each group was about 48–52k tickets a day. From 17 Oct the blank group collapsed while the with-vehicle group held:

  | Date | With vehicle | Blank |
  |---|---:|---:|
  | 17 Oct (Sat) | 44,746 | 24,090 |
  | 18 Oct (Sun) | 29,829 | 5,180 |
  | 19 Oct (Mon) | 46,195 | 28,606 |
  | 20 Oct (Tue) | 27,806 | 21,569 |

  By 21–22 Oct both were back to about 46–49k. — (local data check) [October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv)
- Blank share by purchase hour ranges from 0.40 (02h) to 0.51 (17–18h). Across the 359 routes with ≥ 2,000 tickets, the median blank share is 0.505 (p10 0.375, p90 0.626, min 0.238, max 0.963). — (local data check)
- Rows with and without a vehicle number look alike. — (local data check)
  - Share of rows at each per-passenger fare: ₹9 — 39.2% (with vehicle) vs 41.0% (blank); ₹13.5 — 31.7% vs 31.9%.
  - is_ac = True: 78.4% vs 82.6%.
  - passenger_count > 1: 6.8% vs 6.3%.
- passenger_count is 1 on 2,392,082 rows, 2 on 141,930 and 3 on 25,886. Only 1 row has 6. — (local data check)

### Inferences

**When the vehicle number is captured**
- The bus registration enters an app ticket only when the rider scans the bus's QR sticker (or types the bus number, as Tummoc allows). This can happen at purchase (scan-first flows) or at a later on-board validation step (One Delhi and Tummoc style). Route/stop-only flows (Chartr route-based ticketing, WhatsApp) cannot know the vehicle unless a later validation adds it.
- This matches the dataset. For tickets with a vehicle number, the median purchase is 0.8 min after the bus passed the boarding stop, which fits scan-after-boarding.

**Blank vehicle numbers mark a channel, not random missingness**
- From 17–19 Oct the blank group fell sharply while the with-vehicle group stayed near normal. To estimate the expected blank count, I multiplied that day's with-vehicle count by the usual blank : with-vehicle ratio for the same weekday.

  | Date | Blank rows | Expected | Share of expected |
  |---|---:|---:|---:|
  | 17 Oct (Sat) | 24,090 | ≈ 40.6k | ~59% |
  | 18 Oct (Sun) | 5,180 | ≈ 26.5k | ~20% |
  | 19 Oct (Mon) | 28,606 | ≈ 48k | ~59% |

  That looks like an outage or change in the specific app(s) or flow(s) that produce blank rows.
- Analysts should treat "vehicle_number is blank" as a channel marker. Expect channel-mix shifts, and check any time-series model for a 17–20 Oct artefact.
- The 20 Oct drop in both groups looks like a holiday. Dussehra is my unverified guess.

**What the stop fields mean in each flow**
- Blank rows: start_stop_name, end_stop_name and route are rider-declared. The rider may have bought before boarding, so created_at is not a boarding time.
- Vehicle rows: the route and direction (e.g. "8UP") were probably resolved from the scanned bus's current trip. The One Delhi review about "current route for a bus number" hints at this lookup. This is unconfirmed.
- Purchases before boarding are possible only in the newer route-based flows. The earlier flows (Tummoc 2024 FAQ: "You must board the bus") and the 23% figure for vehicle tickets suggest pre-purchase is a minority behaviour.

**The order cap**
- passenger_count tops out at 3 apart from one row, which fits a per-order cap of three like Tummoc's. That suggests a network- or seller-level cap. WhatsApp's "up to 6" may then be split into several orders. Unverified.

### Gaps
- No official One Delhi help, FAQ or terms text was retrievable. The DDC page refused connection, the Play page did not render, and the One Delhi terms and refund pages were not found online. So these remain unknown for One Delhi:
  - the exact 2025–26 purchase steps;
  - whether the bus scan comes at purchase or at a separate "validate" step;
  - the validity window in minutes.
- No source states which app produced each ticket, or which buyer apps support scan-first, route-first or both. The dataset has no app or channel column.
- The Chalo, Rapido, redBus, Tocxi and Katch Go flows for DTC buses are not publicly documented.
- No official DTC rule on e-ticket validity was found. Only third-party app rules: same day, and 30 min after activation.

## 2. ONDC bus ticketing in Delhi: buyer apps, flow differences, discounts, statistics

### Takeaway

DTC bus tickets, including the then-DIMTS cluster buses, went live on ONDC on 2 Sep 2024. One Delhi was the first buyer app. By 2026:

- DTC's page lists ten channels, including Rapido and redBus.
- ONDC lists One Delhi, Chalo, Chartr, Tummoc and OneTicket as transit ticketing apps.
- Press counts 30+ apps network-wide.
- Google Maps, Uber and Rapido are documented only for **Delhi Metro** ONDC tickets, apart from Rapido's appearance on DTC's list.

Chartr says it built India's first intra-city bus ONDC seller: 6.04 crore+ orders and ₹90.69 crore+ in seller amount. Very likely it is the DTC seller-side platform, and so the source that pools all buyer apps into this dataset.

The ONDC TRV11 v2.0.1 spec (20 Aug 2024) defines three ways to find or confirm a ticket: station-code, GPS and "Vehicle Based Confirmation" flows. The bus registration is an optional field (`fulfillments[].vehicle.registration`). It can be sent at confirm, or attached later through an `update` call.

The 10% discount is visible in the data: 99.3% of rows are exactly 0.9 × the ₹5/10/15/20/25 fare ladder.

There is no official Delhi-bus-only daily ONDC statistic. The CM's 12 Sep 2026 post gives "9.2 crore+" Delhi metro and bus journeys combined.

### Cited Findings

**Launch and buyer apps**
- 2 Sep 2024: ONDC partnered with DTC for "digital QR ticketing". DTC and DIMTS are both integrated, and the buyer app is One Delhi with UPI. Chartr, Tummoc and WhatsApp were "to be integrated soon". EaseMyTrip, Paytm and redBus were named as upcoming buyer apps. — [Inc42](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc/); [CXOToday](https://cxotoday.com/media-coverage/digital-qr-ticketing-for-dtc-buses-now-live-on-the-ondc-network/); [Mediabrief](https://mediabrief.com/digital-qr-ticketing-for-dtc-and-dimts-buses-now-live-on-ondc/)
- ONDC's public-transport page lists these buyer apps:
  - Delhi Metro Sarthi ("Official Delhi Metro ticketing").
  - One Delhi ("Delhi bus and metro ticketing").
  - Chalo, OneTicket, Tummoc and Chartr.
  - Bharat Taxi, Namma Yatri and Yatri Sathi.

  The page is undated. — [ONDC public transport](https://ondc.org/pages/public-transport.html)
- June 2026 (search summary):
  - Intra-city bus is live on ONDC for DTC, CRUT (Odisha), BEST (Mumbai) and Katch Mobility.
  - Tickets sell through 30+ apps "including Uber, Rapido, Paytm, ixigo, Namma Yatri, redBus, magicpin, and Navi". The list is network-wide and does not say which apps sell DTC buses.

  — [Business Standard, Jun 2026](https://www.business-standard.com/industry/news/ondc-enables-three-lakh-daily-bus-and-metro-ticket-bookings-126060101212_1.html)
- Ixigo ran ONDC QA as a buyer app for "Unreserved Ticket Booking (Intracity Busses) | TRV 11 | v2.0.1" from 22–24 Sep 2026. No operator is named. — [ONDC pramaan #2032](https://github.com/ONDC-Official/pramaan/issues/2032)
- Metro-only evidence for other big apps:
  - Google Maps in-app booking in Delhi covers metro only, "powered by … Namma Yatri" — [Google Maps Help](https://support.google.com/maps/answer/15179212?hl=en&co=GENIE.Platform%3DAndroid)
  - Uber added Delhi Metro QR tickets via ONDC in May 2025 — [Inc42](https://inc42.com/buzz/uber-users-can-now-buy-delhi-metro-qr-tickets-within-the-app/)
  - Rapido sells Delhi Metro tickets via ONDC. One summary dates this to June 2025, while the May 2025 Uber coverage says Rapido had launched earlier (search summaries) — [Inc42](https://inc42.com/buzz/rapido-rolls-out-service-to-allow-users-to-book-delhi-metro-tickets/)
  - I found no launch report for DTC bus tickets on these apps. Rapido is on DTC's channel list — [DTC](https://dtc.delhi.gov.in/dtc-digital-ticket/)

**Seller side (Chartr)**
- Chartr "was the first company in India to build intra-city bus ticketing ONDC seller", with "6.04 Cr+ orders fulfilled and ₹90.69 Cr+ in seller amount" and "7+" buyer network participants onboarded. The figures are undated, and no operator is named. — [Chartr ONDC blog](https://chartr.in/blog/ondc/)
- Chartr is registered as both "Technology Service Provider Seller" and "Technology Service Provider Buyer". Its Delhi card lists the role "ONDC Seller", with "1.5 Cr Tickets", "3,500 Buses" and "37 Depots". — [chartr.in](https://chartr.in/)
- A GitHub user "AmanChartr" (apparently Chartr; the affiliation is inferred from the username) commented on the TRV11 v2.0.1 spec thread on 6 Sep 2024. — [ONDC mobility-spec discussion #195](https://github.com/ONDC-Official/mobility-specification/discussions/195)

**Protocol (ONDC TRV11, "unreserved ticket booking", metro and intracity bus)**
- README version table: v2.0.1 (20 Aug 2024), "Base version of mobility for metro & intracity is completed". It lists four flows: "Station code based flow", "GPS based flow", "Cancel flow" and "Vehicle Based Confirmation flow". Change notes: a TICKET_INFO tag group for the ticket number, a separate TICKET fulfillment under a base TRIP fulfillment (linked by PARENT_ID), and timestamps for time in items. — [mobility-specification README, draft-TRV11-2.0.1](https://raw.githubusercontent.com/ONDC-Official/mobility-specification/draft-TRV11-2.0.1/README.md)
- Backlog, 2–3 Sep 2024 — [Discussion #196](https://github.com/ONDC-Official/mobility-specification/discussions/196); [Discussion #195](https://github.com/ONDC-Official/mobility-specification/discussions/195):
  - "Vehicle based confirmation flow": "update API flow with vehicle number for vehicle number based confirmation flow".
  - Ticket validity: "Timestamp at item level signifying validity of ticket" (`item.time.duration` / `item.time.timestamp`).
  - TICKET means "individual ticket(s) (viz. single or multiple qr codes)".
- Intracity-bus example files — [examples/intracity-bus](https://github.com/ONDC-Official/mobility-specification/tree/draft-TRV11-2.0.1/api/components/examples/intracity-bus):
  - **Search:** "Search_for_intra_city_bus_service, with city and type of vehicle", and "…mode of transit from a specific position" (GPS).
  - **Confirm:** two vehicle-related examples, "confirm_ticket_vehicle_based" and "confirm_ticket_vehicle_confirm". In confirm_ticket_vehicle_confirm, the two TICKET fulfillments (F5, F6) carry `vehicle.registration: "GL90"`, and the TRIP fulfillment (F1) carries none. The vehicle_based example as read lists only fulfillment IDs. — [confirm_ticket_vehicle_confirm.yaml](https://raw.githubusercontent.com/ONDC-Official/mobility-specification/draft-TRV11-2.0.1/api/components/examples/intracity-bus/confirm/confirm_ticket_vehicle_confirm.yaml)
  - **Update:** "Update_vehicle_details_for_intra-city_bus_service" uses `update_target: "order.fulfillments"` to set `message.order.fulfillments[].vehicle.registration` on an existing order. — [Update_vehicle_details…_18.yaml](https://raw.githubusercontent.com/ONDC-Official/mobility-specification/draft-TRV11-2.0.1/api/components/examples/intracity-bus/update/Update_vehicle_details_for_intra-city_bus_service_18.yaml)
  - **Payment** in the example: `collected_by: "BAP"` (the buyer app takes the money), with a BUYER_FINDER_FEES tag and a SETTLEMENT_TYPE of `upi`.
- Monthly-pass flows for TRV11 intracity buses were still being QA'd in Sep 2026. A "PASS" fulfillment type exists, with fields such as Vehicle.category. — [automation-framework #1443](https://github.com/ONDC-Official/automation-framework/issues/1443)

**Discounts**
- July 2021: the Delhi Cabinet approved a 10% fare discount on DTC and cluster buses for tickets bought through contactless app ticketing. — [HT via PressReader](https://www.pressreader.com/india/hindustan-times-delhi/20210718/281651078120594)
- In 2025–26 the 10% is advertised for One Delhi ([APKPure](https://apkpure.net/one-delhi/com.delhitransport.onedelhi)), Chalo ([Impressive Times](https://impressivetimes.com/latest/delhi-inter-state-ac-bus-service-2025-afcs-chalo-app/)) and Chartr ([Chartr](https://www.chartr.in/products/chartr-app/)).
- Per-passenger amounts in the October 2026 file. — (local data check)

  | Fare | Rows | Share | Equivalent to |
  |---|---:|---:|---|
  | ₹9.0 | 1,026,439 | 40.1% | 0.9 × ₹10 |
  | ₹13.5 | 813,302 | 31.8% | 0.9 × ₹15 |
  | ₹18.0 | 274,722 | 10.7% | 0.9 × ₹20 |
  | ₹22.5 | 237,866 | 9.3% | 0.9 × ₹25 |
  | ₹4.5 | 190,044 | 7.4% | 0.9 × ₹5 |

  - These five values make up 99.3% of rows.
  - Full-fare values are absent from the top 15. ₹10/15/20/25 do not appear there, so each has fewer than 46 rows. ₹13, ₹22, ₹27 and ₹40 together cover under 0.3%.
  - Other values: ₹26.5 (6,441 rows), ₹22.0 (4,656), ₹31 (1,721), ₹35.5 (1,120), ₹44.5 (755). These are unexplained, possibly NCR or longer routes.
  - Only 8 rows have amount = 0.

**Statistics**
- About 12 Sep 2026 (search summary):
  - The CM's post said Delhi commuters can use ONDC apps for metro and bus tickets, and ONDC said "9.2 crore+ journeys have already gone digital". This is Delhi metro and bus combined, with no bus split.
  - Network-wide: over 5 lakh metro and bus journeys a day, about 30% of online public-transport transactions, 40+ consumer apps, and "four city bus entities".

  — [Orissa Diary](https://orissadiary.com/delhi-cm-highlights-ondc-enabled-metro-bus-ticketing-as-digital-journeys-cross-9-2-crore/); [ONDC on X, 12 Sep 2026](https://x.com/ONDC_Official/status/2098683617291755755)
- ONDC network-wide figures: "300K+ tickets/day" across metro and bus, "10K+ buses across 20+ cities", "30+ buyer apps". — [ONDC public transport](https://ondc.org/pages/public-transport.html)
- The hackathon says bus e-ticketing "captures only 3–4% of bus tickets". — [Transport Stack hackathon](https://delhi.transportstack.in/hackathon/)

### Inferences

**Where the dataset comes from**
- Chartr says it built the first intra-city bus ONDC seller and labels Delhi "ONDC Seller", and DTC was the first city bus service on ONDC. So Chartr almost certainly runs the DTC seller-side platform. No source states this explicitly.
- If so, the Transport Stack/IIIT-Delhi extract is a seller-side log. It pools orders from every buyer app, which explains why it has no app column.
- Chartr's ₹90.69 Cr ÷ 6.04 Cr orders is about ₹15 per order. Spread over about 26 months since Sep 2024, 6.04 Cr is about 75–80k orders a day. That is the same order of magnitude as the file's 82.6k a day, but Chartr's totals may include CRUT (Odisha) and passes.

**How the vehicle number can arrive (the protocol allows three ways)**
- (i) At confirm, when the buyer app already knows the bus because the rider scanned the bus QR first.
- (ii) Via a later `update`, when the rider buys first and then scans or validates on the bus.
- (iii) Never, in pure route/stop or GPS flows.
- If the extract's created_at is the order time, rows filled by (ii) would have a vehicle but a purchase time before the scan. The observed +0.8 min median suggests (i) dominates the vehicle rows. The split between (i) and (ii) is unknown.

**What the amount column means**
- amount is the post-discount price: 0.9 × the slab fare × passenger_count. Undo the discount (÷ 0.9) to recover fare slabs or distance bands.
- Both channels (with and without a vehicle number) carry the same discount.

**Why volume fell since 2024**
- January 2024 One Delhi sold about 1.5 lakh a day; the file has about 82.6k a day. The fall is consistent with free pink app tickets being removed (only 8 zero-amount rows) and conductor UPI/NCMC on the new ETMs absorbing some digital payers. This is an inference, not an evidenced cause.

### Gaps
- No official 2025–26 daily count of Delhi bus ONDC tickets, and no split by buyer app or flow. The CM/ONDC figure combines metro and bus, and Business Standard and Orissa Diary could only be read via search summaries.
- I could not confirm from a primary source which of the 30+ network apps actually sell DTC bus tickets (vs. metro only): Paytm, PhonePe, Uber, Namma Yatri, Google Maps, ixigo, magicpin and Navi are all unconfirmed for DTC buses. Rapido and redBus are confirmed only by DTC's list.
- Chartr's role as DTC's seller-side provider is inferred, not stated.
- It is not documented which buyer apps implement the vehicle-based confirm or update flow.
- The TRV11 2.1.0 changes, and whether DTC uses 2.0.1 or 2.1.0 in production, were not determined.

## 3. Conductor Electronic Ticketing Machines (ETMs): UPI QR and card payment, vendor/system, relation to ONDC data

### Takeaway

On 23 Sep 2025 DTC launched an Automated Fare Collection System (AFCS) with Canara Bank: an MoU and about 3,000 PoS/ETMs supplied at no cost. Conductors accept cash, UPI, debit and credit cards, "static Universal QR codes" and NCMC. The system was first limited to about 300 buses and reached all DTC and cluster buses by 4–5 Oct 2025.

Conductor-issued tickets are a separate AFCS/bank stream. Nothing indicates they pass through ONDC. The fare pattern in the file (all 0.9 × ladder, no full fares) and the hackathon's separate "ETM data" label point the same way: ETM cash, UPI, card and NCMC tickets are **not** in the ONDC file. No hardware or software vendor beyond Canara Bank was found.

### Cited Findings
- AFCS launch, 23 Sep 2025 — [Impressive Times, 23 Sep 2025](https://impressivetimes.com/latest/delhi-inter-state-ac-bus-service-2025-afcs-chalo-app/):
  - The AFCS was "developed in partnership with Canara Bank", with an MoU for rolling it out across the bus network.
  - "PoS/ETM machines" replace manual ticketing, with about 3,000 installed free of cost.
  - Payment modes: cash, UPI, debit and credit cards, "Static Universal QR codes" and NCMC.
  - "Stickers with Universal QR codes have already been deployed across the fleet".
  - Stated goal: "The number of tickets sold will match the number of passengers". Revenue goes directly to DTC's account.
- DTC post, 23 Sep 2025: "DTC with Canara Bank has implemented the Automated Fare Collection System (AFCS) and state-of-the-art E-Ticketing Machines". — [DTC on X](https://x.com/dtchq_delhi/status/1970523256760262895)
- 5 Oct 2025, citing DTC's post of 4 Oct — [ETV Bharat](https://www.etvbharat.com/en/!state/dtc-cashless-ticketing-system-now-implemented-on-all-delhi-buses-enn25100503259):
  - The system is live in all DTC and cluster buses. Earlier it was "limited to only 300 buses".
  - Every bus operator has been given an ETM.
  - Passengers pay by debit card, credit card, UPI or NCMC.
- An unofficial site gives depot counts and a discount notice (search summary; low confidence). — [dtcbus.co.in](https://dtcbus.co.in/national-common-mobility-card-payments-in-dtc-buses/)
  - 100 machines at Rajghat depot and 245 at Hasanpur.
  - In-bus displays advertise 10% off for NCMC payments.
- An undated Morning Standard item describes a cashless-ticketing pilot at selected depots with 10% off for card users (search summary). — [Morning Standard via Magzter](https://www.magzter.com/nl/stories/newspaper/The-Morning-Standard/DTCS-CASHLESS-TICKETING-TRIAL-UNDERWAY-AT-SELECTED-DEPOTS)
- Older history:
  - A Cabinet decision gave 10% off for using a Metro card or Common Mobility Card on DTC and cluster ETMs. If no ETM ticket could be issued, the full cash fare applied (undated, pre-2022; search summary). — [Millennium Post](https://www.millenniumpost.in/delhi/10-discount-in-dtc-fares-on-usage-of-metro-mobility-cards-329461)
  - DTC's 2016 ETMs were phased out in September 2022, and DTC moved to pre-printed paper tickets. Cluster buses kept handheld ETMs (reused from etm_ticket_india.md). — [HVT/Transport-Links 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- Chartr sells Android ETMs with UPI, NFC and QR support. They run offline-first, store transactions locally and push them "in real time or synced when connectivity returns". No source says Chartr supplied DTC's 2025 ETMs. — [Chartr AFCS](https://chartr.in/products/afcs/); [Chartr ETM blog](https://chartr.in/blog/etm/)
- The hackathon names "E-ticketing and Electronic Ticketing Machine (ETM) data" as separate inputs for Problem 2. The October file README says "Ticketing is from ONDC e-ticketing". — [Transport Stack hackathon](https://delhi.transportstack.in/hackathon/); [README](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/README.md)

### Inferences

**ETM payments are outside the ONDC file**
- ETM-issued tickets, whether paid by cash, UPI, card or NCMC, are recorded by the Canara Bank AFCS, not as ONDC orders.
- The fare pattern supports this. If conductor UPI or card tickets were mixed in, full-fare per-passenger values (₹5/10/15/20/25) would appear. They are essentially absent.

**What the "Universal QR" sticker is remains open**
- Reading 1: it is the interoperable successor to app-specific stickers. In 2024 Tummoc still told riders to scan the Tummoc QR if one was posted in the bus, and otherwise to enter the bus number. If so, any ONDC buyer-app scan yields the bus registration.
- Reading 2: it is a static UPI or Bharat QR for paying DTC directly. Then those payments sit in the bank/AFCS stream, not ONDC.
- The sources do not settle this.

**What a 2025 ETM record would hold**
- If they follow Indian ETM practice, they would record ETM/conductor ID, vehicle, route and direction, fare stage or stop, time and payment mode (see etm_ticket_india.md for the GIZ and HVT field lists).
- The 2025 AFCS schema is not published.

### Gaps
- The ETM hardware maker and AFCS software vendor are not identified (Canara Bank is only named as partner or acquirer).
- These are also unknown:
  - the ETM data schema;
  - whether ETMs record a GPS-stamped boarding stop;
  - whether ETMs can scan passenger QR tickets;
  - whether a 10% NCMC discount applies on the 2025 machines.
- There is no public breakdown of conductor-ticket volume by payment mode (cash vs. UPI vs. card vs. NCMC).
- The content and behaviour of the "Universal QR" stickers are unknown (see Inferences).

## 4. NCMC, Pink Saheli Smart Card and passes: how they are tapped and recorded, and whether they appear in ONDC data; final Pink Saheli date

### Takeaway

The Pink Saheli Smart Card is a personalised NCMC "tap-and-go" card. Riders tap it on the conductor's ETM, and "the journey is automatically recorded". Other NCMC cards and bank cards are also accepted on the same ETMs.

The final switchover:

- Paper pink tickets were extended to 30 Sep 2026.
- Card-only free travel ran from 1 Oct 2026. Some reports use "from 30 September" or "since 3 October".
- The formal rule was notified on Sunday 4 Oct 2026 as the "Delhi Transport Corporation (Free and Concessional Passes) (Second Amendment) Regulations, 2026".
- Earlier dates were superseded by extensions: 1 Aug, 1 Sep, and 17–18 Sep 2026.

These taps are ETM/AFCS records and are absent from the ONDC file, which has only 8 zero-fare rows in October 2026. Passes are sold in One Delhi (from Aug 2025), Chartr (from Aug 2025) and Tummoc. ONDC pass flows were still in QA in Sep 2026, and the file has only ticket_type_id = 1.

### Cited Findings

**How the card is used and recorded**
- The card works on NCMC "Tap-and-Go" technology, and "the journey is automatically recorded by tapping the card on ETM machines". Passengers "no longer need paper tickets" and can access a "digital travel record". — [Daily Prabhat (ANI), 7 Oct 2026](https://www.dailyprabhat.com/pink-saheli-takes-off-35-lakh-women-ride-dtc-in-6-days-38-card-centres-set-up-across-delhi/)
- The card is valid on DTC and cluster buses, and riders "tap it on the Electronic Ticketing Machine (ETM) while boarding the bus". — [Times Today, 17 Jul 2026](https://www.timestoday.co/2026/07/17/pink-saheli-smart-card-mandatory-for-free-dtc-bus-travel-from-august-1-2026/)
- Economic Survey 2025-26: free travel is implemented "with provision of Pink Saheli Smart Card/NCMC Card. A single journey pass of face value of 10/- … is being issued" (reused from delhi_ops.md). — [ES 2025-26](https://delhiplanning.delhi.gov.in/sites/default/files/2026-03/economic_survey_english_0.pdf)

**Dates (in the order they were announced)**
- 17 Jul 2026 report: paper pink tickets invalid after 31 Jul, and the card mandatory from 1 Aug 2026. — [Times Today](https://www.timestoday.co/2026/07/17/pink-saheli-smart-card-mandatory-for-free-dtc-bus-travel-from-august-1-2026/)
- 1 September, from a NewsX headline only (reused from delhi_ops.md). — [NewsX](https://www.newsx.com/india/no-more-pink-tickets-on-delhi-buses-why-women-need-the-pink-saheli-smart-card-from-september-1-266667/)
- Paper ticket "valid till 17 September 2026", and card-only from 18 Sep (search summary). — [govtschemesindia](https://www.govtschemesindia.com/delhi-pink-saheli-smart-card-scheme/)
- Headline: "Delhi Government Extends Paper Pink Tickets Till September 30; Smart Card Mandatory From October 1" (search result; page returned 502). — [LatestLY](https://www.latestly.com/india/news/delhi-government-extends-paper-pink-tickets-till-september-30-smart-card-mandatory-from-october-1-7608818.html)
- 4 Oct 2026 report (PTI), announced "on Sunday" — [The Patriot (PTI), 4 Oct 2026](https://thepatriot.in/delhi-ncr/pink-saheli-card-mandatory-for-free-bus-travel-by-women-in-delhi-90596/amp):
  - The Transport Department "had earlier directed that the Pink Saheli Smart Card would be mandatory" from 30 September.
  - The card "replaced the paper-based pink tickets … after several extensions".
  - The rule is notified as the "Delhi Transport Corporation (Free and Concessional Passes) (Second Amendment) Regulations, 2026".
  - Free travel is for women and transgender residents of Delhi, on DTC and cluster buses, AC and non-AC. Ineligible women may buy a ticket at the applicable fare.
  - About 19 lakh women have used the card since its March 2026 launch.
- 7 Oct 2026 (ANI): the card-based free travel system was "announced" on 3 October. More than 35 lakh women travelled on DTC buses in the first 6 days of October, and more than 25 lakh since 3 October. These figures are not reconciled in the source. There are 38 issuing centres. — [Daily Prabhat (ANI)](https://www.dailyprabhat.com/pink-saheli-takes-off-35-lakh-women-ride-dtc-in-6-days-38-card-centres-set-up-across-delhi/)

**Before 2026 (app pink tickets)**
- One Delhi could issue free pink QR tickets by scanning the in-bus QR. — [Curly Tales, 2021](https://curlytales.com/delhi-book-bus-tickets-via-one-delhi-application-heres-how/amp/)
- HVT (2024) lists "One Delhi App → gender, QR ticket purchase incl. free pink ticket", and "Metro card on bus → boarding only (one tap)" (reused). — [HVT/Transport-Links 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)
- In Chartr's 2020 pilot, 79.4% of app tickets were pink tickets (reused). — [PMC10152222](https://pmc.ncbi.nlm.nih.gov/articles/PMC10152222)

**Passes**
- One Delhi 2.16 "Added Bus Passes" (24 Aug 2025) — [App Store](https://apps.apple.com/in/app/one-delhi/id1641749010)
- Chartr 1.1.0 "Added passes" (31 Aug 2025) — [App Store](https://apps.apple.com/us/app/-/id6747386059)
- Tummoc passes are validated by entering the bus number or scanning the bus QR — [Tummoc, Jun 2024](https://blog.tummoc.com/?p=2344)
- The ONDC TRV11 intracity-bus monthly-pass ("PASS" fulfillment) flow had open QA bugs in Sep 2026 — [automation-framework #1443](https://github.com/ONDC-Official/automation-framework/issues/1443)

**Local data checks on the ONDC file**
- Only 8 rows have amount = 0, and ticket_type_id is always 1. — (local data check) [October-Delhi.csv](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/October-Delhi.csv)

### Inferences
- **Final date.** Treat **1 Oct 2026** as the operative card-only date: paper pink tickets were accepted through 30 Sep 2026. Treat 4 Oct 2026 as the date the regulation was notified. October 2026 is therefore entirely in the card era. The ANI "since 3 October" wording probably refers to the announcement or publicity, not the cut-over.
- **Free rides are not in the file.** Women's free rides in October 2026 are ETM/AFCS card taps. They are not ONDC orders and do not appear in the file: there are only 8 zero-fare rows.
- **What a tap record probably holds.** A Pink Saheli tap record most likely holds card ID, ETM/vehicle, route and time, but nothing published confirms that. This is the field that would let ETM data recover women's boardings.
- **Possible shift in paying riders.** Women who are not Delhi residents, or who lack a card, now pay. Some may buy app tickets, so the ONDC file may contain slightly more paying women from October 2026. This is not measurable from the file, which has no gender field.
- **Passes are not in the file.** App pass sales and validations, like monthly passes or Tummoc's bus-number validation, are not single-journey ONDC tickets. ticket_type_id = 1 only suggests passes are excluded, or not live on ONDC for DTC.

### Gaps
- The official Transport Department or DTC notification text, with the exact effective date and clause, was not retrieved. Zeebiz returned 402, LatestLY 502, and Business Standard was not fetched.
- The content of a Pink Saheli or NCMC tap record is not published: whether it holds a boarding stop or GPS fix, the vehicle number, or a ₹10 nominal value.
- There are no public counts of pass holders or pass validations, and it is not documented whether app pass validations reach any dataset.
- Card eligibility age is still inconsistent across sources (5+ vs. 12+; see delhi_ops.md).

## 5. Official documentation of what a Delhi bus QR ticket contains

### Takeaway
I found **no** DTC, Transport Department or ONDC document that lists the fields printed on, or encoded in, a Delhi bus QR ticket. The closest primary sources are:

- **ONDC TRV11 v2.0.1 examples.** These include a ticket number (TICKET_INFO), item-level validity, stops, an optional `vehicle.registration` on TICKET fulfillments, quantity and payment.
- **Third-party app documentation.** Tummoc shows "last validated time, bus number and route number" after a bus-QR scan. Chartr says tickets are time-bound and conductor-scanned.
- **The hackathon README.** It is the only schema of the extract.

Vehicle registration is optional in every source. It is present only when a bus QR or bus number was supplied.

### Cited Findings
- **Hackathon README schema.** Columns: passenger_count, amount ("22"), vehicle_number (`DL1PD6826`, "blank, NULL, on about half the rows"), ticket_type_id (1), start_stop_name, end_stop_name, route (`8UP`), created_at (`2026-10-28 10:19:18.780611+05:30`) and is_ac. The GPS vehicle_id uses the same registration format (`DL1PD8979`). Source line: "Ticketing is from ONDC e-ticketing." — [README](file:///C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data/raw/ticketing/README.md)
- **ONDC TRV11 v2.0.1:**
  - TICKET_INFO tag group "for ticket number".
  - TICKET fulfillment as a child of TRIP (PARENT_ID).
  - Item-level time for validity (`item.time.duration` / `item.time.timestamp`).
  - Search by city and vehicle type, or by position.
  - Confirm, or a later update, carrying `fulfillments[].vehicle.registration`.

  — [README](https://raw.githubusercontent.com/ONDC-Official/mobility-specification/draft-TRV11-2.0.1/README.md); [Discussion #195](https://github.com/ONDC-Official/mobility-specification/discussions/195); [update example](https://raw.githubusercontent.com/ONDC-Official/mobility-specification/draft-TRV11-2.0.1/api/components/examples/intracity-bus/update/Update_vehicle_details_for_intra-city_bus_service_18.yaml)
- **Validator fields (Sep 2026 QA notes).** Intracity-bus on_init and on_confirm are expected to carry:
  - `fulfillments.stops` (type "start", `location.descriptor.code`, gps, id) and `Vehicle.category`/variant.
  - The TICKET_INFO "NUMBER" tag.
  - `valid_to`, plus the "SCHEDULED_INFO"/"GTFS" codes.

  — [automation-framework #1443](https://github.com/ONDC-Official/automation-framework/issues/1443)
- **Tummoc.** After scanning the bus QR, the app shows "the last validated time, bus number and route number". — [Tummoc FAQ](https://blog.tummoc.com/dtc-ticket-and-pass-faqs/)
- **Chartr.** Mobile QR tickets are "time-bound" and conductor- or inspector-scanned, with cross-bus reuse detection. — [Chartr AFCS](https://chartr.in/products/afcs/)
- **Indian ETM practice, for comparison (reused from etm_ticket_india.md).** ETMs record "the route, time, origin, destination and fare for each trip". HVT lists ETM fields as "origin and destination stops, fare stage, time stamp, vehicle number, trip direction". — [GIZ Roadmap 2021](https://changing-transport.org/wp-content/uploads/2021_Roadmap-for-Data-driven-Transformation-of-Indian-Bus-Systems.pdf); [HVT 2024](https://transport-links.com/wp-content/uploads/2024/10/HVT055-%E2%80%93-LC023_Safe-and-Secure-Public-Transport-in-Delhi_Final-Report_F-17-1.pdf)

### Inferences

**What each channel records** (synthesis of the findings above; 2025–26 status). Columns: whether the channel is in the ONDC file; whether the vehicle registration is captured, and when; and stop/time semantics.

| Channel | In ONDC file? | Vehicle reg captured? | Stop and time semantics |
|---|---|---|---|
| App, scan-first (scan bus QR → choose destination → pay): One Delhi, Chartr, Tummoc, likely redBus "DTCQR" and others | Yes | Yes, at purchase (confirm) | Rider is on board. created_at ≈ just after boarding. Route probably taken from the bus's current trip. |
| App, buy-then-validate (pay → board → scan bus QR or type bus number): Tummoc 2024; One Delhi "validate" | Yes (the order) | Only if the validation is sent back to the seller via ONDC `update` (protocol supports it; practice unknown) | created_at = purchase time, possibly before boarding. Validation time is not in the extract. |
| App, route/stop or GPS flow, no bus scan: Chartr route-based (Apr 2026), WhatsApp, likely Chalo/Rapido/others | Yes | No (blank) | Route and stops are rider-declared. Can be bought at the stop or earlier, same day. |
| Conductor ETM: cash, UPI, cards, NCMC (Canara AFCS since Sep–Oct 2025) | No | ETM tied to the bus, but not in this file | Separate AFCS stream. Full fare, apart from a possible NCMC discount. |
| Pink Saheli NCMC tap on ETM (only way to ride free from 1 Oct 2026) | No | Probably via the ETM, unpublished | Free ride, recorded as a tap. |
| App passes (One Delhi, Chartr, Tummoc); paper or online DTC passes | No (ticket_type_id = 1 only) | Tummoc pass validation records bus number in-app | Not single-journey tickets. |

**Practical reading of the file**
- Rows with a vehicle_number can be joined to GPS vehicle_id and treated as on-board purchases.
- Blank rows are a different channel with rider-declared stops. Their purchase time may precede boarding, and the channel mix shifts, as seen on 17–19 Oct.
- amount = 0.9 × fare × passenger_count.
- The file carries no women's free rides, no passes and no conductor tickets.

### Gaps
- There is no official schema, circular or FAQ listing QR-ticket fields for DTC.
- It is not documented how route (with UP/DOWN) and start_stop_name are populated in scan-first flows (auto-filled from AVL or phone GPS, or chosen by the rider) or in route flows (direction inferred from the stop order).
- It is unknown whether created_at is the order-confirm time at the seller or at the buyer app, and whether a later vehicle `update` changes any field in the extract.
