# ONDC bus e-ticketing in Delhi: protocol, systems, and what each ticket field means (as of 16 Nov 2026)

Scope and conventions:
- Covers Delhi DTC and cluster (DIMTS) buses, 2024–2026. Items dated before 2024 are tagged **[older]**.
- **"Spec"** means ONDC's TRV11 mobility specification in the GitHub repo `ONDC-Official/mobility-specification`. I downloaded and read the YAML files directly.
- **"Seller code"** means the public repo `transport-stack/ondc-buses-seller`, in the Delhi Transport Stack GitHub organisation, with commits by the user `ks-chartr`. I read it file by file. It is a public snapshot published in 2026 and may not match what ran in production in October 2026 (see the Gaps in §2).
- **Dataset facts** come from the coordinator and were not re-derived here: the columns passenger_count, amount, vehicle_number, ticket_type_id, end_stop_name, route, start_stop_name, created_at and is_ac, plus the observed patterns (a)–(d).
- **Cited Findings** are what a source documents. **Inferences** are my own reasoning. "(snippet only)" means the page could not be opened and the claim comes from a search-engine snippet; treat those as weaker.
- Source wording is paraphrased. Field and enum names (`vehicle.registration`, `QR_AND_VEHICLE_NUMBER`) are given verbatim because they are identifiers.

**End-to-end chain, in brief** (details and sources in §1–§3):

```
Rider app (buyer app / BAP: One Delhi, Chartr, Tummoc, WhatsApp bot, Chalo, ...)
  │ search  (stop codes START/END, vehicle.category=BUS, [Delhi convention: vehicle.registration, vehicle.variant])
  ▼ ONDC gateway → registry lookup → seller platform (BPP: "Transport Dept." catalog; providers DTC / DIMTS)
  ◄ on_search  (one item per route-variant: route name, SJT, fare, qty 1..3, validity PT1D; fulfillment = stops + vehicle{BUS, AC/NAC, registration echoed})
  │ select → on_select (fare from fare matrix: route × stop pair × AC/NAC)
  │ init   → on_init   (price × passenger count; payment collected by the buyer app; TTL 3 min)
  │ [buyer app collects UPI payment]
  │ confirm (payment PAID + payment transaction_id)
  ▼ seller: on_confirm task → INSERT Ticket row (created_at = now) → encrypted QR string → on_confirm to buyer app
  ◄ on_confirm (QR in fulfillment.stops[0].authorization; valid_to = next day 03:00 IST; status CLAIMED/UNCLAIMED)
Conductor/inspector scans QR → seller validate_qr endpoint → ticket record
Buyer app settles money to Transport Dept. T+1 + reconciliation API call
```

## 1. ONDC mobility spec (TRV11): which fields carry route, stops, fare, vehicle and timestamps? Is the vehicle optional? Is there a separate "bus known" flow?

### Takeaway
Delhi bus tickets use the ONDC domain `ONDC:TRV11` (unreserved metro and intracity bus tickets), a Beckn-style search → select → init → confirm → status/update exchange. The route is a `ROUTE_INFO` tag, the boarding and alighting stops are `fulfillment.stops[]` entries of type START and END, the fare sits in `items.price` and `quote`, the QR sits in `stops[].authorization` with a `valid_to`, and the order carries `created_at`/`updated_at`. In the base flow the vehicle is only `vehicle.category: BUS`. A bus registration (`vehicle.registration`) appears only in optional "Vehicle Based Confirmation" flows: drafted in May 2024, then in release 2.0.1 with the auth type `QR_AND_VEHICLE_NUMBER` from June 2025, plus a "User Based Confirmation" flow from August 2025. **At the protocol level, therefore, the vehicle number is optional and depends on the flow a buyer app implements.**

### Cited Findings

