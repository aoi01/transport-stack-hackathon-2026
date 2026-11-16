# Where the stop names in Delhi ONDC bus e-tickets come from, and which stop IDs or stop lists can be obtained (as of 16 Nov 2026)

Scope and conventions:
- **Prior notes.** This note builds on `../デリーのバス乗車券の電子購入/ondc_data_semantics.md` (the seller `Ticket` table, the ONDC flow) and `../停留所名の照合と通過検出/transit_stop_matching.md` (the 88.8% / 32.9% split by `fare_stage` flags). It does not repeat them.
- **Code reading.** On 16 Nov 2026 I cloned all 17 public repos of the `transport-stack` GitHub organisation, plus the ONDC `mobility-specification` branches `release-TRV11-2.0.1` and `draft-TRV11-2.1.0`, and read them. Links point to the files on GitHub.
- **No live endpoints were called.** No account was created and nothing was sent from `data/`.
- **Local check** marks a computation I ran on the team's own files (`data/raw/ticketing/October-Delhi.csv`, `data/raw/gtfs_static/` v32, `data/processed/*.parquet`). All Local checks ran on this machine; no data left it.
- **Inferences** are my reasoning, not documented facts.

**Bottom line**
- **The source of the ticket names.** The ticket stop names come from the ONDC seller's own route–stop master. In the public code this lives in a separate PostgreSQL database called `transit_db`, in the tables `stops_new`, `routes_new` and `stops_pair_new`. It is not built from the team's GTFS v32 at sale time.
- **Stop codes.** The seller's stop "codes" are upper-case slugs of the stop name, such as `TILAK_BRIDGE`. They are not the GTFS 8-hex `stop_code`.
- **What to request.** The most useful item is a snapshot of `stops_new`, `routes_new` and `stops_pair_new` (route, stop name, code, sequence, lat/lon, fare). Second is the journey planner's internal GTFS-stop → ticket-code mapping (`tkt_code`). Third are the DTC/DIMTS ETM stage masters.

```
GTFS editor (Chartr; fare stages are set per route in its Route Editor)
   └─(at some date, from each route's first trip: stop_name, lat, lon, order)─► seller "transit_db"
        routes_new / stops_new (route_id, name, code = SLUG(name), sequence_in_route, lat, lon)
        stops_pair_new (route_id, is_ac, start/end code, start/end name, start/end sequence, fare_details {bf, tl})
            │  ONDC "Search 1" (no stops)  → full catalog: ROUTE fulfillments + one STOPS fulfillment {name, code, gps}
            │  ONDC "Search 2" (START/END codes) → per-route TRIP items: start/intermediate/end {name, code}, fare
            ▼
   Buyer apps (One Delhi, Chartr, Tummoc, WhatsApp, Chalo …) show the seller's stop list; the rider picks start and end
            ▼
   on_confirm → Ticket row: start/end_stop_name (seller name), start/end_stop_code (slug), route = seller route name
            ▼
   Hackathon CSV: names only; every name has been passed through a Python-style title-case (export step or seller master, unknown)
```

## 1. In the ONDC mobility spec and the Beckn mobility examples, how are stops represented in search, on_search, select, init and confirm? Do Delhi or bus examples use codes shaped like GTFS `stop_code` or `stop_id`?

### Takeaway
In ONDC TRV11 (intracity bus), a stop is a `fulfillment.stops[]` element with `type` (START, END, INTERMEDIATE_STOP, TRANSIT_STOP), `location.descriptor.code`, `location.descriptor.name` and `location.gps`. The code is an opaque string chosen by the seller (the BPP), and the spec puts no constraint on it. Every Delhi-modelled example uses upper-case name slugs such as `KASHMERE_GATE` and `GREATER_KAILASH`. No ONDC example uses a GTFS-style hex `stop_code` or a numeric `stop_id`. The Beckn v2 bus example uses operator-defined IDs (e.g. `BLR-STOP-SILKBOARD-01`) and has no GTFS binding either.

### Cited Findings
- **Attribute dictionary (2.0.1).**
  - In search, `stops.location.descriptor.code` is OPTIONAL, owned by the BAP, with `gps` as the alternative.
  - In on_search, `descriptor.code` and `descriptor.name` are OPTIONAL, owned by the BPP. The usage examples are `INDIRA_GANDHI_TECHNICAL_UNIV` and "Indira Gandhi Technical Unviversity", and the description is only the generic "Physical description of something."
  - `stops.id` is described as a "Unique reference ID for individual stop", and `parent_stop_id` links each stop to the previous one.
  - No namespace is defined for stop codes; nothing ties them to GTFS.
  - Stop types are enumerated as START, END, INTERMEDIATE_STOP and TRANSIT_STOP.
  - [attributes/intracity-bus/index.yaml, release-TRV11-2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/attributes/intracity-bus/index.yaml); [enum Fulfillment.yaml, release-TRV11-2.0.0](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.0/api/components/enum/Fulfillment.yaml)
- **Search 1 → catalog of all routes.** `search` carries only `vehicle.category: BUS`. The on_search catalog then holds:
  - `ROUTE` fulfillments: ordered stop ids (`START` → `INTERMEDIATE_STOP` with `parent_stop_id` → `END`), with a `ROUTE_INFO` tag (`ROUTE_ID` such as '242', `ROUTE_DIRECTION` UP/DOWN).
  - One `STOPS` fulfillment listing every stop as `{id, location.descriptor {name, code}, gps}`, e.g. `kashmere gate`/`KASHMERE_GATE`, `gpo`/`GPO`, `dhaula kuan`/`DHAULA_KUAN`, `Greater Kailash`/`GREATER_KAILASH`.
  - [search example 2](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/search/Search_for_intra_city_bus_service,_with_city_and_type_of_vehicle_2.yaml); [on_search catalog example 21](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_search/Return_a_public_transit_catalog_of_all_routes_in_serverd_21.yaml)
- **Search 2 → fare products.**
  - `search` sends START and END as codes only: `KASHMERE_GATE` → `GREATER_KAILASH`.
  - on_search returns `TRIP` fulfillments whose stops carry name, code and gps for START, every INTERMEDIATE_STOP and END.
  - [search example 3](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/search/Search_for_intra_city_bus_service,_with_city_and_type_of_vehicle_3.yaml); [on_search fare products example 19](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_search/Return_a_public_transit_catalog_of_fare_products_19.yaml)
