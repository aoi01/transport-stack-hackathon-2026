# How Delhi bus riders buy QR/mobile tickets in practice: Hindi and Indian user-generated sources (as of 16 Nov 2026)

Scope and conventions:
- Covers Delhi DTC and cluster buses only. Each source is tagged with its language in [brackets]. Items dated before 2024 are marked [older].
- "(snippet only)" means the page could not be opened (403, 404 or bot check), so the finding comes from the search-engine snippet. Treat these as weaker.
- Copyright limits: user and press wording is **paraphrased in English**, not quoted, except for one short quote. Follow the links for the original wording.
- The research tools could not reach these sources: Reddit (domain blocked), X/Twitter, Quora (no indexed hits), Google Play review text (the page renders without reviews), Navbharat Times, Dainik Jagran, Live Hindustan, Dainik Bhaskar, ABP, NDTV India and TV9. The Hindi press coverage therefore comes mostly from Amar Ujala, Aaj Tak, Zee News Hindi, NewsOnAir Hindi and CMV360 Hindi.
- Dataset facts (given by the coordinator, not re-derived here): the file holds 2.56M ONDC e-tickets for October 2026. 48.5% have no vehicle number. The blank share is 30–70% on almost every route and similar for AC and non-AC buses and across fares. Where a vehicle number exists, the median purchase time is 0.8 minutes after the bus passed the boarding stop.

## 1. Hindi tutorials and articles: how do they explain buying a DTC/cluster bus ticket? Do they show a QR sticker inside the bus, or manual route/stop selection?

### Takeaway
Since the 2020 trials, explainers have described two parallel entry paths:
- **Bus-identifying:** scan a QR code physically inside the bus, or type the bus number.
- **Manual:** pick the route, the boarding stop and the destination stop by hand.

The channels added in 2024–2025 (the WhatsApp chatbot, and the Chalo app on ONDC) appear in Hindi media only as route/stop selection, with no bus step. The fleet-wide "Universal QR" sticker of September 2025 is described separately, as something you scan inside the bus with any UPI app.