#### Where the spec lives, and its versions
- **Location.** ONDC's GitHub organisation lists "Unreserved Ticket Booking (Metro/Intracity Bus)" as version `release-TRV11-2.0.0` in its Mobility Specifications Developer Guide. — [ONDC-Official GitHub org](https://github.com/ONDC-Official); [Developer guide](https://ondc-official.github.io/mobility-specification/)
- **Other branches.** The repo also has `release-TRV11-2.0.1`, `draft-TRV11-2.1.0` and a feature branch `feat/vechicelConfimrationIntra` (typo in the original). — [branches](https://github.com/ONDC-Official/mobility-specification/branches/all)
- **Version table in the 2.0.0 README.**
  - v2.0.0 "Metro base", 20 Feb 2024.
  - v2.0.0 "Intracity base", 30 May 2024, on beckn core 1.2.0.
  - The Intracity base covers station-code, GPS and cancellation flows.
  - [README, release-TRV11-2.0.0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/README.md)
- **2.0.0 changelog.** The intracity spec update on the developer docs is dated 13 Aug 2024. It adds `collected_by` in search, and later entries run to April 2026. — [changelog 2.0.0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/docs/changeLog/TRV11_2.0.0_130824.md)
- **The intracity examples are modelled on Delhi.**
  - City code `std:011`.
  - Provider "Delhi Transport Corporation" with the DTC logo.
  - Stop codes such as `KASHMERE_GATE` → `GREATER_KAILASH`.
  - Example route `ROUTE_ID '242'`, `ROUTE_DIRECTION 'UP'`.
  - [search example 2](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/search/example_2.yaml); [on_search example 0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/on_search/example_0.yaml)

#### Message flow
- **Flows defined in 2.0.1:**
  - Purchase Journey (Code Based), using stop codes
  - GPS-based flow
  - Pagination
  - Unlimited passes
  - User cancellation and technical cancellation
  - Vehicle Based Confirmation, with and without an update call
  - User Based Confirmation
  - Seller Side Confirmation
  - [flows folder, release-TRV11-2.0.1](https://github.com/ONDC-Official/mobility-specification/tree/release-TRV11-2.0.1/api/components/flows)
- **Sequence.** Buyer app → gateway → registry lookup → seller platform. Then on_search catalog → select/on_select → init/on_init → confirm/on_confirm (in the seller-side variant, followed by an unsolicited on_update) → status/on_status. — [Seller Side Confirmation flow](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/flows/intracity_seller_side_confirmation/index.yaml)
- **Payment fields in confirm:** `collected_by: BAP` (the buyer app collects the money), `type: PRE_ORDER`, `status: PAID`, `params.transaction_id`, `params.amount`, `BUYER_FINDER_FEES` and `SETTLEMENT_TERMS` tags. — [confirm example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/confirm/example_0.yaml)

#### Route, stops, fare and timestamp fields
- **search.**
  - `message.intent.fulfillment.stops[]` holds a START and an END stop, given either as `location.descriptor.code` (stop code) or as `location.gps`.
  - `fulfillment.vehicle.category: BUS`.
  - A variant searches by vehicle category and city only.
  - [search example 0 (GPS)](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/search/example_0.yaml); [search example 2 (codes)](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/search/example_2.yaml)
- **Attribute dictionary.**
  - `vehicle.category` is MANDATORY in search and OPTIONAL in on_search.
  - `ROUTE_INFO.ROUTE_ID` and `ROUTE_DIRECTION` are MANDATORY in on_search.
  - `items.time.duration` (usage example `PT2D`, label "Validity") is described as the service time window.
  - `authorization.valid_to` is described as the token's validity.
  - [attributes, intracity-bus, 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/attributes/intracity-bus/index.yaml)
- **on_search catalog.**
  - Items have `descriptor.code` SJT, SFSJT (concession, with a `FARE_POLICY` tag) or PASS, plus `price.value`, `quantity.minimum/maximum.count` (max 6 in the example) and `time {label: Validity, duration: PT2D}`.
  - Fulfillments have type TRIP. Their stops run START → INTERMEDIATE_STOP (each with `parent_stop_id`) → END, with names, codes and GPS.
  - `vehicle.category: BUS`.
  - The `ROUTE_INFO` tag holds ROUTE_ID, ROUTE_DIRECTION and OPERATIONAL_START/END_TIME.
  - [on_search example 0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/on_search/example_0.yaml)
- **Enumerations.**
  - Fulfillment types: ROUTE, TRIP, and STOPS (added 16 Sep 2024).
  - Stop types: START, END, INTERMEDIATE_STOP, TRANSIT_STOP.
  - Authorization type: QR. Authorization status: UNCLAIMED or CLAIMED.
  - Ticket codes: SJT, SFSJT, RJT (return journey), PASS.
  - [enum Fulfillment.yaml](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/enum/Fulfillment.yaml); [enum item.yaml](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/enum/item.yaml); [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md)
- **on_confirm.**
  - `order.id` and `status: ACTIVE`.
  - **One fulfillment per passenger**, each with `stops[0].authorization {type: QR, token: <base64 QR>, valid_to: end of day, status: UNCLAIMED}` and a `TICKET_INFO.NUMBER` tag.
  - `quote.breakup` lines BASE_FARE, OFFER and TOLL.
  - `cancellation_terms` (cancel within PT60M, 0% fee).
  - `created_at` and `updated_at`.
  - [on_confirm example 0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/on_confirm/example_0.yaml)
- **Order status.** Values are ACTIVE, COMPLETED, CANCELLED and SOFT_CANCEL. `COMPLETE` was renamed `COMPLETED` on 16 Dec 2025, and `CANCEL_INITIATED` was added on 9 Oct 2024. — [enum status.yaml](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/enum/status.yaml); [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md)
- **Draft 2.1.0.**
  - CGST, SGST and SURCHARGE tags added to the quote (14 Nov 2025).
  - Point-of-sale "agent" flows enabled on 21 Nov 2025 (agent activation, agent login with route selection, agent-based purchase), i.e. conductor devices selling over ONDC.
  - A `GTFS` link in a `SCHEDULED_INFO` tag (10 Nov 2025, in 2.0.1).
  - [changelog 2.1.0](https://github.com/ONDC-Official/mobility-specification/blob/draft-TRV11-2.1.0/api/components/docs/changeLog/TRV11_2.1.0_141125.md); [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md)

#### The vehicle number, and the "bus known" flows
- **The official search examples never carry a registration.** In 2.0.0 and 2.0.1 they carry only `vehicle.category: BUS`. — [2.0.1 search examples](https://github.com/ONDC-Official/mobility-specification/tree/release-TRV11-2.0.1/api/components/examples/intracity-bus/search)
- **First draft, May 2024.** The feature branch `feat/vechicelConfimrationIntra` has a commit dated 28 May 2024 that adds a vehicle-based authorisation flow.
  - The buyer app sends `update` with `fulfillments[].vehicle.registration` (example value `GL90`).
  - The seller's on_update returns authorization `type: VEHICLE_NUMBER`, an empty token and `status: VERIFIED`.
  - [branch commits](https://github.com/ONDC-Official/mobility-specification/commits/feat/vechicelConfimrationIntra); [on_update vehicle example](https://github.com/ONDC-Official/mobility-specification/blob/feat/vechicelConfimrationIntra/api/components/examples/intra_city/on_update/example_1_vehicle.yaml)
- **Release 2.0.1, "Vehicle Based Confirmation (Without Update Call)".**
  - The buyer app's `confirm` already includes the registration, on each passenger's `TICKET` fulfillment.
  - on_confirm returns, per passenger, a `type: TICKET` fulfillment with `vehicle.registration`, authorization `type: QR_AND_VEHICLE_NUMBER` and `status: CLAIMED`, linked to the TRIP fulfillment through an `INFO.PARENT_ID` tag.
  - [flow](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/flows/intracity_vehicle_based_confirm_call/index.yaml); [confirm example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/confirm/confirm_ticket_vehicle_confirm.yaml); [on_confirm example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_confirm/Return_confirmed_vehicle_confirmation.yaml)
- **Release 2.0.1, "Vehicle Based Confirmation (With Update Call)".** The order is confirmed first, with the vehicle unknown. The buyer app later sends `update` (`update_target: order.fulfillments`) carrying the vehicle registration, and the seller answers with on_update. — [flow](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/flows/intracity___vehicle_based_confirmation_flow/index.yaml); [update example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/update/Update_vehicle_details_for_intra-city_bus_service_18.yaml)
- **Changelog entries for these flows.**
  - 18 Jun 2025: the vehicle authorisation code was renamed from VEHICLE_NUMBER to QR_AND_VEHICLE_NUMBER, and the vehicle-based flows were updated in both variants. The entry is filed under the Metro heading of the 2.0.1 changelog, but it concerns these intracity flows.
  - 22 Dec 2025 (2.1.0): the missing vehicle registration was added to the on_update of the vehicle-based flow.
  - The release 2.0.1 vehicle confirm example was itself added in a commit dated 18 Jun 2025.
  - [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md); [changelog 2.1.0](https://github.com/ONDC-Official/mobility-specification/blob/draft-TRV11-2.1.0/api/components/docs/changeLog/TRV11_2.1.0_141125.md); [file history](https://github.com/ONDC-Official/mobility-specification/commits/release-TRV11-2.0.1/api/components/examples/intracity-bus/confirm/confirm_ticket_vehicle_confirm.yaml)
- **"User Based Confirmation" (20 Aug 2025).**
  - New authorization type `USER_CONFIRMATION_AND_QR`.
  - on_confirm issues the ticket as `UNCLAIMED`.
  - The buyer app later sends `update` with `authorization.status: CLAIMED`, and on_update echoes it.
  - [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md); [flow](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/flows/intracity_user_based_confiramtion/index.yaml); [on_confirm example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_confirm/on_confirm_request_user_based.yaml); [update example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/update/update_vehicle_user_based.yaml)
- **[older] ONDC's intracity bus requirements document (v1.0, 31 Aug 2023).** The planned MVP was:
  - Search by place name or coordinates.
  - Choose a route, the number of tickets and a rider category.
  - Pay and receive a QR ticket.
  - It explicitly allowed for a QR that the rider activates before the journey starts.
  - [ONDC "Intra City BRD-MVP v1"](https://docs.google.com/document/d/1i2ZdcfZ40HValk-fLAHo41jEbfml3vEr/)

### Inferences
- **A blank vehicle number is protocol-legal and expected.** The spec has explicit flows for both cases: the bus identified at purchase (vehicle-based) and the bus confirmed later (update, or user-based claim). A ticket with no registration is the normal output of the base "code based" purchase flow, not an error.
- **The vehicle can arrive after the order exists.** Because the official flows put the registration in `confirm` or in a later `update`, whether a dataset row has a vehicle number can depend on *when* the row was written or exported relative to any later update.
- **Delhi departs from the official examples.** The seller code (§2) reads the registration from the *search* request, which none of the official search examples carry. That is a Delhi-specific convention between the seller and its buyer apps.
- **The dataset `route` value is not the ONDC route ID.** A value such as "433UP" is not the spec's ROUTE_ID + ROUTE_DIRECTION pair. In Delhi it comes from the seller's route name (§2).

### Gaps
- The developer-guide web app did not render. Field optionality comes from the attribute YAML and the examples, not from rendered documentation.
- The spec does not say which buyer apps implement which flow, or which flows Delhi's production seller supported in October 2026.

## 2. Who runs the Delhi seller side, which buyer apps sell Delhi bus tickets (and since when), and what the seller platform stores

### Takeaway
The seller of record is DTC / the Transport Department of the Delhi government (GNCTD), covering DTC and cluster (DIMTS) buses. It went live on ONDC on 2 Sep 2024, with the One Delhi app as the first buyer app; Chalo was added on 23 Sep 2025. The seller platform is Chartr's ONDC bus seller, published in 2026 as `transport-stack/ondc-buses-seller`. **Its `Ticket` table carries exactly the dataset's column names** (passenger_count, amount, vehicle_number, ticket_type_id, start_stop_name, end_stop_name, route, is_ac, created_at), so the hackathon file is very probably an extract of that table. In that code, vehicle_number is copied from the buyer app's *search* request and is NULL whenever the buyer app does not send one. The seller never looks the bus up itself.

### Cited Findings

#### Operator, seller platform and its builders
- **2 Sep 2024 launch.**
  - DTC city-bus QR ticketing went live on ONDC, the first public bus service on the network.
  - DTC and DIMTS bus services were both integrated.
  - One Delhi was the live buyer app, with payment by UPI.
  - Chartr, Tummoc and WhatsApp (which already sold DTC tickets) were "to integrate soon".
  - EaseMyTrip, Paytm and redBus were named as upcoming buyer apps.
  - [Inc42, 2 Sep 2024](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc); [CXOToday, 2 Sep 2024](https://cxotoday.com/media-coverage/digital-qr-ticketing-for-dtc-buses-now-live-on-the-ondc-network/)
- **ONDC's own timeline.**
  - September 2024: the first bus service goes live (DTC).
  - May 2025: Delhi Metro.
  - June 2026: 375K+ daily metro and bus tickets across 35+ apps.
  - [ONDC "Our journey"](https://ondc.org/pages/about-us.html)
- **DTC's terms for buyer apps.** The PDF is undated and is hosted on the Transport Stack CDN under the seller's `STATIC_TERMS` URL. It says:
  - DTC and cluster bus ticketing is enabled on ONDC.
  - Buyer apps must onboard ONDC and may not sell DTC or cluster tickets any other way.
  - The seller is DTC / the Transport Department, GNCTD.
  - The department may offer an online discount.
  - Any app convenience fee must be shown separately and is not reimbursed.
  - Money is settled T+1, with a reconciliation API call carrying the bank reference (UTR).
  - A GNCTD dashboard records the tickets sold by each buyer app.
  - [DTC static terms PDF](https://cdn-delhi.transportstack.in/ondc-seller/DTC_static_terms.pdf); [URL referenced in seller code](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py)
- **Chartr's self-description.**
  - It was the first company in India to build an intra-city bus ticketing seller on ONDC.
  - Cumulative, undated and self-reported: 6.04 crore+ (60.4M+) ONDC orders fulfilled, ₹90.69 crore+ seller amount, 7+ buyer apps onboarded.
  - Its Delhi page lists "India's 1st ONDC Seller for buses" and an "ONDC Seller & Buyer" product.
  - [Chartr ONDC blog](https://chartr.in/blog/ondc/); [Chartr Delhi page](https://chartr.in/cities/)
- **JICA DXLab.** It says India's first Beckn-protocol bus ticketing service was launched where Transport Stack and ONDC meet, and that JICA DXLab implements Transport Stack with the Delhi Transport Department. — [JICA DXLab DPI/DPG page](https://www.jica.go.jp/english/about/dx/jicadx/dxlab/dpi_dpg/index.html)
- **Chartr's Transport Stack page.**
  - Delhi Transport Stack was built by the Transport Department, GNCTD.
  - Chartr is one of two official partner applications.
  - It covers an open GTFS for DTC and DIMTS, and GTFS-RT from Chartr's vehicle-tracking system for 3,500+ buses.
  - Ticketing data is not listed among the datasets.
  - [Chartr – Delhi Transport Stack](https://chartr.in/products/transport-stack/)
- **Chartr and IIIT-Delhi.** Chartr is incubated at IIIT-Delhi. Per a June 2025 report, it completed a full technology transfer from the institute and powers digital ticketing and live tracking for DTC and cluster buses. — [The Week/PTI, 15 Jun 2025](https://www.theweek.in/wire-updates/national/2025/06/15/des25-dl-iiitd-chartr-app.html)
- **The public seller repo.**
  - The Transport Stack GitHub organisation hosts `ondc-buses-seller` (pinned) and `ondc-micro-mobility-buyer`. — [transport-stack org](https://github.com/transport-stack)
  - The repo was created on GitHub on 6 Apr 2026, last pushed on 13 Aug 2026, carries an Apache-2.0 licence and has commits by `ks-chartr`. — [repo](https://github.com/transport-stack/ondc-buses-seller); [commits](https://github.com/transport-stack/ondc-buses-seller/commits/main)
  - Its README describes the endpoints:
    - Search (1) returns all stops and routes.
    - Search (2) takes start and end stops and returns routes, intermediate stops and fares.
    - Select holds the session with a reservation timeout.
    - Init computes the fare from the passenger count.
    - Confirm runs after the buyer side has completed payment, generates a PNR and returns the QR ticket.
    - Update changes an existing booking.
    - [README](https://github.com/transport-stack/ondc-buses-seller/blob/main/README.md)
- **Schema dates (Django migrations).**
  - Ticket model with passenger_count and vehicle_number: 11 May 2024.
  - Route and stop codes: 20 May 2024.
  - created_at and stop names: 8 Jun 2024.
  - is_ac and agency: 6 Aug 2024.
  - claim_status: 24 Oct 2024.
  - [migrations folder](https://github.com/transport-stack/ondc-buses-seller/tree/main/main/migrations)
- **Settings.** `TIME_ZONE = "Asia/Kolkata"` with `USE_TZ = True`. The production database is PostgreSQL. — [settings/base.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/settings/base.py); [settings/production.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/settings/production.py)

#### Buyer apps for Delhi buses, and go-live dates

| Buyer app | Status for DTC/cluster buses on ONDC | Date | Source |
|---|---|---|---|
| One Delhi (Delhi government app) | First live ONDC buyer app | 2 Sep 2024 | [Inc42](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc) |
| Chartr | "Soon" in Sep 2024. Now lists itself as ONDC seller and buyer. Named by ONDC in Jun 2026 among bus-ticket apps | Buyer go-live date not found | [Inc42](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc); [Chartr](https://chartr.in/cities/); [StartupTalky, 1 Jun 2026](https://startuptalky.com/news/ondc-drives-public-transport-digitisation/) |
| Tummoc | "Soon" in Sep 2024. Named in Jun 2026 | Date not found | Same as above |
| WhatsApp (DTC chatbot) | Launched by DTC in Apr 2024, before ONDC. "Soon" to integrate in Sep 2024. ONDC's page says tickets are bookable on WhatsApp | ONDC go-live date not found | [Business Today, 11 Apr 2024](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11); [ONDC public transport](https://ondc.org/pages/public-transport.html) |
| Chalo | Launched on ONDC for DTC by the Delhi CM, with a 10% discount | 23 Sep 2025 | [The Week/PTI, 23 Sep 2025](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html) |
| EaseMyTrip, Paytm, redBus | "Upcoming" in Sep 2024. Not confirmed for DTC | — | [Inc42](https://inc42.com/buzz/now-dtc-bus-commuters-in-delhi-can-buy-tickets-online-via-ondc) |
| Uber, Rapido, Namma Yatri, ixigo, Navi, magicpin | Named as ONDC transit apps at network level (Delhi Metro confirmed). Not confirmed for Delhi buses | — | [StartupTalky, 1 Jun 2026](https://startuptalky.com/news/ondc-drives-public-transport-digitisation/) |

- **ONDC's 1 June 2026 statement.**
  - Intra-city bus booking is live for DTC, CRUT (Odisha), BEST (Mumbai) and Katch Mobility.
  - The named bus-ticket apps are Chalo, Tummoc, One Delhi, Katchapp and Chartr.
  - Over 30 apps are on the network, and the network handles 300K+ metro and bus tickets a day, with no split by city or mode.
  - [StartupTalky, 1 Jun 2026](https://startuptalky.com/news/ondc-drives-public-transport-digitisation/); [ONDC public transport page](https://ondc.org/pages/public-transport.html)

#### QR codes in buses, and how apps identify the bus
- **[older] Chartr / One Delhi trial design, 2020–21.**
  - "By Fare": scan the bus QR, then pay.
  - "By Destination": pick route, source and destination, then scan the bus QR.
  - One Delhi (July 2021): scan the QR inside the bus, then choose a fare or the source and destination stops.
  - [Chartr App Store listing (snippet only)](https://apps.apple.com/qa/app/chartr-tickets-bus-and-metro/id1586843576); [Curly Tales, 19 Jul 2021](https://curlytales.com/delhi-book-bus-tickets-via-one-delhi-application-heres-how)
- **[older] February 2021.** Contactless ticketing was extended to all DTC buses, with QR stickers on the back of seats. — [Hindustan Times via PressReader (snippet only)](https://www.pressreader.com/india/hindustan-times-st-noida/20210225/281809991618212)
- **Tummoc, June 2024.**
  - The rider validates on board by scanning a Tummoc QR if one is posted in the bus, otherwise by typing the bus number.
  - This implies Tummoc QRs were not in every bus.
  - [Tummoc blog, 10 Jun 2024](https://blog.tummoc.com/?p=2344)
- **September 2025: DTC's automated fare collection system.**
  - Built with Canara Bank: 3,000 conductor machines, installed free.
  - The machines accept cash, UPI, cards, static "Universal QR" codes and NCMC cards.
  - Universal QR stickers are reported as already deployed across the fleet.
  - The article does not say where the stickers are placed, whether they are bus-specific, or whether these payments become ONDC orders.
  - [The Week/PTI, 23 Sep 2025](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **Chartr's current pages.**
  - The app's bus flow: pick the route, enter start and end stops, choose AC or Non-AC, pay from the wallet. A QR is generated at once, and conductors scan it.
  - Chartr's fare-collection product page starts the flow differently: live bus on a map → route → stops → fare → payment → QR.
  - [Chartr app](https://chartr.in/products/chartr-app/); [Chartr fare collection (AFCS)](https://chartr.in/products/afcs/)
- **One Delhi reviews (Jul 2024 and Jan 2025).** An App Store review describes typing a bus number that the app could not resolve to a route. Another says some e-buses were missing. These were reported in the sibling note `hindi_user_voices.md` and not re-verified here. — [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)

#### How the seller code builds one ticket row
1. **Search view.**
   - Rejects anything but `vehicle.category == "BUS"`.
   - With no stops, it returns the full stop/route list (Search 1).
   - With exactly START and END stops, it queues `on_search` with the request's `stops` and **its whole `vehicle` object**.
   - [main/views/search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/search.py)
2. **Search transformer.**
   - Requires exactly two stops plus a vehicle object.
   - Reads the optional `vehicle.variant` ("AC" → AC only, "NAC" → non-AC only, absent → both).
   - Queries the table `stops_pair_new` by start and end stop code.
   - [search_transformer.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/transformers/search_transformer.py); [modules/fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py)
3. **on_search, one item per matching route-variant.**
   - `items[].descriptor.name` is the route name from `stops_pair_new.name`, with code `SJT`.
   - Price is the route fare. Quantity min is 1 and max is 3. Validity is `PT1D`.
   - The TRIP fulfillment carries START, intermediate and END stops, and `vehicle {category: BUS, variant: "AC"/"NAC" from the route's is_ac, registration: <whatever the buyer sent in search, else null>}`.
   - The `ROUTE_INFO` ROUTE_DIRECTION is set to the text "START_CODE to END_CODE", and operational times are fixed at 06:00 and 23:00.
   - Providers are "Delhi Transport Corporation" and "Delhi Integrated Multi-Modal Transit System".
   - The result is cached for 30 minutes.
   - [main/tasks/on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py); [main/constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py)
4. **on_select.** Recomputes base fare and toll from the fare matrix for start stop, end stop, route_id and variant, then caches. — [on_select.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_select.py)
5. **on_init.**
   - Multiplies the price, base fare and toll by the passenger count.
   - Adds the seller's payment parameters, cancellation terms and an empty billing block. The payment terms themselves (collected by the buyer app, settlement window PT1D, static-terms URL) were already in the on_search catalog.
   - Sets the context TTL to `PT03M`; the code's TTL enums are 30 s for on_search and on_select and 180 s for on_init.
   - [on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py); [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py); [main/utils/enums.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/utils/enums.py)
6. **Confirm view.**
   - Requires a payment `transaction_id`.
   - Routes pass orders to `pass_on_confirm` and tickets to `on_confirm`.
   - The active ticket handler is `on_confirm_wo_bus` ("without bus"). The import of an alternative `on_confirm` module is commented out.
   - [main/views/confirm.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/confirm.py)
7. **on_confirm (`on_confirm_wo_bus.py`).**
   - From the cached init data it takes the route name, the provider (mapped to agency DTC or DIMTS), the variant, the start and end stop codes and names, and `fulfillments[0].vehicle.registration` (None if absent).
   - PNR is the buyer's payment transaction_id.
   - The ticket count is `items[0].quantity.selected.count`.
   - Validity is set to **03:00 IST the next day**.
   - It builds an encrypted QR string: creation time, PNR, route, stop names, bus registration, validity, ticket id, fare per ticket, ticket count and agency.
   - **It then creates the `Ticket` row**, before sending on_confirm to the buyer app, with:
     - `ticket_type_id = 1` (category hard-coded to "G" = General)
     - payment type prepaid and payment status completed
     - `amount` = the quote total
     - `vehicle_number` = the registration
     - `is_ac` from the variant
     - `claim_status = CLAIMED`
   - [main/tasks/on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [modules/create_ticket/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/create_ticket/main.py)
8. **on_confirm payload.**
   - QR authorization `{type: QR, token, valid_to, status: "UNCLAIMED" if no bus registration else "CLAIMED"}`.
   - `vehicle {category, variant, registration}`.
   - `created_at` and `updated_at`.
   - [modules/confirm_response_generator.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/confirm_response_generator.py)
9. **Validation.** A `validate_qr` endpoint decrypts a QR string and returns the matching ticket or pass record. — [main/views/validate_qr.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/validate_qr.py)
10. **Housekeeping.**
    - A daily Celery task at 01:00 marks the previous day's CONFIRMED tickets EXPIRED.
    - `TicketUpdate` rows older than 7 days are deleted.
    - [main/tasks/tasks.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/tasks.py); [setup/add_celerytasks.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/setup/add_celerytasks.py); [main/models/tickets.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/tickets.py)
- **Missing or incomplete in the public snapshot.**
  - `main/views/update.py` is imported but absent.
  - The visible Update transformer only edits billing details.
  - A fleet lookup (`fetch_vehicle_data`, by vehicle id from a fleet-data URL) is imported in on_confirm but never called.
  - [main/views/__init__.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/__init__.py); [update_transformer.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/transformers/update_transformer.py); [modules/get_bus_details.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/get_bus_details.py)
- **Column naming.** Django names a foreign-key column by appending `_id`, so the FK `ticket_type` is stored as the column `ticket_type_id`. — [Django docs: ForeignKey database representation](https://docs.djangoproject.com/en/4.2/ref/models/fields/#database-representation)

#### Field dictionary: dataset column → seller code → ONDC message path
Sources for every row: [main/models/tickets.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/tickets.py), [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py), [on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py), [on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py), [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py), [models/models.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/models.py).

| Dataset column | Where the seller code gets it | ONDC message path | Defensible meaning, and caveats |
|---|---|---|---|
| `created_at` | `DateTimeField(auto_now_add=True)`, set when the `on_confirm` task inserts the row. Time zone Asia/Kolkata, PostgreSQL | Roughly `order.created_at` in on_confirm, which the code generates separately with `datetime.now()` | When the seller issued the ticket after the buyer app's post-payment `confirm`. **Not** search time, boarding time or QR-scan time |
| `vehicle_number` | `CharField(32, null)`. Copied from `search.message.intent.fulfillment.vehicle.registration` and echoed through on_search, select and init | Delhi convention: in search. Official spec: `fulfillments[].vehicle.registration` in a vehicle-based confirm or update | Bus registration **supplied by the buyer app** (from a bus QR, a typed number or a selected bus). **NULL if the buyer app sent none.** Not validated by the seller in the public code |
| `route` | `items[0].descriptor.name`, from `stops_pair_new.name` | `items[].descriptor.name` | The seller's route-variant name the rider chose (e.g. 433UP). The UP/DOWN suffix is part of the name; this seller fills ROUTE_DIRECTION with "start code to end code" |
| `start_stop_name`, `end_stop_name` | First and last stop of the chosen fulfillment, named from `stops_pair_new` | `fulfillments[].stops[START/END].location.descriptor.name` | The stop pair the rider **selected for the fare**, in the seller's naming. Not an observed boarding or alighting stop. The codes exist in `start_stop_code` and `end_stop_code`, which are not in the dataset |
| `is_ac` | `vehicle.variant == "AC"`, taken from the chosen route-variant's `is_ac` in the fare table | `fulfillments[].vehicle.variant` (AC/NAC) | Fare variant of the selected route product, **not an observation of the physical bus** |
| `amount` | `quote.price.value` from on_init; the code comment calls it the "discounted amount" | `quote.price.value` | **Total for the whole order (all passengers)**, in INR. Divide by passenger_count for a per-rider fare |
| `passenger_count` | `items[0].quantity.selected.count`. The catalog advertises min 1 and max 3 | `items[].quantity.selected.count` | 1–3 riders on **one QR and one row** |
| `ticket_type_id` | FK to `TicketType`. Set to 1 because the code hard-codes category "G" | Item code `SJT` | Always 1, meaning "General" single-journey ticket. Carries no information. Passes live in a separate `Pass` table |

Columns in the seller table but **not in the dataset**:
- `pnr` (the buyer's payment transaction id)
- `transit_pnr` ("T" + date + random hex)
- `ticket_status` (1 confirmed, 3 pending, 5 cancelled, 7 expired)
- `payment_type`, `payment_status`
- `fare` (an FK to the fare breakup: basic, toll, discount and so on)
- `valid_till`
- `agency` (DTC or DIMTS)
- `start_stop_code`, `end_stop_code`
- **`subscriber_id`**, the buyer app's ONDC `bap_id`
- `description`, `claim_status`, `updated_at`, `active`

— [main/models/tickets.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/tickets.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py)

### Inferences
- **The dataset is almost certainly a subset of the seller's `Ticket` table.** Four independent matches:
  - The column names are identical, including `ticket_type_id`, which is exactly Django's FK column name.
  - `created_at` has microseconds and a +05:30 offset, which fits a PostgreSQL timestamptz read in the Asia/Kolkata zone.
  - `ticket_type_id` is constant at 1, as the code hard-codes.
  - `passenger_count` is capped at 3, the code's constant.
- **A blank vehicle_number means the buyer app's purchase path did not identify a bus at search time.** It does not mean "the bus has no number" or "GPS failure". In the public code there is no seller-side fallback such as an AVL lookup.
- **Claim status disagrees between the message and the table.** The ONDC on_confirm marks such tickets UNCLAIMED, but the DB `claim_status` is set to CLAIMED for every row, so the field is uninformative even if it were exported.
- **Likely coverage.** DTC's terms bar any channel other than ONDC for third-party apps, so the table probably covers all app-sold single-journey tickets for DTC and cluster buses from 2 Sep 2024: One Delhi, Chartr, Tummoc, WhatsApp, Chalo and others, whichever route via this seller.
- **Likely exclusions:**
  - Conductor-machine tickets (cash, UPI, the Universal QR, NCMC) under the Canara Bank system.
  - Passes, which go to a separate `Pass` table.
  - Women's free travel (pink tickets, Pink Saheli card).
- **Possible rough scale.** The sibling note `hindi_user_voices.md` quotes a coordinator figure of 2.56M tickets for October 2026, about 83K a day. If right, Delhi buses would be roughly a quarter of ONDC's 300–375K daily metro and bus tickets. This is a rough cross-source inference.

### Gaps
- No source says which buyer apps put `vehicle.registration` (or `variant`) into their search, or how they obtain it (bus QR content, typed number, or a bus picked on a live map).
- The production code version in October 2026 is unknown. Whether post-confirm vehicle updates (the official "with update call" or user-based flows) are written into `vehicle_number` cannot be checked, because the update view is missing from the public repo.
- No dated announcements were found for Chartr, Tummoc or WhatsApp going live as ONDC buyer apps for Delhi buses.
- No ONDC-seller tender or contract documents were found. The only 2026 JICA DXLab procurement found is a vendor contract, not this platform.
- No source says whether the in-bus QR stickers (the 2021 seat-back stickers, Tummoc's QRs, or the 2025 Universal QR) encode the bus registration, or whether a Universal QR payment becomes an ONDC order.

## 3. Ticket lifecycle: what `created_at` means, validity window, buying before boarding, and validation

### Takeaway
`created_at` is when the seller created the ticket on receiving the buyer app's post-payment `confirm`. In practice that is the ticket issue time: seconds after the rider paid, and a little after the moment the rider chose the route (and, where present, the bus) at search. In the seller code a ticket does not need a bus, is valid until 03:00 IST the next day, and is checked by conductors or inspectors scanning the QR against the seller's records. Individual apps add their own rules on top; Tummoc, for example, activates the ticket on board for 30 minutes.

### Cited Findings
- **When the row is written.** `Ticket.created_at` is `auto_now_add`, filled when the row is inserted inside the `on_confirm` Celery task. That task runs only after the buyer app's `confirm`, which must carry a payment transaction id; ticket_status is 1 when the payment status is PAID. — [models/models.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/models.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [views/confirm.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/confirm.py)
- **The README places Confirm after payment is completed on the buyer side.** — [README](https://github.com/transport-stack/ondc-buses-seller/blob/main/README.md)
- **Time limits on the transaction.**
  - Search, select and init data are cached for 1,800 s (30 min).
  - on_init sets TTL `PT03M`; on_search and on_select TTLs are 30 s.
  - If `confirm` arrives after the cache expires, on_confirm fails with no ticket data and no row is created.
  - [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py); [enums.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/utils/enums.py); [on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py)
- **Payment.** The buyer app collects payment and settles to the Transport Department T+1, with a reconciliation call. — [DTC static terms](https://cdn-delhi.transportstack.in/ondc-seller/DTC_static_terms.pdf); [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py)
- **Validity in the seller code.**
  - The catalog item says `PT1D`.
  - `valid_till` and the QR's `valid_to` are set to 03:00 the next day, IST. The code appends "Z" to this local time, so it is mislabelled as UTC in the message.
  - The daily 01:00 job expires the previous calendar day's confirmed tickets.
  - [on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [tasks/tasks.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/tasks.py)
- **Cancellation.** Both the spec examples and the seller code offer cancellation within PT60M at 0% fee. The spec examples use validity `PT2D` with an end-of-day `valid_to`. — [on_confirm example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/on_confirm/example_0.yaml); [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py)
- **Claim states in the spec.** QR tickets can be UNCLAIMED or CLAIMED. The user-based confirmation flow (Aug 2025) issues them UNCLAIMED and lets the buyer app mark them CLAIMED later. — [enum Fulfillment.yaml](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/enum/Fulfillment.yaml); [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md)
- **[older] Activation was planned from the start.** ONDC's 2023 requirements document already allowed a ticket to be activated before the journey starts. — [ONDC BRD v1, Aug 2023](https://docs.google.com/document/d/1i2ZdcfZ40HValk-fLAHo41jEbfml3vEr/)
- **Tummoc (June 2024).**
  - Book on the go.
  - Once on the bus, activate the ticket; it stays active for 30 minutes.
  - Validate by scanning the bus QR or typing the bus number.
  - Tummoc says validation helps DTC understand route demand and ridership.
  - [Tummoc blog](https://blog.tummoc.com/?p=2344)
- **DTC WhatsApp (April 2024).** Choose start and destination stops, buy up to six tickets per transaction, pay by UPI inside the chat. — [Business Today](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11)
- **Chartr on validation.** Conductors and inspectors scan the ticket QR to verify it; mobile tickets are time-bound to prevent reuse. — [Chartr app](https://chartr.in/products/chartr-app/); [Chartr AFCS](https://chartr.in/products/afcs/)
- **Draft 2.1.0 (Nov 2025)** adds agent/POS flows for selling through ONDC on conductor devices. — [changelog 2.1.0](https://github.com/ONDC-Official/mobility-specification/blob/draft-TRV11-2.1.0/api/components/docs/changeLog/TRV11_2.1.0_141125.md)

### Inferences
- **Read `created_at` as the ticket-issue timestamp:** payment success plus a few seconds of network and queue delay. For tickets with a vehicle number, the bus was identified earlier, at search. The gap is the time spent selecting, initialising and paying. The code bounds it to under 30 minutes, and the 3-minute init TTL suggests it is usually short, probably about 0.5–3 minutes, though this is not measured. The Celery queue can only make `created_at` *later*, never earlier.
- **`created_at` is the seller server's clock, not the AVL clock.** Check for offsets before joining to GPS data.
- **Buying before boarding is allowed by the seller.** No bus is required, and validity runs to 03:00 the next day. Blank-vehicle rows can therefore include pre-boarding purchases (at the stop, or chat and "route" flows) as well as on-board purchases where the rider simply picked the route.
- **One row can stand for up to three riders**, all on the same QR.
- **Quirk: a ticket bought just after midnight gets about 27 hours of validity**, because the code sets "tomorrow 03:00" relative to the purchase time. The 01:00 expiry job, which works on calendar days, is what limits stale tickets in the database.

### Gaps
- No 2025–26 official source says how conductors actually verify ONDC bus tickets (device scan or visual check), or whether the seller enforces one use per ticket.
- Whether the production seller or the buyer apps enforce activation windows beyond Tummoc's documented 30-minute rule is unknown.

## 4. Does any Transport Stack, IIIT-Delhi (CSM), Chartr or ONDC publication describe this ticket dataset, its coverage or known quirks?

### Takeaway
No. I found no publication that documents the ONDC ticket dataset, its coverage or its quirks. The open seller code is the closest thing to a data dictionary. Chartr and ONDC publish only aggregate counters.

### Cited Findings
- **Delhi Transport Stack's published offerings** are open GTFS, GTFS-RT and a journey-planner API. Ticket data is not listed. — [Chartr – Delhi Transport Stack](https://chartr.in/products/transport-stack/)
- **JICA DXLab** describes integrating 20+ static and real-time datasets across six operators in the first phase, without naming ticket data. — [JICA DXLab](https://www.jica.go.jp/english/about/dx/jicadx/dxlab/dpi_dpg/index.html)
- **ONDC publishes network totals only:** 300K+ daily metro and bus tickets, 375K+ in June 2026. There is no Delhi bus breakdown. — [ONDC public transport](https://ondc.org/pages/public-transport.html); [ONDC about-us](https://ondc.org/pages/about-us.html); [StartupTalky](https://startuptalky.com/news/ondc-drives-public-transport-digitisation/)
- **Chartr publishes only cumulative counters**, undated: 6.04 crore+ ONDC orders and ₹90.69 crore+ seller amount. — [Chartr ONDC blog](https://chartr.in/blog/ondc/)
- **IT for Change's May 2026 policy paper** discusses the Delhi Transport Stack as digital public infrastructure and Beckn/ONDC in general. It contains nothing on ticket data. — [IT for Change, "The DPI Turn in India's Urban Transportation Policy"](https://itforchange.net/sites/default/files/2026-05/The%20DPI%20Turn%20in%20India%E2%80%99s%20Urban%20Transportation%20Policy_.pdf)
- **Implementation quirks visible in the seller code** (beyond §2–§3):
  - Start and end stop GPS in the catalog is the placeholder "0.000000".
  - Operational start and end times are fixed at 06:00 and 23:00 of the current date.
  - `PINK_TICKET_FARE = 10.0` is defined and imported but unused in the active path.
  - `DISCOUNT = 0.10`: on_init overwrites the *last* quote-breakup entry with 10% of the base fare. In the on_select quote that last entry is the TOLL line, not an OFFER line. On_confirm then reads only an OFFER line (absent) as the discount and stores the quote total as `amount`. How the advertised 10% digital discount reaches `amount` cannot be traced in the public code.
  - A commented debug line compares the bus registration with the *string* `'None'`.
  - No `cancel` endpoint is registered in the public URL config, although the seller advertises cancellation terms (PT60M, 0% fee).
  - [on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py); [fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py); [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py); [on_select.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_select.py); [on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [main/urls.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/urls.py)
- **Context on women's free travel.** Delhi's Pink Saheli smart card for free travel by women and transgender residents on DTC and cluster buses was launched in late 2025 and is replacing pink paper tickets. Such journeys are free and outside the paid ONDC flow. — [Free Press Journal (snippet only)](https://www.freepressjournal.in/india/delhi-govt-launches-pink-saheli-smart-card-to-provide-free-travel-for-women-transgender-commuters-across-dtc-buses)

### Inferences
- **Quirks the team should treat as known, all from the code:**
  - `ticket_type_id` is constant.
  - `passenger_count` is capped at 3.
  - `amount` is the order total.
  - `is_ac` is the chosen fare variant, not the bus.
  - Stop names follow the seller's fare table, which may not match GTFS names or IDs (a likely source of the stop-name mismatches).
  - `vehicle_number` is unvalidated buyer input that may contain placeholder strings.
  - `route` is the rider-chosen route-variant.
- **Coverage skews.** Paid riders only. Resident women and transgender riders largely travel free on Pink Saheli cards and so are under-represented. Pass holders and cash or conductor-machine riders are absent.

### Gaps
- No organiser documentation was found on how the hackathon extract was filtered: for example, whether it keeps only CONFIRMED and EXPIRED rows, includes cancelled ones, or drops `subscriber_id` deliberately.
- No IIIT-Delhi CSM, Chartr or Transport Stack paper on ONDC ticket-data quality was found.

## 5. Plausible explanations for the October 2026 patterns (a)–(d)

### Takeaway
All four patterns fit the seller code's mechanics:
- **Blank vehicle numbers arise per purchase path** (buyer app or in-app flow), not per bus or per route.
- **`ticket_type_id` and the 1–3 passenger range are hard-coded.**
- **`created_at` is the post-payment confirm time, while the bus is identified earlier, at search.**

The one decisive variable the team lacks is the buyer-app id (`subscriber_id`, the ONDC `bap_id`). The seller table stores it, but the dataset leaves it out. Ask the organisers for it, together with `agency`, the stop codes, `valid_till` and `ticket_status`.

### Cited Findings
- **Where the vehicle number comes from.** `vehicle_number` is copied from the search request's `vehicle.registration` and is None when absent. The seller does not derive it from fleet or AVL data in the active code. — [on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [get_bus_details.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/get_bus_details.py)
- **How AC/non-AC options are returned.** Without a variant in the search, the seller returns both AC and non-AC route-variants for the stop pair and the rider picks one. With a variant, it filters. — [search_transformer.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/transformers/search_transformer.py); [fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py)
- **Channels that pick stops without a bus step:**
  - The WhatsApp bot (start and destination stops, up to six tickets).
  - The Chartr app (route, stops, AC or Non-AC).
  - Tummoc (buy anytime, then validate on board with the bus QR or bus number).
  - [Business Today](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11); [Chartr app](https://chartr.in/products/chartr-app/); [Tummoc](https://blog.tummoc.com/?p=2344)
- **Chalo's Delhi flow.** Hindi press reportedly describes it as route plus destination selection, with no bus step. This comes from the sibling note and was not re-verified. — [Amar Ujala, 24 Sep 2025](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
- **Channels that identify a bus:**
  - One Delhi: bus QR or typed bus number. The App Store review was reported in the sibling note and not re-verified.
  - Chartr: its fare-collection page describes a flow that starts from a live bus on the map.
  - [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010); [Chartr AFCS](https://chartr.in/products/afcs/)
- **Hard-coded values.** `GENERAL_TICKET_TYPE_ID = 1`, the ticket category is hard-coded "G" (giving 1), `MIN_PAX_COUNT = 1` and `MAX_PAX_COUNT = 3`. Pass orders go to a separate handler and table. — [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py); [on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py); [views/confirm.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/confirm.py)
- **Ticket limits elsewhere.** The ONDC spec examples allow up to six tickets per order, and the pre-ONDC WhatsApp bot allowed six per transaction. — [on_search example](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/examples/intra_city/on_search/example_0.yaml); [Business Today](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11)
- **Timing.** The bus is captured at search; `created_at` is set at on_confirm after payment, within a 30-minute cache window with a 3-minute init TTL. — [constants.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/constants.py); [on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py)
- **Fares differ by bus type.** Delhi charges more on AC (electric) buses than non-AC: a minimum of ₹10 versus ₹5. — [Down To Earth (snippet only)](https://www.downtoearth.org.in/air/india-on-e-wheels-punes-uniform-fares-for-ac-and-non-ac-buses-could-offer-model-for-public-transport)

### Inferences

**(a) 48.5% blank vehicle numbers, uniform across routes; AC 49.8% vs non-AC 43.2%; same mean fare**
- **Most defensible reading.** A blank marks a purchase path that never identified a bus: route/stop-only flows (the WhatsApp bot, Chalo, Chartr's route-and-stops mode, pre-boarding purchases) as opposed to bus-QR, bus-number or live-bus flows. Every major channel sells on every route, so a channel-mix mechanism naturally gives a similar 30–70% blank share almost everywhere.
- **Bus- or route-level causes are less likely.** Missing stickers on certain buses, a depot that is not onboarded, or AVL gaps would instead show clustering by vehicle or depot.
- **"Same mean fare"** for blank and non-blank rows means similar trip lengths. That again points to the channel, not to the kind of journey.
- **Possible causes of the 6.6-point AC gap (all unproven):**
  - A different app mix on AC-heavy corridors.
  - Bus lookup failing more often for newer e-buses. Riders reported some e-buses missing from One Delhi (sibling note), which would push AC riders towards route/stop flows.
  - Defaults in the AC/non-AC choice when no bus is known.
- **If "same mean fare" instead means AC and non-AC have the same mean fare,** that conflicts with Delhi's differential AC and non-AC fares. In that case check `amount / passenger_count` by `is_ac`, since `is_ac` is the chosen product, not the bus.
- **Checks:**
  - Look for placeholder strings in `vehicle_number` (`'None'`, `''`, `'null'`, `'0'`, `'NA'`), and include them in the blank share.
  - Check the registration format.
  - Using AVL, check that the vehicle was actually running the ticket's `route` near `created_at`.
  - Count how many AVL-active buses never appear in tickets.

**(b) Sunday 18 Oct 2026: 14.8% blank vs 36–38% on neighbouring days**
- **Under the mechanism above, a one-day drop in blanks means a one-day shift in channel mix or behaviour:**
  - An outage, maintenance window, payment-gateway or ONDC-integration fault at a blank-producing channel such as a stop-based app or the chatbot.
  - A one-day campaign or feature change that pushed bus scanning.
  - A data artefact, such as one buyer app filling a default registration.
- I found no public report of a Delhi bus-ticket app outage in October 2026 (see Gaps).
- **The mid-month level is itself informative.** The neighbouring days at 36–38% are well below the monthly 48.5%, so the blank share probably trends or steps during the month. A channel launch, promotion or app change is again the natural cause.
- **Checks:**
  - Daily counts of blank and non-blank rows, not shares. If blank rows collapsed on 18 Oct while non-blank rows stayed at a normal Sunday level, a blank-producing channel was down. If total volume held but more rows had vehicles, it was a behaviour or feature change.
  - The hour-of-day profile on 18 Oct, to look for an outage window.
  - The number of distinct `vehicle_number` values and the top values on 18 Oct. One value repeated across many routes would point to a default-value bug.
  - The `passenger_count` and `amount` distributions on that day.
  - A daily plot of the blank share across the whole month.

**(c) `ticket_type_id` always 1; `passenger_count` 1 (93%), 2 or 3**
- Both are by construction:
  - The seller hard-codes the "General" ticket type (id 1).
  - The catalog caps quantity at 3, below the six allowed by ONDC's examples and the old WhatsApp bot.
  - Concession types (SFSJT) and passes are not in this table.
- **Treat each row as one order (one QR) for 1–3 riders.** Use `passenger_count` as a ridership weight, and per-rider fare = `amount / passenger_count`.

**(d) Rows with a vehicle number: median purchase 0.8 min after the bus passed the boarding stop; 23% bought before it arrived**
- **A median 0.8 min after passing fits on-board purchase:** board, scan the in-bus QR or type the bus number, pay by UPI. `created_at` is stamped only after payment, at confirm.
- **Plausible reasons for the 23% "before arrival":**
  1. **The bus is identified before boarding.** Chartr's flow starts from a live bus on the map, and One Delhi and Tummoc accept a typed bus number, so a rider at the stop can pick or type the approaching bus.
  2. **The chosen start stop is not the real boarding stop.** It is a fare-stage choice (§2); riders may pick a nearby or bigger stop with the same fare, which moves the computed passing time.
  3. **AVL timing error.** Ping interval, latency, stop-matching geometry or stop-coordinate offsets.
  4. **Clock or time-zone misalignment** between the seller server and the AVL feed.
  5. **The wrong bus.** The registration is unvalidated, so a rider can select the next or a previous bus on the same route.
- **Server delays cannot explain early purchases.** Celery or network delays only make `created_at` later.
- **Recommendation:** treat `created_at − passing time` as noisy, and use the vehicle-number subset to calibrate boarding-time inference. Do not assume `start_stop_name` is the actual boarding stop.

### Gaps
- Without `subscriber_id`, the buyer-app explanation for (a) and (b) cannot be tested directly from the dataset.
- No outage, maintenance or campaign report for 18 Oct 2026 was found in web searches on 16 Nov 2026. The searches covered Delhi bus-ticket app outages in October 2026 and DTC/ONDC news.
- Which production code ran in October 2026, including whether post-confirm vehicle updates fill `vehicle_number`, is unknown. If they do, the blank share could depend on when the extract was taken.
- The typical gap between search and confirm in Delhi is not published, so the lag between bus identification and `created_at` can only be bounded (under 30 minutes), not measured.