- **select, init and confirm.**
  - The buyer's `init` and `confirm` refer to fulfillments by id only (e.g. F1, F5) and carry no stop descriptors.
  - The seller's `on_select`, `on_init` and `on_confirm` echo the TRIP fulfillment with all six stops `{name, code, gps}`. The per-passenger `TICKET` fulfillments carry the QR `authorization` on a START stop that has no descriptor.
  - Local reading of the 2.0.1 examples: [on_select 26](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_select/Return_a_quote_offered_by_a_public_transit_service_provider_26.yaml); [init 7](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/init/Initialize_the_order_by_providing_billing_details_7.yaml); [on_init 28](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_init/Return_draft_order_for_transit_ticket_with_settlement_via_payment_link_28.yaml); [on_confirm 30](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_confirm/Return_confirmed_ticket_order_with_payment_confirmation_30.yaml)
- **The same slug codes in draft 2.1.0.** Draft 2.1.0 (Nov 2025 onward) keeps the same Delhi slug codes: `KASHMERE_GATE`, `GREATER_KAILASH`, `INDIRA_GANDHI_TECHNICAL_UNIV`, `YAMUNA_BAZAR`, `GPO`, `DHAULA_KUAN`, with city `std:011` and provider "Delhi Transport Corporation". — [draft-TRV11-2.1.0 intracity-bus examples](https://github.com/ONDC-Official/mobility-specification/tree/draft-TRV11-2.1.0/api/components/examples/intracity-bus)
- **The GTFS tag is not a stop key.** The only GTFS hook in TRV11 is a `SCHEDULED_INFO` tag group with a `GTFS` tag, added on 10 Nov 2025. Its example value is a URL (`https://api.transit-solutions/gtfs-realtime`), placed at order level in on_confirm, on_status and on_cancel. — [changelog 2.0.1](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/docs/changeLog/TRV11_2.0.1_200924.md); [on_confirm example 30](https://github.com/ONDC-Official/mobility-specification/blob/release-TRV11-2.0.1/api/components/examples/intracity-bus/on_confirm/Return_confirmed_ticket_order_with_payment_confirmation_30.yaml)
- **Beckn v2 mobility public-transit bus guide (BMTC scenario, examples added 2 Mar 2026).**
  - The search is stop-to-stop by `descriptor.name`, e.g. "Silk Board Bus Stop".
  - Stops appear as `mobility:Stop` with operator IDs such as `BLR-STOP-SILKBOARD-01`, and as `STOP_ID` / `STOP_NAME` tag values.
  - GTFS appears only in the repo's standards survey.
  - [beckn/mobility public_transit_bus README](https://github.com/beckn/mobility/blob/main/docs/example_implementations/public_transit_bus/README.md); [beckn/mobility repo](https://github.com/beckn/mobility)
- **Local check: the slug rule reproduces the codes.** The rule is upper-case of `re.sub(r'\W+', '_', name.strip(punctuation))`.
  - It reproduces 18 of 20 code/name pairs in the spec examples and the seller test fixtures, including all 11 pairs from the seller's 2024 pre-prod exchange.
  - Both misses look hand-written: `INDIRA_GANDHI_TECHNICAL_UNIV` (spec example, truncated) and `SHAHEED_STHAL` (seller cancel fixture with placeholder GPS, dropping "(New Bus Adda)").
  - Sources: the spec examples above; [seller fixture stored_search_data.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/stored_search_data.json)

### Inferences
- The protocol forces no shared stop ID across sellers. In Delhi the stop key is whatever the seller chose, and every Delhi example points to name slugs. A ticket's `start_stop_code` is therefore very unlikely to be a GTFS `stop_code` such as `9CE15308`.
- Under the spec, the catalog a buyer app receives already contains every stop of every route, with order (`parent_stop_id`) and GPS. Any stop list an app shows is a rendering of the seller's catalog unless the app overrides it (see §3).

### Gaps
- The production seller's actual code values in October 2026 cannot be observed without being an ONDC-registered buyer app. Whether production adds suffixes to tell same-named stops apart is unknown.
- I did not open the rendered ONDC developer guide (a web app). Field optionality above comes from the YAML attribute files.

## 2. In the transport-stack GitHub organisation: is there code that loads GTFS stops, routes or fares into the seller? Which feed and fields? How are fare stages and the fare matrix built? Any clue why names differ on routes without `fare_stage` flags? Any public fixtures with Delhi stop names?

### Takeaway
No public code in the organisation loads GTFS into the seller. At runtime the seller reads an external, read-only route–stop–fare master from a PostgreSQL database called `transit_db` (tables `routes_new`, `stops_new`, `stops_pair_new`; legacy tables `routes`, `stops`, `all_routes`), and `data/fare_matrix/` is git-ignored.

Several pieces of evidence point to an older snapshot of Chartr's GTFS as the origin of that master:
- **Format.** The legacy `stop_details` layout is the same `[stop_id, stop_name, lat, lon]` list that the ETA calculator builds from each GTFS route's first trip.
- **Coordinates.** Coordinates in the seller's 2024 fixtures equal some GTFS v32 coordinates exactly.
- **Ticket codes.** The journey planner carries a per-GTFS-stop `tkt_code`, which it sends to the seller's `fetch_fare`.

Fares are stored per stop pair, not per stage: `stops_pair_new.fare_details {bf, tl}` and the legacy `routes.fare_matrix[start_seq][end_seq]`.

Why names diverge on routes without flags: **local checks** show that on those routes the ticket names still follow the seller's older, often abbreviated naming (e.g. "Ito Bsz Marg", "S.J. Hospital", "Kashmere Gate City (T)"), while GTFS v32 renamed or re-digitised those stops. On flagged routes, GTFS and the seller names agree (90.8% by the slug key).

### Cited Findings

**Where the seller gets routes, stops and fares (`transport-stack/ondc-buses-seller`; public snapshot first committed 6 May 2025; last migration 20 Jan 2025)**
- **Database.** Production settings define a second database `transit_db` (env `TRANSIT_DB_NAME/USER/PASS/HOST`) beside the ticket DB `default`. — [settings/production.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/settings/production.py); [settings/development.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/settings/development.py)
- **Fare and stop queries (`FareCalculator`)** run on `connections['transit_db']`:
  - `select fare_details from stops_pair_new where start_stop_code = %s and end_stop_code = %s and route_id = %s and is_ac = %s`.
  - `select * from stops_pair_new where start_stop_code = %s and end_stop_code = %s [and is_ac = %s]`. The columns used are `route_id`, `name` (the route name), `agency`, `is_ac`, `fare_details` (JSON `{"bf": base fare, "tl": toll}`), `start_stop_name`, `end_stop_name`, `start_sequence` and `end_sequence`.
  - `select * from stops_new where route_id::int in (...)`. Intermediate stops are rows `start_sequence+1 … end_sequence-1`, emitted as `{name, code}`.
  - Start and end GPS are hard-coded to "0.000000".
  - [modules/fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py)
- **Legacy queries (`_main.py`)** used the tables `stops(route_id, name, code, sequence_in_route)` and `routes(route_id, name, agency, is_ac, is_active, fare_matrix, stop_details)`:
  - fare = `routes.fare_matrix::jsonb #>> array[start_sequence, end_sequence]`;
  - start/end lat and lon = `stop_details #>> array[seq,'2']` and `array[seq,'3']`;
  - routes for a stop pair need `a.code = start AND b.code = end AND a.sequence_in_route < b.sequence_in_route AND r.is_active`.
  - [modules/fare_setup/_main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/_main.py)
- **Commented-out models.**
  - An unmanaged `Route` model maps table `all_routes` (`route_id`, `route_long_name`, `agency`, `stop_details`, `is_ac`, `fare_matrix`).
  - `Stop` has `route`, `stop_name` and `stop_pos`.
  - A DB router sends reads of `all_routes` to a read-only database alias `chartr` and forbids writes.
  - [main/models/routes.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/routes.py); [settings/routers.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/settings/routers.py); [main/models/managers.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/managers.py)
- **No loader in the repo.** `data/fare_matrix/` contains only a `.gitignore`. I found no management command, script, fixture or migration that creates or fills `stops_new`, `routes_new`, `stops_pair_new`, `routes` or `stops`; migrations `0002` delete the early `Stop`/`Route` models. — [data/fare_matrix/.gitignore](https://github.com/transport-stack/ondc-buses-seller/blob/main/data/fare_matrix/.gitignore); [migrations folder](https://github.com/transport-stack/ondc-buses-seller/tree/main/main/migrations)
- **Search 1 sends the whole master to buyer apps.** A search without stops triggers `on_search_all_route_stops`, which:
  - pages through `stops_new JOIN routes_new` per agency (`DTC`, then `DIMTS`), 3,000 rows per page;
  - selects `s.name, s.code, s.route_id, r.agency, r.name, s.latitude, s.longitude, s.sequence_in_route`, ordered by route and sequence;
  - posts ONDC on_search pages to the buyer's `bap_uri` with `ROUTE` fulfillments (ROUTE_ID = route name without UP/DOWN, ROUTE_DIRECTION) and one `STOPS` fulfillment holding `{name, code}` and `gps = "lat, lon"` for every stop.
  - [main/tasks/ondc_all_route_search_.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/ondc_all_route_search_.py); [main/views/search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/search.py)
- **The ticket's names and codes come from the seller, not the buyer app.**
  - In on_search, the START/END `code` is the code the buyer sent; the `name` is `stops_pair_new.start_stop_name`/`end_stop_name`.
  - on_select builds from the seller's cached on_search; on_init builds from the cached on_select.
  - `on_confirm_wo_bus` reads `start_stop_code/name` and `end_stop_code/name` from the seller's cached on_init (`fulfillments[0].stops[0]` and `[-1]`) and writes them to `Ticket`.
  - [main/tasks/on_search.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_search.py); [main/tasks/on_select.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_select.py); [main/tasks/on_init.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_init.py); [main/tasks/on_confirm_wo_bus.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/on_confirm_wo_bus.py)
- **`Ticket` fields** (Django default table `main_ticket`): `start_stop_name` / `start_stop_code` / `end_stop_name` / `end_stop_code` (each `CharField(80)`), `route` (50), `agency` (FK to table `agency`), `fare` (one-to-one to `FareBreakup`: basic, toll, discount, coupon_discount, amount, …), `subscriber_id`, `valid_till`, `ticket_status`, `pnr`, `transit_pnr`, `claim_status`. — [main/models/tickets.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/tickets.py); [main/models/fare_setup.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/fare_setup.py)
- **Missing views.** A `fetch_fare` route is registered, but `main/views/fetch_fare.py` and `update.py` are absent from the public snapshot. — [main/urls.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/urls.py); [main/views/__init__.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/views/__init__.py)

**Other repos that link GTFS to ticket codes**
- **Journey planner (`get_bus_fare`).** It POSTs `{start_stop_code, end_stop_code, route_id, variant}` to `https://pre-prod-ondc-ticketing-api-delhi.transportstack.in/fetch_fare`, using each stop's `tkt_code`. — [journey-planner modules/bus_fare.py](https://github.com/transport-stack/journey-planner/blob/main/modules/bus_fare.py); [algorithms/bus/core.py](https://github.com/transport-stack/journey-planner/blob/main/algorithms/bus/core.py)
- **Journey planner (bus stops).**
  - Bus stops load from `data/GTFS/bus/stops.txt`. If that file has a `tkt_code` column it is used; otherwise `tkt_code = ''`.
  - A location's default `tkt_code` is `clean_stop_name(name)`: strip punctuation, then `re.sub(r'\W+', '_', name)`. This is the same slug rule, without upper-casing.
  - A separate `data/meta/mapped_stops.pkl` maps metro to bus stops.
  - [models/models.py](https://github.com/transport-stack/journey-planner/blob/main/models/models.py); [envs/.env.module.bus.dev](https://github.com/transport-stack/journey-planner/blob/main/envs/.env.module.bus.dev); [algorithms/bus/config.py](https://github.com/transport-stack/journey-planner/blob/main/algorithms/bus/config.py)
- **ETA calculator (first commit 10 Sep 2024).**
  - It builds a table `all_routes(route_id, stop_details)` from GTFS. `stop_details` is the string of `[stop_id, stop_name, stop_lat, stop_lon]` for the stops of each route's first trip.
  - Its `stops` table copies GTFS `stop_code` into an Integer column.
  - [eta-calculator modules/utils.py](https://github.com/transport-stack/eta-calculator/blob/main/modules/utils.py); [modules/db_models.py](https://github.com/transport-stack/eta-calculator/blob/main/modules/db_models.py)
- **Chartr ONDC buyer backend (`ondc-micro-mobility-buyer`, initial commit 19 Jun 2025).**
  - It has a view that saves an incoming route/stop catalog as `data/static_stops_data/routes_and_stops.json` (zipped).
  - A test list `routes.json` has 50 Delhi `(start_stop_code, end_stop_code, route_id = route name)` entries, e.g. `WEST_ENCLAVE_SANSAD_VIHAR_T` → `DEV_NAGAR` on `993DOWN`, and `BADARPUR_BORDER_T` → `RK_PURAM_SEC_1` on `544DOWN`.
  - Its bus estimate call sends `start_stop_code`, `end_stop_code`, `route_id` (route name), `variant`, `bus_reg_num` and `category`.
  - [views/on_search_route_stops.py](https://github.com/transport-stack/ondc-micro-mobility-buyer/blob/main/ondc_buyer_backend/views/on_search_route_stops.py); [routes.json](https://github.com/transport-stack/ondc-micro-mobility-buyer/blob/main/ondc_buyer_backend/routes.json); [locustfiles/bus_ticket_locustfile.py](https://github.com/transport-stack/ondc-micro-mobility-buyer/blob/main/ondc_buyer_backend/locustfiles/bus_ticket_locustfile.py)
- **Architecture doc.** The ONDC Seller "consumes from" "PTO inventory + ONDC", while the other modules consume Open Transit Data APIs. — [wiki-transport-stack docs/architecture/overview.md](https://github.com/transport-stack/wiki-transport-stack/blob/main/docs/architecture/overview.md)
- **Wiki bus data model.** It lists only standard GTFS fields (stops: stop_id, stop_name, lat/lon, location_type, parent_station). It does not mention `stop_code`, `fare_stage` or any ticketing stop code. — [docs/models/bus.md](https://github.com/transport-stack/wiki-transport-stack/blob/main/docs/models/bus.md)
- **Chartr's GTFS product page.**
  - Its GTFS editor is "used by DIMTS and DTC to manage Delhi's bus network".
  - In its Route Editor users can "set fare stages and distances on routes".
  - A Stop Merger flags stops within 70 m.
  - The Delhi map shows 6,800+ stops.
  - "No GTFS, no integration" for ONDC sellers and journey planners.
  - [Chartr GTFS](https://chartr.in/products/gtfs/)

**Public fixtures with Delhi stop names**
- **Seller fixtures from a real pre-prod exchange** (3 Jun 2024; buyer `pre-prod-ondc-buyer-api.chartr.in`, seller `pre-prod-ondc-ticketing-api.delhitransport.in`):
  - The search is `OLD_DELHI_RAILWAY_STATION_T_H_C_SEN_MARG` → `TILAK_BRIDGE` with registration "None".
  - The stored on_search returns 16 items (403UP, 405AUP, 419UP, 425UP, 429UP, 502UP, 0419(NS)UP, 0502(NS)UP, each NAC ₹10 / AC ₹15).
  - Seller ROUTE_IDs include 5159 (403UP) and 5161 (405AUP).
  - Every intermediate stop is listed: Red Fort, Jama Masjid, Darya Ganj, "GOLCHA CINEMA", Delhi Gate, "Express Building-DC2809", "ITO BSZ Marg".
  - [search request](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/search_jsons/request.json); [stored_search_data.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/stored_search_data.json)
- **Second seller fixture.**
  - `ROHINI_SEC_22_TERMINAL` → `AVANTIKA_XING` with GPS "28.718025, 77.0638" and "28.698384, 77.097225".
  - Seller route_ids: 1 = 102STLDOWN, 1329 = 102DOWN (DIMTS), 5464 = EXPRESS-85AUP, 5580 = 247DOWN, 5913 = 0901(NS)DOWN (DTC).
  - [on_search_jsons/request.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/request.json); [on_search_jsons/response.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/response.json); [search_transformer_response.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/search_transformer_response.json)

**Local checks on GTFS v32 and the October 2026 tickets** ([tickets](../../data/raw/ticketing/October-Delhi.csv); [GTFS v32](../../data/raw/gtfs_static/stops.txt))
- **Route IDs.** The seller route_ids are not GTFS v32 route_ids. GTFS v32 has 403UP = 1896, 102DOWN = 5, 102STLDOWN = 8, 247DOWN = 1759 and 0901(NS)DOWN = 1487; its maximum route_id is 4044. GTFS route_id 1329 is D-024DOWN. 405AUP, EXPRESS-85AUP, 0419(NS)UP and 0502(NS)UP are absent from v32.
- **Coordinates.** The seller's 2024 coordinates equal some v32 stops exactly:
  - Avantika Xing (stop_id 155), Rohini Sec 22 Terminal (stop_id 35), and the latitudes of Tilak Bridge (1585), Delhi Gate (336) and Jama Masjid (334).
  - v32 also holds a second "Rohini Sec 22 Terminal" (stop_id 1, coordinates with 14 decimals). It is used by 102DOWN and 0901(NS)DOWN, whereas 102STLDOWN uses stop 35.
  - Other 2024 stops (Old Delhi RS (T) H C Sen Marg, GOLCHA CINEMA, Express Building, Red Fort) have no exact coordinate twin in v32.
- **GTFS stop_code.** v32 `stop_code` is a unique 8-hex string for all 6,862 stops. It is not the md5, sha1, sha256 or crc32 (first or last 8 hex) of name, id, coordinates or their combinations, so it is opaque. No transport-stack code uses it as a ticketing key.
- **Title-casing.** Every ticket start name is unchanged by Python's `str.title()` (100% ticket-weighted in every route group), whereas 22% of GTFS v32 stop names contain an all-caps token (e.g. "ISBT", "GOLCHA CINEMA").
  - Start and end names show Python-specific artefacts: "St. Stephen'S Hospital", "Lodhi Colony 18Block", "Rohini Sec-15E".
  - There are 0 cases of a lowercase letter after a digit or an apostrophe among 7,552 distinct names.
  - So a Python-style `.title()` was applied somewhere after mid-2024: the 2024 seller output still had "GOLCHA CINEMA".
- **How ticket start names relate to GTFS names on the same route, by `fare_stage` flag** (ticket-weighted start names; routes found in GTFS):

  | Route group | Tickets | Equal to a GTFS name on the route | Equal after GTFS `.title()` | Same slug key on route | Same slug anywhere in GTFS |
  |---|---|---|---|---|---|
  | Flagged (`fare_stage`=1 present) | 1,044,144 | 66.0% | +20.6% (86.6% total) | 90.8% | 93.7% |
  | Unflagged | 1,470,533 | 36.8% | +7.6% (44.4% total) | 45.9% | 59.3% |

- **Unflagged DTC routes keep 2024-style seller names.** On 403UP, 419UP, 502UP, 425UP and 429UP the GTFS v32 pattern reads "ITO BSZ Marg (Ram Charan Aggarwal Chowk)", "Express Building" and "ISBT Kashmere Gate Terminal". The tickets read:
  - "Ito Bsz Marg" (3,036 mentions, mainly 502UP, 405UP and 419UP) and "Golcha Cinema" (3,174), which are the title-cased 2024 seller names;
  - abbreviations typical of DTC fare-stage lists: "S.J. Hospital", "Tb Hospital", "Iit Gate", "Mmtc", "Pts", "Ina Cly", "Kashmere Gate City (T)", "K.Gate Isbt", "Jd Blk Pitam Pura", "Y-Blk. Mangol Puri".
  - Some 2024 names no longer occur at all: "Old Delhi Railway Station (T) H C Sen Marg" and "Express Building-DC2809" have 0 mentions.
- **Coordinate precision does not separate the two groups.** Stops with ≤6-decimal coordinates make up 53.5% of stop_times rows on unflagged routes and 51.7% on flagged routes, so this is not a simple two-source merge by coordinate format.
- **Name length.** The longest ticket name has 77 characters, within the seller's `CharField(80)`; two GTFS v32 names exceed 80 characters.
- **Feed date.** The v32 zip entries are dated 7 Oct 2026 (feed_version v32, feed_start_date 2025-01-01).

### Inferences
- **The seller master came from an older GTFS lineage.** It was built offline from an earlier state of the same Chartr GTFS/editor lineage: per route, the stop list of one trip, keeping `stop_name` and lat/lon, re-keyed by `code = SLUG(name)` and `sequence_in_route`. The fares were laid over it as a stop×stop matrix. It is not regenerated automatically from each published GTFS version. This rests on the shared `[stop_id, name, lat, lon]` layout, the exact coordinate twins, and the `tkt_code` field.
- **Why names differ on unflagged routes (the most consistent story):**
  - The `fare_stage` flags mark routes whose stops and fare stages were curated in Chartr's Route Editor. Those routes kept GTFS names aligned with the seller master, which needs fare stages to build fares.
  - On routes without flags, GTFS v32 stops were renamed, merged or re-digitised after the seller master snapshot. The seller master kept older, ETM-style names, or the route was rebuilt from DTC's own route/stage list.
  - The coexistence of duplicate terminal stops in v32 (stop 1 vs stop 35) fits re-digitisation.
  - This is an inference. No commit or document states it.
- **Requesting the stop codes alone would help little.** The `start_stop_code`/`end_stop_code` in the Ticket table are most likely slugs of the same names, so they collapse spelling and spacing variants (e.g. "Badarpur Border(T)" / "Badarpur Border (T)" → `BADARPUR_BORDER_T`) but cannot separate same-named stops. Their value is small unless the seller's route + `sequence_in_route` + lat/lon come with them.
- **Ordering.** Because the seller only finds pairs with start_sequence < end_sequence, every ticket's (start, end) is ordered along the seller's route sequence. This supports the "start before end" constraint used in the earlier matching note.

### Gaps
- The October 2026 contents of `stops_new`, `routes_new` and `stops_pair_new`, and when they were last rebuilt, are not public.
- Whether title-casing happens in the seller master or in the hackathon export is undetermined.
- Why only 1,214 of 2,574 routes have `fare_stage` flags is undocumented. The "curated in Route Editor" explanation is inferred.
- The code of `fetch_fare` (the endpoint the journey planner calls) is not in the public repo.

## 3. Buyer apps for Delhi buses (One Delhi, Chartr, Chalo, WhatsApp, and any of Paytm, PhonePe, Rapido, Namma Yatri, Google Wallet): do they show all stops or only fare stages? Is their stop list from OTD GTFS or the seller catalog? Do they publish open data or unauthenticated endpoints?

### Takeaway
Every app selling DTC or cluster tickets through ONDC receives its stop list from the seller's ONDC catalog: Search 1 returns all stops of every route from `stops_new`, and Search 2 returns a stop pair with all intermediate stops. The catalog and the October tickets show that riders can pick any stop, not only fare stages. I found no documentation of any app building its stop list from OTD GTFS.
- **Apps confirmed for DTC buses:** One Delhi, Chartr, Tummoc, WhatsApp and Chalo.
- **Not confirmed:** Paytm, PhonePe, Rapido, Namma Yatri and Google sell Delhi Metro tickets on ONDC; I found no evidence that they sell DTC buses.
- **Public stop lists:** No app publishes open stop data. The catalog reaches only ONDC-registered buyer apps through signed callbacks to their `bap_uri`.

### Cited Findings
- **The catalog is pushed, not exposed.** The seller posts the full route/stop catalog to the requesting buyer's `bap_uri + /on_search` (asynchronous callback), paged by agency. — [ondc_all_route_search_.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/ondc_all_route_search_.py)
- **Request signing.** The seller code includes Beckn signature creation and verification (`verify_authorisation_header`) with registry lookup. — [main/utils/cryptic_utils.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/utils/cryptic_utils.py)
- **A buyer stores the catalog privately.** Chartr's buyer backend has a handler that stores a received route/stop catalog as `routes_and_stops.json`/zip on its own server. — [on_search_route_stops.py](https://github.com/transport-stack/ondc-micro-mobility-buyer/blob/main/ondc_buyer_backend/views/on_search_route_stops.py)
- **All intermediate stops in a real exchange.** The 2024 Chartr pre-prod exchange lists every intermediate stop between the chosen pair, including non-terminal stops such as Red Fort, Jama Masjid and Darya Ganj. — [stored_search_data.json](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tests/jsons/on_search_jsons/stored_search_data.json)
- **Local check (earlier note): ticket names use the full stop list.** On flagged routes, ticket start names are 43.0% fare-stage stops and 47.7% other stops on the route. — [transit_stop_matching.md](../停留所名の照合と通過検出/transit_stop_matching.md)
- **Apps for DTC.**
  - The wiki names four buyer apps (OneDelhi, Chartr, Tummoc, WhatsApp). — [wiki docs/delhi-transport-stack.md](https://github.com/transport-stack/wiki-transport-stack/blob/main/docs/delhi-transport-stack.md)
  - ONDC's 2 Jun 2026 statement gives one combined list for DTC, CRUT, BEST and Katch Mobility: Chartr, One Delhi, Katchapp, WhatsApp, Tummoc, Chalo, with 300,000+ metro and bus tickets a day. — [Angel One, 2 Jun 2026](https://oga-prod.angelone.in/news/economy/ondc-crosses-450-million-transactions-books-over-300-000-metro-and-bus-tickets-daily)
  - Chalo was launched for DTC on ONDC on 23 Sep 2025. — [The Week/PTI](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **One Delhi flow [older, 2020–21 trial].**
  - "By Destination": choose route, source stop and destination stop, then scan the bus QR.
  - "By Fare": scan the QR and choose a fare without picking stops.
  - [Okhla Times (search snippet only)](https://theokhlatimes.com/?p=905); [Curly Tales](https://curlytales.com/delhi-book-bus-tickets-via-one-delhi-application-heres-how)
- **WhatsApp (DTC).** After "Book Ticket", the rider picks the destination stop in a WhatsApp webview built by PeLocal, then pays by UPI inside WhatsApp. The vendor's case study reports 14 lakh+ tickets. It does not say where the stop list comes from or whether a source stop is chosen. — [AiSensy case study](https://aisensy.com/case-studies/delhi-transport-corporation)
- **Chartr.** Its bus flow is: pick the route, enter start and end stops, choose AC or non-AC. — [Chartr app](https://chartr.in/products/chartr-app/) (as cited in the sibling note)
- **Chalo.** I found no source describing Chalo's Delhi stop-selection screens.
- **Other ONDC apps.** Rapido and Uber are documented on ONDC for Delhi Metro only. — [Inc42, Rapido](https://inc42.com/buzz/rapido-rolls-out-service-to-allow-users-to-book-delhi-metro-tickets/); [Inc42, Uber](https://inc42.com/buzz/uber-users-can-now-buy-delhi-metro-qr-tickets-within-the-app/)
- **Ticketing data is not on the platform.** The Transport Stack newsletter (Issue 1, Jul 2026) lists "ticketing & ridership" as coming soon and says Delhi's ticketing data "sits in a disguised internal system" pending transport-department approval. — [newsletter/1](https://github.com/transport-stack/transport-stack.github.io/blob/main/newsletter/1/index.html)
- **The only seller fare endpoint seen in code** is `pre-prod-ondc-ticketing-api-delhi.transportstack.in/fetch_fare`, referenced by the journey planner. Its implementation is not public, and I did not call it. — [journey-planner modules/bus_fare.py](https://github.com/transport-stack/journey-planner/blob/main/modules/bus_fare.py)

### Inferences
- **The seller name is the label riders see.** Names are fixed by the seller, so a ticket's start and end names are the seller's labels in whatever app was used. The buyer app id (`subscriber_id`) does not change the name text.
- **Riders choose freely among all stops.** They are not constrained to fare stages, but the fare is computed per stop pair from `stops_pair_new`. The "fare-stage only" assumption does not hold for app tickets.
- **No unauthenticated catalog.** Without ONDC registration, which this team must not do, the only routes to the catalog are the organisers, a buyer app operator, or Chartr.

### Gaps
- No current (2025–26) screenshots or help pages for the One Delhi, Chalo or Tummoc stop pickers were found. Whether any app hides stops, groups them, or auto-selects the start stop from the scanned bus QR is unknown.
- Whether the WhatsApp webview (PeLocal) uses the ONDC catalog or its own list is undocumented.

## 4. Delhi OTD GTFS (otd.delhi.gov.in) vs Transport Stack GTFS (delhi.transportstack.in): stop naming, `stop_code`, `fare_stage`, update frequency or changelog; DTC and DIMTS ETM "stage master" lists

### Takeaway
They are different feeds.
- **OTD:** the IIIT-Delhi/DIMTS portal from 2018. Its static page shows 3,464 stops, 543 routes and 16,562 trips, last updated 20 Jun 2024. It documents only the six core GTFS files and none of `stop_code` or `fare_stage`.
- **Transport Stack GTFS v32:** packaged 7 Oct 2026, with 6,862 stops (8-hex `stop_code` on all), 2,574 routes, 80,357 trips, and `fare_stage` on 1,214 routes.
- **Changelogs:** Neither feed publishes one. Transport Stack keeps a historic GTFS index internally.
- **ETM stage masters:** No consolidated DTC or DIMTS ETM stage master is public; only per-route DTC fare-stage circulars exist.

### Cited Findings
- **OTD static page.**
  - Stops 3,464; Routes 543; Stop Times 378,324; Trips 16,562; all "last updated" 20 Jun 2024.
  - Downloads need a usage form (commercial or non-commercial, purpose).
  - The only explicit file link is `agency.txt` on `traffickarma.iiitd.edu.in`.
  - [OTD static data](https://otd.delhi.gov.in/data/static)
- **OTD documentation.**
  - It lists agency, calendar, stops, routes, trips and stop_times with a link to the GTFS reference.
  - It documents no fields (no `stop_code`, `fare_stage`, `stop_dist` or fare files), no versioning and no update frequency.
  - It warns stop_times times are "a rough estimate generated by assuming a constant speed of travel".
  - [OTD documentation](https://otd.delhi.gov.in/documentation)
- **OTD history.** OTD launched in November 2018, built by IIIT-Delhi with DIMTS. The same article reports routes changing without the static data being updated, and that the Transport Stack integrates "close to 5,000 bus stands and nearly 2,000 bus routes". — [Swarajya, 10 Mar 2026](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus)
- **Transport Stack GTFS: team records** (portal and downloads, 13–15 Nov 2026):
  - The portal shows "last updated 2026-06-23".
  - An earlier download ("v1") had 6,812 stops, 2,554 routes and 65,322 trips.
  - The hackathon brief quotes ~10,500 stops, ~2,400 routes and ~89,000 trips, which matches neither.
  - [docs/data.md](../../docs/data.md); [docs/context.md](../../docs/context.md)
- **Local check: v32 contents.**
  - `feed_info` v32 for both DTC and DIMTS; zip entries dated 7 Oct 2026.
  - `stops.txt` columns are `stop_id, stop_code, stop_name, stop_lat, stop_lon`.
  - `stop_times.txt` has `fare_stage` (0/1) and an empty `stop_dist`.
  - The 6,862 stops have 3,813 coordinates with ≤6 decimals and 3,049 with more; stop_ids go up to 8,595,906.
  - [Local check](../../data/raw/gtfs_static/feed_info.txt)
- **Chartr's editor.** It sets fare stages and distances per route, and the Delhi map shows 6,800+ stops. This matches v32's count, so v32 is very likely an export of Chartr's editor. — [Chartr GTFS](https://chartr.in/products/gtfs/)
- **Historic GTFS versions exist internally.** The TransOps dashboard API exposes Elasticsearch indices named `es-delhi-gtfs-static-v01` and `es-delhi-gtfs-static-historic-v01`. — [dashboard-api elasticsearch proxy](https://github.com/transport-stack/dashboard-api/blob/main/api/v2/views/elasticsearc_proxy_api.py)
- **DTC fare stages are published route by route as circulars.**
  - The archive lists items such as "Revised fare Stages of Route No.490", mostly from 2012–2015 in the indexed pages.
  - The 740C circular (13 Jun 2026) lists every stop with "Fare Stage" numbers and asks IT to update "the online ticketing app and website".
  - [DTC circulars archive (snippet)](https://dtc.delhi.gov.in/dtc-circulars/archive?page=9); [740C circular](https://dtc.delhi.gov.in/sites/default/files/DTC/important-news/circular_for_route_no_740c.pdf) (read in the sibling note)
- **DTC's AFCS (Sep 2025).** DTC rolled out a Canara Bank automated fare collection system: 3,000 conductor machines. The report does not mention a public stage master. — [The Week/PTI, 23 Sep 2025](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **ETM records were advertised.** The hackathon was announced with "live bus GPS, e-ticketing, ETM and metro AFC records", and the team's Problem 2 brief lists "4–5 weeks of e-ticketing and ETM records". — [newsletter/2](https://github.com/transport-stack/transport-stack.github.io/blob/main/newsletter/2/index.html); [docs/context.md](../../docs/context.md)

### Inferences
- **Use OTD only as historical evidence.** OTD's 2024 static feed is about a fifth of v32's routes. It is likely an older or partial lineage, probably cluster-oriented given DIMTS's role, though not verified. It could serve only as evidence of older names, and it cannot be fetched without filling a usage form.
- **No public stop-level key across versions.** Neither feed documents `stop_code` semantics. v32's hex codes are opaque. The ETA calculator stored stop_code as Integer in 2024, which weakly suggests the code format changed between versions. So `stop_code` should not be assumed stable across versions without the organisers confirming it.
- **ETM data is the main source for unflagged routes.** ETM stage masters, which DTC IT maintains and which circulars ask IT to update, are the natural reference for the abbreviated names seen on unflagged routes. They are only obtainable from DTC, DIMTS or the organisers.

### Gaps
- I could not download the OTD feed (form required), so whether it has `stop_code` or `fare_stage`, and how its names compare with v32 and the tickets, is untested.
- No changelog or release notes exist for Transport Stack GTFS v1 → v32.
- No public DTC or DIMTS ETM stage master was found, nor any document from the Canara Bank AFCS route configuration.

## 5. What exactly should the team ask the organisers for, named in their own system terms? And what can it rebuild itself?

### Takeaway
Priority 1 is a dated snapshot of the ONDC seller's stop master from `transit_db`, which alone would turn most of the remaining name matching into a key join through route, sequence and coordinates:
- `stops_new (route_id, name, code, latitude, longitude, sequence_in_route)`;
- `routes_new (route_id, name, agency, is_ac/is_active)`;
- `stops_pair_new (route_id, name, agency, is_ac, start_stop_code, end_stop_code, start_stop_name, end_stop_name, start_sequence, end_sequence, fare_details)`.

An alternative is the ONDC Search-1 catalog dump (`routes_and_stops.json`) as received by a buyer app.

Priority 2 is the GTFS↔ticket crosswalk the journey planner uses (`tkt_code` per GTFS stop).

Priority 3 adds the `main_ticket` columns left out of the CSV, and the DTC/DIMTS ETM stage masters.

The team can rebuild these itself, with no request:
- the seller's slug key: 90.8% / 45.9% on-route agreement for flagged / unflagged routes;
- title-case normalisation;
- route ordering constraints;
- fare-based placement.

### Cited Findings
- **Names of the seller's tables and columns:**
  - `stops_pair_new`: start_stop_code, end_stop_code, route_id, is_ac, fare_details {bf, tl}, name, agency, start/end_stop_name, start/end_sequence.
  - `stops_new` (with `routes_new`): name, code, route_id, latitude, longitude, sequence_in_route; route `name` and `agency`.
  - Legacy: `routes.fare_matrix`, `routes.stop_details`, `stops.sequence_in_route`, and `all_routes` in the `chartr` DB.
  - [modules/fare_setup/main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/main.py); [ondc_all_route_search_.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/tasks/ondc_all_route_search_.py); [modules/fare_setup/_main.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/modules/fare_setup/_main.py); [main/models/routes.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/routes.py)
- **Ticket table columns absent from the CSV:** `start_stop_code`, `end_stop_code`, `agency` (→ table `agency`), `subscriber_id`, `fare` (→ `FareBreakup`: basic, toll, discount, coupon_discount, amount), `valid_till`, `ticket_status`, `pnr`/`transit_pnr`, `updated_at`. — [main/models/tickets.py](https://github.com/transport-stack/ondc-buses-seller/blob/main/main/models/tickets.py)
- **The journey planner's ticket code** comes from a `tkt_code` column in its bus `stops.txt` (`data/GTFS/bus/stops.txt`), which is sent to the seller's `fetch_fare`. — [journey-planner models/models.py](https://github.com/transport-stack/journey-planner/blob/main/models/models.py); [modules/bus_fare.py](https://github.com/transport-stack/journey-planner/blob/main/modules/bus_fare.py)
- **Historic GTFS index:** `es-delhi-gtfs-static-historic-v01`. — [dashboard-api](https://github.com/transport-stack/dashboard-api/blob/main/api/v2/views/elasticsearc_proxy_api.py)
- **Contact.** The data README names the source as "Transport Stack / IIIT Delhi" with contact csm@iiitd.ac.in. — [data/raw/ticketing/README.md](../../data/raw/ticketing/README.md)
- **Local check: the slug key.** Ticket start names agree with a GTFS v32 stop name on the same route under the seller's slug rule for 90.8% (flagged) and 45.9% (unflagged) of tickets. Plain equality gives 66.0% and 36.8%; equality after `.title()` gives 86.6% and 44.4%. — [Local check](../../data/raw/ticketing/October-Delhi.csv)

### Inferences

#### Request list (in priority order; ask for the October 2026 state, or every version valid during 1–31 Oct 2026 with validity dates)
1. **Seller stop master** from the ONDC bus seller's `transit_db`, as CSV:
   - `routes_new`: all columns; at least `route_id, name, agency, is_ac, is_active`.
   - `stops_new`: `route_id, name, code, latitude, longitude, sequence_in_route`.
   - `stops_pair_new`: `route_id, name, agency, is_ac, start_stop_code, end_stop_code, start_stop_name, end_stop_name, start_sequence, end_sequence, fare_details`.
   - Also ask when these tables were last rebuilt, and from which GTFS `feed_version` or editor export.
   - **Fallback:** one complete Search-1 `on_search` catalog (all pages: `ROUTE` fulfillments plus the `STOPS` fulfillment) as received by One Delhi or Chartr's buyer, i.e. their `routes_and_stops.json`.
   - **What it gives:** a route + sequence + lat/lon for every ticket name; most of the 31% of unflagged-route tickets the team cannot match would resolve by a join.
2. **GTFS ↔ ticketing crosswalk:**
   - the bus `stops.txt` used by the Transport Stack journey planner, including its `tkt_code` column (and `mapped_stops.pkl` if relevant);
   - or any table `gtfs stop_id → seller stop code (+ seller route_id ↔ GTFS route_id)`.
   - Also ask whether v32 `stop_code` (8-hex) is stable across GTFS versions and whether the seller uses it anywhere.
3. **Missing Ticket columns** for the same rows as the CSV (with a row id): `start_stop_code`, `end_stop_code`, `agency_id`, `subscriber_id`, `fare_id` → `FareBreakup(basic, toll, discount, coupon_discount, amount)`, `valid_till`, `ticket_status`, `updated_at`.
   - The codes alone mostly duplicate the names (slugs); they matter mainly together with item 1.
   - `agency` separates DTC from DIMTS; `basic`/`discount` make fare-based placement exact.
4. **ETM data promised in the Problem 2 brief:**
   - DTC/DIMTS ETM (Canara Bank AFCS since Sep 2025) route master and stage master: route, direction, stage number, stage name, stops in stage, and fare table.
   - ETM ticket records with `from_stage` and `to_stage`.
5. **GTFS lineage:**
   - the GTFS version that the seller master was built from, or the version closest to it (from `es-delhi-gtfs-static-historic-v01`);
   - the reason only 1,214 routes carry `fare_stage` flags, i.e. which routes were curated in the Route Editor;
   - whether stop names are title-cased in the seller DB or only in the hackathon export.

#### What the team can rebuild without any request
- **The seller key.** Apply `SLUG(name) = upper(re.sub(r'\W+', '_', name.strip(punctuation)))` to both ticket names and GTFS names, and match on (route, slug). This is the seller's own code convention, and it already gives 90.8% / 45.9% on-route agreement for flagged / unflagged routes. Normalise `.title()` before any fuzzy step.
- **Stop order.** The seller only sells start_sequence < end_sequence, so every ticket is a "start before end" constraint on the seller's hidden sequence. Learn each route's ticket-name order from millions of pairs, as in the earlier note's step 3.
- **Fare placement.** Per-rider fare ÷ 0.9 gives the slab. Use it to place names along the route (fare-band trilateration). The seller's `fare_details` comes from a stop×stop table, which is consistent with this.
- **2024 anchors.** The public seller fixtures, and Chartr buyer `routes.json` (50 route terminals), provide a few verified older names and codes for 403UP, 405AUP, 419UP, 425UP, 429UP, 502UP, 102DOWN, 247DOWN and others. Use them only as spot checks.
- **Circular annexes.** Where a DTC circular exists (e.g. 740C), its English annex supplies spelling variants and stage membership.

### Gaps
- Whether the organisers can release `transit_db` tables or the buyer-side catalog (data ownership: GNCTD Transport Department; operator: Chartr) is unknown.
- If the seller master was rebuilt during October 2026, a single snapshot will not match early-month tickets. The request therefore asks for versions with validity dates.