### Cited Findings
- **[Hindi] Amar Ujala, 15 Sep 2020 [older].** Describes the first QR-ticket trial: route 534 (Anand Vihar–Mehrauli), 29 buses.
  - Passengers download the app, enter their destination and scan a QR code to pay, without going to the conductor or using cash.
  - First-day uptake was low. The conductor said only two or three women booked (paraphrased). Passengers were unsure of the process.
  - Manual tickets were expected to continue for some months.
  - [Amar Ujala](https://www.amarujala.com/delhi-ncr/qr-code-ticket-trial-started-in-dtc-buses)
- **[English, local news] The Okhla Times, 5 Aug 2020 [older].** The Chartr trial instructions gave two paths:
  - "By Fare": scan the bus QR, choose Buy New Ticket, then pay.
  - "By Destination": choose the route, source stop and destination stop, tap Buy, then scan the bus QR and pay.
  - In this original design both paths ended with a bus-QR scan.
  - IIIT-Delhi trained conductors online to help riders.
  - [The Okhla Times](https://theokhlatimes.com/e-ticketing-dtc-buses/)
- **[English] Curly Tales, 19 Jul 2021 [older].** One Delhi was described as: scan the QR code inside the bus, then choose either a fare or source/destination stops, with a 10% app discount. The example was framed around pink tickets and passes. [Curly Tales](https://curlytales.com/delhi-book-bus-tickets-via-one-delhi-application-heres-how)
- **[Hindi] Amar Ujala, 11 Apr 2024: step-by-step WhatsApp booking.**
  - Steps: send "Hi" to 8744073223, or scan a QR code to start the chat → choose language → pick Book Ticket → choose Source and Destination → choose the bus route → choose AC or non-AC → enter the number of tickets → pay by UPI or card → scroll up and tap Download Ticket.
  - The ticket is valid only until the time printed on it.
  - **No step asks for the bus number.** The article does not say where the start-chat QR is displayed.
  - [Amar Ujala](https://www.amarujala.com/automobiles/dtc-bus-ticket-booking-by-whatsapp-know-step-by-step-process-2024-04-11)
- **[English] Business Today, 11 Apr 2024.** WhatsApp sells up to six tickets per UPI transaction. A "quick purchase" option lets frequent riders skip choosing start and end points. The bus number is not mentioned. [Business Today](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11)
- **[Hindi] Amar Ujala, 24 Sep 2025: the Automated Fare Collection System (AFCS) launch.**
  - Conductors get new POS/ETM machines that accept cash, UPI, debit/credit cards and a Universal QR. Canara Bank is providing 3,000 machines free.
  - QR stickers have been put up across the whole DTC fleet.
  - The article lists three ways to buy:
    1. **Chalo app:** pick the route and destination, pay, and get the ticket on your phone, with 10% off.
    2. **Universal QR:** scan the QR inside the bus and pay with any UPI app; the digital ticket is issued immediately.
    3. **Conductor's machine:** get a printed ticket, paying by cash, card or UPI.
  - The article does not say whether the bus number is captured.
  - [Amar Ujala](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
- **[English, PTI] The Week, 23 Sep 2025.**
  - The Chalo app was launched on the ONDC platform, with a 10% discount to encourage adoption.
  - Quote: "Stickers with Universal QR codes have already been deployed across the fleet".
  - [The Week / PTI](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **[English, vendor blog] Tummoc, 10 Jun 2024.**
  - You buy the DTC ticket in the app. **Once inside the bus**, you open Bookings and tap Validate Ticket.
  - You scan the Tummoc QR if one is posted in the bus; otherwise you type the bus number.
  - The ticket then stays active for 30 minutes.
  - [Tummoc blog](https://blog.tummoc.com/?p=2344)
- **[English, App Store] Chartr 2.0**, a new app first listed in Aug 2025.
  - The store text gives the bus flow as: scan the QR, enter the destination, pay, get the ticket.
  - A 9 Dec 2025 review complains that the bus-route selection screen closes before a route can be picked. This shows a manual route picker also exists.
  - [App Store: Chartr 2.0](https://apps.apple.com/in/app/chartr-2-0/id6747386059)
- **[English, App Store] One Delhi review, 25 Jul 2024.** On iOS, after the user typed the bus number, the app could not find the current route, and payment then failed (paraphrased). This shows One Delhi has a bus-number entry step. [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)
- **[Hindi/Hinglish YouTube, titles only].** Descriptions and transcripts could not be retrieved.
  - "Dtc bus eticket & dtc bus pass buy online one delhi & chartr app | Chartr app new update Around me" ([YouTube](https://www.youtube.com/watch?v=ZOD9HpqtFUI))
  - "DTC Bus ticket Whatsapp Se Kaise Book Karen" ([YouTube](https://www.youtube.com/watch?v=zBqOgk0kWL0))
  - A Zee News Hindi live report on the 2020 e-ticketing trial [older] ([YouTube](https://www.youtube.com/watch?v=eYqcLjEpSsA))
  - Tummoc's "Introducing Pre-Booking of DTC Bus Tickets" ([YouTube](https://www.youtube.com/watch?v=EYGZZyrXF_U))

### Inferences
- Bus-identifying inputs (QR scan, typed bus number) and route/stop inputs have co-existed since 2020. Which one fills a vehicle field depends on each app's flow.
- The 2024–2025 mass channels (WhatsApp, Chalo on ONDC) are presented in Hindi media as route/stop-only. That fits the hypothesis that manually selected tickets carry no vehicle number.
- WhatsApp makes the rider pick AC or non-AC, so the fare can be set without knowing the bus. This fits the dataset finding that the blank-vehicle share and fares are similar for AC and non-AC.
- Counterpoint: in the 2020 Chartr design, even the route/stop path ended with a bus-QR scan. "Manual selection" does not automatically mean "no bus"; it depends on the app version.

### Gaps
- I found no screen-by-screen 2025–2026 Hindi tutorial of the current One Delhi bus flow; the major Hindi portals above were blocked for the tools.
- It is undocumented whether the QR that starts the WhatsApp chat is a bus-specific sticker that could pass a bus ID.
- It is unclear whether Chalo's ONDC flow offers a bus-QR or bus-number option at all.

## 2. Is a QR code (with the bus number) pasted inside every bus? Reports of missing, torn or non-working stickers?

### Takeaway
Official and press accounts say every bus carries QR stickers: on the back of every seat in 2021, and a fleet-wide Universal QR from September 2025. I found no rider report of missing or torn stickers. There are, however, reports that some buses cannot be found in the apps (missing e-bus registrations, failed bus-number lookups). Several different QR systems (Chartr/One Delhi, Tummoc, Universal QR) may sit in the same bus.

### Cited Findings
- **[English] Hindustan Times, 25 Feb 2021 [older] (snippet only; page returned 403).** Contactless Chartr ticketing was extended to all DTC buses, with QR stickers on the back of each seat. Most passengers still paid cash for paper tickets. [HT via PressReader](https://www.pressreader.com/india/hindustan-times-st-noida/20210225/281809991618212)
- **[English] Zee Business, 2020 trial [older] (snippet only).** The QR was placed near the conductor's seat. [Zee Business](https://www.zeebiz.com/india/news-delhi-contactless-ticketing-system-this-app-allows-you-to-book-ticket-on-dtc-buses-through-qr-code-150905)
- **[English/Hindi] PTI and Amar Ujala, 23–24 Sep 2025.** Both report Universal QR stickers deployed across the whole DTC fleet (see section 1). [The Week / PTI](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html); [Amar Ujala](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
- **[English, vendor] Tummoc, Jun 2024.** The instructions assume a Tummoc QR may be absent: scan it if posted, otherwise type the bus number. [Tummoc blog](https://blog.tummoc.com/?p=2344)
- **[English, ground report] Swarajya, 10 Mar 2026.**
  - One Delhi tracks more than 7,300 DTC and cluster buses.
  - Users complain that some e-buses' registration numbers were never added to the app, and those complaints stayed open for months.
  - Bus GPS units also go offline.
  - [Swarajya](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus)
- **[English, App Store] One Delhi reviews.** 5 Jan 2025: the app shows zero buses on the route. 25 Jul 2024: the bus number did not return the route. [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)

### Inferences
- If the fleet-wide sticker claim holds, missing stickers cannot explain a 30–70% blank share on almost every route.
- Missing e-bus registrations would mainly affect e-buses, which are AC. Yet the dataset shows similar blank shares for AC and non-AC, so this is not the main driver either.
- That leaves the rider's choice of channel or flow as the more likely explanation.
- The September 2025 Universal QR is a UPI payment QR. It is unknown whether a payment through it becomes an ONDC ticket, or carries a vehicle number.

### Gaps
- No Reddit, X or Google Play text about torn, missing or non-working stickers could be accessed.
- No source says whether the One Delhi/ONDC QR encodes the vehicle or only the route or depot.

## 3. Can riders buy while waiting at the stop? Do conductors accept such tickets? How are tickets checked?

### Takeaway
The route/stop channels (WhatsApp, Chalo, Tummoc pre-booking) let riders buy before the bus arrives. Bus-QR flows require being in the bus. In practice the ticket is checked by showing the phone screen, according to the sources. There are recurring disputes and ₹200 fines when the app fails, and vendors claim conductors scan the QR.

### Cited Findings
- **[English, vendor] Tummoc.** A YouTube video is titled "Introducing Pre-Booking of DTC Bus Tickets". The blog says the ticket is bought in advance and activated on board for 30 minutes. [YouTube](https://www.youtube.com/watch?v=EYGZZyrXF_U); [Tummoc blog](https://blog.tummoc.com/?p=2344)
- **[Hindi] Amar Ujala, Apr 2024.** The WhatsApp ticket has no bus step and is valid until the time printed on it, so it can be bought at the stop. [Amar Ujala](https://www.amarujala.com/automobiles/dtc-bus-ticket-booking-by-whatsapp-know-step-by-step-process-2024-04-11)
- **[Hindi] Amar Ujala, Sep 2025.** A Chalo ticket is bought by choosing the route and destination; no bus step is mentioned. [Amar Ujala](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
- **[English, vendor] Chartr product page (snippet only).** Claims the QR ticket is generated instantly and that conductors scan it to verify. [Chartr](https://chartr.in/products/chartr-app/)
- **[English] 91mobiles WhatsApp guide (snippet only; 403).** Advises showing the QR ticket to the conductor or checker if asked. [91mobiles](https://www.91mobiles.com/hub/how-to-book-dtc-bus-tickets-through-whatsapp/amp/)
- **[English] Older Chartr rules [older] (snippet only, 2021 trial reports).**
  - The ticket becomes invalid once the rider reaches the destination entered.
  - At most three tickets per journey.
  - A pink ticket is suggested automatically based on gender.
  - [Zee Business](https://www.zeebiz.com/india/news-delhi-contactless-ticketing-system-this-app-allows-you-to-book-ticket-on-dtc-buses-through-qr-code-150905)
- **[English] consumercomplaints.in posts (snippet only; pages returned 403; one-sided and unverified).**
  - A rider with a Chartr ticket was fined ₹200 by a DTC ticket checker who allegedly took the phone. [Complaint 1](https://www.consumercomplaints.in/delhi-transport-corporation-dtc-ticket-checker-snatched-my-phone-and-forcibly-issued-challan-to-me-c3407907)
  - A One Delhi user hit an "app error" and paid a ₹200 on-the-spot penalty despite showing proof of payment. [Complaint 2](https://www.consumercomplaints.in/delhi-transport-corporation-dtc-subject-request-for-refund-of-200-penalty-due-to-app-error-on-one-delhi-app-c3535068)
- **[English, App Store] One Delhi review, 7 May 2023 [older].** The conductor had no change and told the rider to install One Delhi. The ticket came out "invalid" after the money was deducted. The conductor would not accept it, and the bus nearly left the rider behind (paraphrased). [App Store GB](https://apps.apple.com/gb/app/one-delhi/id1641749010)
- **[English, App Store] One Delhi review, "3 Jan" (year not shown, likely 2026).** Money was deducted but no ticket was booked. There was no refund after 10 days, and the conductor did not help. [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)
- **[English, App Store] One Delhi review, 17 May 2023 [older, positive].** The app is handy when you carry no cash, and it avoids crowding around the conductor's seat. [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)
- **[Hindi] Aaj Tak, 13 Aug 2019 [older] (snippet only).** A Delhi High Court hearing noted that cluster-bus conductors walk through the bus to collect fares, but DTC conductors do not. Out-of-town riders who don't know to approach the conductor end up fined. [Aaj Tak](https://www.aajtak.in/amp/india/delhi/story/cluster-bus-conductors-to-go-to-passengers-to-collect-fare-not-so-in-dtc-delhi-hc-954588-2019-08-13)

### Inferences
- The dataset's median of 0.8 minutes after the bus passes the stop (vehicle-number tickets only) fits "board first, then scan the QR". This matches the QR-in-bus and activate-on-board instructions.
- Blank-vehicle tickets plausibly mix two groups: purchases made at the stop before boarding (WhatsApp, Chalo, route mode) and on-board purchases where the rider simply picked the route.
- The sources suggest checking is visual, so riders have little reason to scan the bus QR when a route/stop path exists.
- Testable in the data: for blank tickets, compare the purchase time with the GPS passage of any bus on that route at the boarding stop. A meaningful share bought before any bus arrives would confirm purchases made at the stop.
- Also compare tickets per transaction for blank and non-blank tickets (WhatsApp allows up to six), and any buyer-app or channel field if the data has one.
- DTC conductors sit at a fixed seat, which pushes riders toward self-service app purchase once on board, to avoid the queue and change problems.

### Gaps
- No 2025–2026 source describes how conductors or checkers actually verify ONDC tickets (scan or glance).
- No source says whether a ticket without a bus number is accepted on any bus of that route, or how long ONDC bus tickets stay valid.
- I found no Hindi rider reports of conductors refusing app tickets or insisting on paper tickets in 2024–2026; the only conductor-refusal stories found are older or about pink tickets.

## 4. Complaints and problems: payment failures, network issues, refusals, fines, fare mismatches, crashes

### Takeaway
Store reviews and complaint sites show these recurring problems:
- money deducted but no ticket, and "invalid" tickets
- buses or routes not found, and failed bus-number lookups
- location and network errors
- ₹200 fines despite payment

The iOS ratings are low. The Android rating is inconsistent between snapshots. I found no specific complaints about fare mismatches.

### Cited Findings
- **[English, App Store] One Delhi (iOS).** Rated 1.7/5 from 225 ratings as of Nov 2026.
  - Reviews: no buses shown (Jan 2025); bus number could not find the route, then payment problems (Jul 2024); paid with no ticket and no refund (3 Jan, likely 2026); invalid ticket plus a hostile conductor (May 2023 [older]).
  - Version notes: bus passes added in Aug 2025; refund and terms pages added in Nov 2025; bug fixes in Jan and Jun 2026.
  - [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)
- **[English, App Store] (snippet only).** Another One Delhi iOS review reports location-not-found and no-network errors when buying a bus ticket. [App Store US](https://apps.apple.com/us/app/id1641749010)
- **[English] One Delhi on Android** ("One Delhi : Travel Simplified", com.delhitransport.onedelhi). AppGoblin shows 3.41★ from about 7K ratings, 3.2M+ installs, last updated 28 Sep 2026. A different snapshot in search results showed 4.64★ from 6.3K ratings. The two conflict; the Play Store page itself did not render reviews. [AppGoblin](https://appgoblin.info/apps/com.delhitransport.onedelhi)
- **[English, App Store] Chartr 2.0.** Rated 2.7/5 from 192 ratings.
  - Reviews: the route picker closes too fast (Dec 2025); the bus booking failed to work and support was unhelpful (Mar, likely 2026); a metro QR failed at the exit gate (Mar, likely 2026).
  - [App Store: Chartr 2.0](https://apps.apple.com/in/app/chartr-2-0/id6747386059)
- **[English, ground report] Swarajya, Mar 2026.**
  - Some e-buses are missing from One Delhi.
  - Stops lack fare information, so riders often don't know the fare before boarding.
  - First-time riders walk to the driver's door to confirm the route.
  - [Swarajya](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus)
- **[English] consumercomplaints.in.** The ₹200 checker fines on Chartr and One Delhi users (see section 3; snippet only, unverified).
- **[Hindi] Zee News Hindi video (date unknown; title only, page 404).** A DTC conductor refused to give women a pink ticket, causing a ruckus. This concerns pink paper tickets, not app tickets. [Zee News Hindi](https://zeenews.india.com/hindi/india/delhi-ncr-haryana/video/delhi-dtc-bus-conductor-refuses-to-give-pink-ticket-to-women-ruckus-created-watch-viral-video/2692716)

### Inferences
- Bus-lookup failures (unregistered e-buses, bus number not found) could push some riders from the bus path to the route path. This is likely a minor contributor given the AC/non-AC parity in the dataset.
- Payment failures with no refund path probably deter repeat use. That may help explain modest ONDC volumes (see section 5).

### Gaps
- Google Play reviews (the largest user base, much of it Hinglish), Reddit r/delhi and r/india, X posts tagging DTC or the transport department, and Quora threads could not be retrieved or were not indexed.
- I found no data on how often each problem occurs.

## 5. Hindi news on the share of digital/QR tickets (2025–2026), UPI payment to conductors, and the Pink Saheli smart card

### Takeaway
- **Digital share:** no 2025–2026 figure for the share of digital or QR tickets on DTC buses was found in Hindi or English news.
- **UPI to conductors:** since September 2025, conductors' new AFCS ETMs (Canara Bank) accept UPI, cards and the Universal QR.
- **Pink Saheli card:** an NCMC card that women tap on the bus ticket machine (ETM). It became mandatory from 1 Aug 2026; paper pink tickets were extended in steps into mid-September 2026. The latest report found counts about 17 lakh cards issued.

### Cited Findings
- **[English] DMRC release via PSU Connect, 6 Jan 2024.** The One Delhi app was then used for DTC bus QR tickets only, averaging about 1.5 lakh ticket sales a day with about 3.0 lakh active users. [PSU Connect](https://psuconnect.in/news/delhi-metro-integrates-its-ticketing-service-with-one-delhi-mobile-app/40694)
- **[English] Hindustan Times, Feb 2021 [older] (snippet only).** Daily bookings through Chartr were about 10,000. [HT via PressReader](https://www.pressreader.com/india/hindustan-times-st-noida/20210225/281809991618212)
- **[English] Urban Acres, 16 Sep 2025.** DTC began a UPI ticket-payment pilot on new e-PoS machines at Tantri Hastnapur, Kalkaji and Rajghat Depot-2, to be expanded fleet-wide. It also says pink tickets are now issued digitally on these machines. [Urban Acres](https://urbanacres.in/?p=76293)
- **[Hindi] Amar Ujala, 24 Sep 2025.**
  - The AFCS replaces manual ticketing. The motive given is fares not being properly deposited.
  - Each ticket's money goes straight to DTC's bank account.
  - Ticket data reaches the server at once, showing passengers and revenue by route.
  - The ETMs accept cash, UPI, card and Universal QR; 3,000 machines come from Canara Bank.
  - [Amar Ujala](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
- **[English] ThePrint (date unknown; snippet only, bot check).** The DTC board approved 5,700 ETMs for digital fare collection. [ThePrint](https://theprint.in/india/delhi-buses-to-see-smart-card-based-ticketing-soon/2620622)
- **[Hindi] CMV360 Hindi, 31 Dec 2025.** The Pink Saheli card will replace paper pink tickets and will be read by conductors' ETMs. A Delhi Aadhaar is required. [CMV360](https://www.cmv360.com/hi/news/delhi-aadhaar-mandatory-for-free-bus-rides-for-women-from-2026-pink-saheli-smart-card-to-replace-pink-tickets)
- **[Hindi] Amar Ujala, 3 Mar 2026 (headline).** About 2,000 Pink Saheli cards were made on the first day at 50 centres. [Amar Ujala](https://www.amarujala.com/delhi-ncr/2000-pink-saheli-smart-cards-were-made-on-the-first-day-at-50-centres-in-the-capital-delhi-ncr-news-c-340-1-del1011-126459-2026-03-03)
- **[Hindi] Aaj Tak, 11 May 2026 (headline).** Free travel on pink paper tickets would end, with only the smart card from July. [Aaj Tak](https://www.aajtak.in/india/delhi/story/delhi-women-free-bus-travel-pink-ticket-to-fully-replace-saheli-smart-card-july-2026-ntc-drmt-dskc-2549142-2026-05-11)
- **[Hindi] Amar Ujala, 20 May 2026.**
  - More than 8 lakh women have the card.
  - It works on NCMC tap-and-go: you tap the card on the ETM in the bus and the trip is recorded, with no paper ticket needed.
  - The process is fully online, and camps are being expanded.
  - [Amar Ujala](https://www.amarujala.com/delhi-ncr/pink-saheli-smart-card-reaches-8-lakh-women-2026-05-20)
  - The Daily Pioneer gives a related figure of 8,40,618 cards by 18 May 2026 (snippet only). [Daily Pioneer](https://www.dailypioneer.com/news/over-8-lakh-women-issued-pink-saheli-smart-cards-for-free-bus-travel-in-delhi-cm-rekha-gupta)
- **[Hindi] Aaj Tak, 27 Jul 2026.**
  - The card becomes mandatory for free DTC rides from 1 Aug 2026.
  - When boarding, the woman taps the card on the ticket machine and gets a free ticket as before.
  - Without a valid card there is no free ride.
  - The orange card for seniors and disabled riders had not yet started.
  - [Aaj Tak](https://www.aajtak.in/india/delhi/story/pink-saheli-smart-card-free-dtc-bus-rides-debit-card-facilities-ntcpsc-dskc-2609912-2026-07-27)
- **[Hindi] NewsOnAir, 16 Aug 2026 (headline/URL).** The pink paper-ticket facility in DTC buses was extended to 31 Aug. [NewsOnAir Hindi](https://newsonair.gov.in/hi/delhi-government-extends-pink-ticket-facility-in-dtc-buses-till-august-31/)
- **[Hindi] NewsOnAir (headline: mandatory deadline extended to 16 Sep).**
  - Conductors keep issuing pink tickets until the 15th of the next month, and 17,04,042 cards have been issued.
  - Officials were told to step up awareness campaigns so that no eligible woman is wrongly refused a free ride.
  - Date conflict: the fetch tool dated this page 31 Jul 2026, but its headline and the 16 Aug item imply late August.
  - [NewsOnAir Hindi](https://newsonair.gov.in/hi/delhi-mandatory-deadline-for-pink-saheli-smart-card-extended-till-september-16/)

### Inferences
- **Women's free rides are outside the dataset.** Pink Saheli trips are recorded as ETM taps in the AFCS, not as ONDC e-tickets. From mid-September 2026, women without the card must pay, which could slightly raise paid (and digital) tickets in October 2026. This is speculative.
- **ONDC volume looks low.** 2.56M tickets in October 2026 is about 83k a day, below One Delhi's roughly 1.5 lakh a day in Jan 2024. Either the hackathon file covers only some digital channels, or digital volume has not grown. The sources cannot settle this.
- **A non-ONDC digital route may divert riders.** Since September 2025, riders can pay the conductor's ETM by UPI or scan the Universal QR with any UPI app. Some digitally inclined riders may now use these instead of ONDC apps; how many is unknown.

### Gaps
- No Hindi or English news item giving a 2025–2026 percentage or count of QR/app tickets on DTC buses was found.
- I found no reports of Pink Saheli tap failures or ETM breakdowns in Delhi.
- It is unconfirmed whether paper pink tickets were fully withdrawn by October 2026.

## 6. Evidence for and against the hypothesis "QR-scan purchases capture the bus; manual route selection does not"

### Takeaway
On balance, the sources support the hypothesis, but only indirectly:
- Every documented flow that records a specific bus does so through a bus QR scan or a typed bus number.
- The newer mass channels (WhatsApp 2024, Chalo on ONDC 2025) are described as route/stop-only, sometimes with AC/non-AC chosen by hand.

No source states that ONDC tickets bought by route selection have an empty vehicle field. One older design (Chartr 2020) required a bus-QR scan even on the route path.

### Cited Findings
- **FOR: bus identity is tied to a QR scan or a typed bus number.**
  - Tummoc validates on board by scanning the bus QR or typing the bus number. [Tummoc blog](https://blog.tummoc.com/?p=2344)
  - One Delhi has a bus-number lookup that sometimes fails. [App Store: One Delhi](https://apps.apple.com/in/app/one-delhi/id1641749010)
  - Chartr 2.0 starts with a QR scan. [App Store: Chartr 2.0](https://apps.apple.com/in/app/chartr-2-0/id6747386059)
- **FOR: route/stop-only channels exist, and they let riders buy off the bus.**
  - WhatsApp: source, destination, route, AC/non-AC, quantity, pay; no bus step. [Amar Ujala, Apr 2024](https://www.amarujala.com/automobiles/dtc-bus-ticket-booking-by-whatsapp-know-step-by-step-process-2024-04-11)
  - WhatsApp's "quick purchase" skips even the stop choice. [Business Today, Apr 2024](https://www.businesstoday.in/amp/technology/news/story/dtc-commuters-across-delhi-ncr-can-now-book-tickets-via-whatsapp-heres-how-425098-2024-04-11)
  - Chalo on ONDC: route and destination only. [Amar Ujala, Sep 2025](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24); [The Week / PTI](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **FOR: missing stickers cannot explain a uniform 48.5% blank share,** since the fleet-wide QR sticker deployment was reported in September 2025. [The Week / PTI](https://www.theweek.in/wire-updates/national/2025/09/23/des87-dl-cm-ld-interstate-buses.html)
- **AGAINST / complicating.**
  - In the 2020 Chartr flow, the "By Destination" path still ended with a bus-QR scan. [The Okhla Times](https://theokhlatimes.com/e-ticketing-dtc-buses/) So the outcome depends on each buyer app's implementation, not on "manual vs QR" as such.
  - Several QR systems co-exist in the bus. The September 2025 Universal QR is a UPI payment QR that may not produce ONDC tickets at all. [Amar Ujala, Sep 2025](https://www.amarujala.com/delhi-ncr/dtc-launches-automated-fare-collection-system-2025-09-24)
  - Some buses (e-buses) were reportedly never registered in One Delhi, so a scan or bus-number lookup could fail. [Swarajya](https://swarajyamag.com/amp/story/reports/delhi-has-the-buses-the-data-and-the-apps-why-cant-you-still-find-your-bus) The dataset's AC/non-AC parity argues this is minor.

### Inferences
- The most plausible reading is a mix of buyer-app/channel effects and rider choice. Some ONDC buyer apps sell by route/stop only (WhatsApp-style, Chalo); others offer a bus QR or bus number that riders can skip. That would spread blank tickets evenly across routes, bus types and fares, as the dataset shows.
- Checks to run on the dataset:
  1. Blank share by buyer app or network participant, if such a field exists. A near-0% versus near-100% split by app would be decisive.
  2. Purchase time of blank tickets relative to bus passages at the boarding stop. Many purchases before any bus arrives would mean riders bought at the stop.
  3. Tickets per transaction for blank and non-blank tickets.
  4. Whether the same rider or device alternates between blank and non-blank tickets.

### Gaps
- No Indian user post, tutorial or news item explicitly says "if you don't scan the bus QR, the ticket has no bus number". The link is inferred from flow descriptions.
- Which ONDC buyer apps were live for Delhi buses in October 2026 is not established here. Confirmed: One Delhi (2024) and Chalo (Sept 2025). Announced only: Chartr, Tummoc, WhatsApp, Paytm, redBus, EaseMyTrip. ([CXO Today, 2 Sep 2024](https://cxotoday.com/media-coverage/digital-qr-ticketing-for-dtc-buses-now-live-on-the-ondc-network/))
