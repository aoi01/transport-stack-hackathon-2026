# Matching romanized Indian (Hindi/Urdu/Punjabi-origin) place and bus-stop names — Delhi ticket stop names → GTFS stops

Research date: 2026-11-16. Scope: normalization rules, phonetic/transliteration-aware matching, Indian address-matching practice, abbreviations/landmark aliases and gazetteers, for raising the ONDC ticket stop-name → Delhi GTFS stop match rate (current: exact 55.7%, fuzzy 18.3%, nearby 5.5%, unmatched 20.6% of tickets).

Besides web sources, I ran a local, read-only experiment on the hackathon data (`data/raw/ticketing/October-Delhi.csv`, 2,559,899 tickets; `data/raw/gtfs_static`; the project's representative patterns `data/processed/patterns.parquet`). It reproduces the project matcher (`src/tsh/crowding.py`: `norm` → exact → `0.5·token_sort + 0.5·token_set ≥ 85`) and compares it with an Indic-aware cascade. Everything from that experiment is labelled **[local experiment]** and sits under *Inferences*, because it is my own measurement, not a published source. "Matched" there means a candidate was found, not that it was verified correct; precision was only eyeballed on small samples.

Headline numbers:
- The baseline replication matches the team's figure: 55.67% of tickets have both ends exact.
- The cascade cuts tickets with an unmatched end from 23.6% to 11.7% (tickets with both ends matched go from 74.6% to 86.5%). This is before any geographic "nearby" fallback.
- Published phonetic methods report high recall on Indian names: IndicSOUNDEX gets 96.5% on Hindi Latin/Devanagari name pairs. Back-transliteration with IndicXlit is only about 59–61% top-1 on Hindi.

---

## Q1. What systematic spelling variation occurs when Hindi/Urdu place names are written in Latin script, and are there published normalization rule sets?

### Takeaway
The variation comes from the system itself. India's official romanization (Hunterian) does not mark vowel length or retroflexion. In practice, people romanize phonetically and inconsistently, so a/aa, i/ee, u/oo, aspirated/unaspirated, v/w/b, z/j, schwa insertion/deletion and word joining/splitting ("Sagar Pur" vs "SagarPur") all occur. Both GTFS and ticket names contain them; GTFS alone has 397 groups of names that collapse to one key after phonetic folding. No published rule set targets Indian place names specifically. The closest published, citable rule sets are:
- the IndicSOUNDEX steps (merge aspirates, merge nasals, drop non-initial vowels, drop "h" after consonants, collapse repeats);
- the address-cleaning recipes in Indian geocoding papers (camel-case splitting, removing duplicate phrases).

### Cited Findings
- **Hunterian system.** It is described as India's "national system of romanization", "officially adopted by the Government of India". A 2007 UN Group of Experts manual calls it "the actually used national system of romanization in India".
  - In its base form, long and short vowels map to the same letter (आ/अ → a, ई/इ → i, ऊ/उ → u). Aspiration is written with "h" (kh, gh, ch, th, dh).
  - Dental and retroflex are not distinguished (त/ट → t, द/ड → d).
  - Nukta letters map to q, f, z (ज़ → z, फ़ → f).
  - Schwa deletion applies to place names, e.g. कानपुर → *Kanpur* rather than *Kanapura*.
  - The same UN citation also says there is "no evidence of the use of the system either in India or in international cartographic products". So its "official" status does not mean names on the ground follow it.
  - Source: [Wikipedia – Hunterian transliteration](https://en.wikipedia.org/wiki/Hunterian_transliteration)
- **Schwa deletion.** Hindi drops the inherent schwa in certain positions (the "schwa syncope rule", usually stated as a VC_CV environment). Romanizations differ in whether they show the deleted schwa — [Wikipedia – Schwa deletion in Indo-Aryan languages](https://en.wikipedia.org/wiki/Schwa_deletion_in_Indo-Aryan_languages). The pairs Mahavir/Mahvir and Indrapuri/Inderpuri are from this project's data, not from that source (see Inferences).
- **No standard romanization.** "Latin script to represent Indic languages is commonly used on the internet and is completely unstandardized leading to multiple spellings for the same word" — [DiPersio 2021 (IndicSOUNDEX)](https://cdn.amazon.science/86/4e/ebc49f01492d89307dbb45d0faf2/indicsoundex-algorithm-for-text-matching.pdf)
- **Dakshina dataset (Google Research, LREC 2020).** Native- and Latin-script data for 12 South Asian languages, including a romanization lexicon in which most words were romanized by more than one annotator, so variant spellings are attested — [Roark et al., arXiv 2007.01176](https://arxiv.org/abs/2007.01176); [dataset](https://github.com/google-research-datasets/dakshina)
- **Delhivery on why locality spellings vary.** "Most people know how to pronounce a locality name in their local language, but not its transliteration in English, which leads to a large number of spelling variations for the same locality name." — [K. Rustogi, "Learning to Decode Unstructured Indian Addresses" (Medium; I saw the search excerpt only, the page returned HTTP 403)](https://medium.com/@kabirrustogi/learning-to-decode-unstructured-indian-addresses-c80ffcda2e84)
- **GeoIndia (Meesho, EMNLP 2024 industry track).**
  - It lists misspelled locality/street names as a core issue, e.g. "daharahara chawk" written as "dharhara chowk".
  - Its cleaning pipeline: lowercase, trim punctuation, remove repeated words, merge ordinals ("1 st" → "1st"). It also does "probabilistic camel case splitting", where "NewDelhi" becomes "New Delhi" when that lower→upper transition is frequent in the data, and "redundant phrase reduction" ("Near Gandhi Market Gandhi Market" → "Near Gandhi Market").
  - Source: [Singhal et al., GeoIndia, EMNLP 2024 Industry](https://aclanthology.org/2024.emnlp-industry.29.pdf)
- **IndicSOUNDEX (Amazon Alexa AI, 2021) published rule set.**
  - Aspirated and unaspirated forms are merged into one code. All nasals are merged. Vowels after the first letter are dropped. "h" after a consonant code is removed. Consecutive identical codes are collapsed. Fifteen consonant classes keep place of articulation and voicing.
  - The first letter goes to a "modified ISO-15919" form with diacritics and the second letter of aspirate pairs removed.
  - A noted side effect: English th/sh/ch collapse to t/s/c.
  - Source: [DiPersio, IndicSOUNDEX, WWW'21 Workshop on Multilingual Search](https://cdn.amazon.science/86/4e/ebc49f01492d89307dbb45d0faf2/indicsoundex-algorithm-for-text-matching.pdf)
- **Commercial matchers.** A vendor blog says Indian address matching must treat "Laxmi/Lakshmi" and "12-B/12B" as equivalent and expand "M G Rd" to "Mahatma Gandhi Road". It reports no accuracy figures (marketing) — [HyperVerge blog](https://hyperverge.co/blog/address-match-onboarding-ai-india/)
- **Google's India address guidance** lists spelling errors in locality/city/state names and widely varying component order as typical problems — [Google Maps Platform – India address feedback](https://developers.google.com/maps/countries/india/india-address-feedback)
- **Toponym suffixes (glosses).** These elements carry meaning and must not be stripped as noise.
  - -pur: "city/settlement", Sanskrit *pura*
  - -nagar: "town", Sanskrit *nagara*; in modern use, residential colonies
  - -abad: Persian, "inhabited / town of"
  - -ganj: Persian-Urdu, "neighbourhood/market"
  - -garh: "fort"
  - Sources: [Wikipedia – Place names in India](https://en.wikipedia.org/wiki/Place_names_in_India); [Wikipedia – -pur](https://www.wikipedia.org/wiki/-pur)
- **Kalan and Khurd** are Persian for "big" and "small". They are administrative designations for the larger and smaller parts of a same-named settlement, so they are discriminative tokens — [DBpedia – Khurd and Kalan](https://dbpedia.org/page/Khurd_and_Kalan). Search results (Wikipedia mirrors) list Delhi examples such as Tikri Khurd and Khera Kalan; the Delhi GTFS itself has 52 "Kalan" and 45 "Khurd" tokens [local experiment].

### Inferences
- **[local experiment] What the GTFS and ticket names look like.**
  - GTFS `stops.txt` has 6,862 stops and 4,614 distinct `stop_name`s. 1,153 names contain "/" (joined alternates) and 499 contain "(".
  - Both joined and split suffix forms coexist in GTFS. Joined: 387 tokens end in "pur" and 172 in "puri". Split: "pur" appears as its own word 298 times and "puri" 241 times.
  - After my phonetic fold (below), **397 groups of distinct raw GTFS names collapse to one key**. Examples:
    - Subash / Subhash Place Depot
    - Prem Bari Pul / Prem Bari Pull / Prembari Pul
    - Buddh / Budh Vihar
    - Mangol Puri / Mangolpuri Y Block
    - Sultan Puri / Sultanpuri Crossing
    - Mubarak Pur Crossing / Mubarakpur Xing
    - Rohini Sec -16 / Sec-16 / Sector-16
    - Katevara / Katewara Village
  - So the inconsistency is inside GTFS too, and normalization must be applied symmetrically to both sides.
- **[local experiment] Variation classes in ticket names**, from what the cascade newly matched and what it left unmatched (ticket form → GTFS/OSM form):

  | Variation | Examples |
  |---|---|
  | Word segmentation | Sagar Pur→SagarPur, Shadi Pur→Shadipur, Seelam Pur→Seelampur, Roshan Pura→Roshanpura, Jahangir Puri→Jahangirpuri |
  | Vowel length / quality | Jeewan→Jivan, Rup→Roop, Swaroop→Swarup, Peera Garhi→Peeragarhi, Rajoukari→Rajokari, Goyla→Goela, Devoli/Devali→Devli |
  | Aspiration | Vashishth→Vashisht, Ramprashta→Ram Prastha |
  | Doubled consonants | Shakkar Pur→Shakarpur |
  | z/j | Hauz Rani→HaujRani |
  | v/b | Balmiki→Valmiki, Madhuvan/Madhuban, Pravat/Parbat |
  | Schwa insertion/deletion | Mahvir→Mahaveer, Rajindera→Rajendra, Inder Puri→Indrapuri |
  | ऋ written ri/ir | Kirshi→Krishi |
  | u/a for short a | Gunj→Ganj, Begam→Begum |
  | e/i | Rohella→Rohilla |
  | Diphthongs | Tamoor→Taimur, Narauji→Nauroji |
  | Typos | Blcok, Distrist, Collage, Sation |
  | Token order | P S Paharganj ↔ Paharganj Police Station |

- **Recommended symmetric canonicalization**, all deterministic and cheap in Python. It extends IndicSOUNDEX-style folding and the GeoIndia cleaning steps.
  1. Lowercase; "&" → "and"; remove "bus stop/bus stand/stop".
  2. Split letter–digit boundaries ("Sec21" → "sec 21", "A1" → "a 1"). Map roman numerals to digits ("Ph-III" → "phase 3").
  3. Expand abbreviations (Q4 table).
  4. Build several keys:
     - (a) space-free key;
     - (b) folded key: ee/ii → i, oo/uu/ou → u, au → o, w → v, z → j, q → k, x/ksh → ks, drop "h" after k/g/c/j/t/d/p/b/s/r, collapse doubled letters, word-final y → i;
     - (c) sorted-token folded key;
     - (d) consonant skeleton: keep the first letter, drop later vowels, v ~ b. Do not collapse repeated digits; I hit this bug myself, "22 20 21" collapsed toward "20 21".
  5. Keep numbers, single-letter block identifiers and Kalan/Khurd as hard-match tokens.
- **Do not fold v/b or drop vowels globally.** These folds help within a route's ~30–60 candidate stops but would create collisions over all 4.6k names. Use them only for route-restricted candidate sets, and only when they give a unique candidate.

### Gaps
- I found no published, evaluated rule set specifically for Indian toponym romanization: no dictionary of a/aa, gunj/ganj, pura/puri equivalences with a measured effect.
- I could not retrieve the ACL 2012 paper (from search snippets) that discusses the number of "valid transliterations and historical variants for many place names". It is not cited here.
- Urdu-origin spellings (q/k, kh/kh, z/j/zh, nukta forms) are not separately quantified anywhere I found.

---

## Q2. Phonetic and transliteration-aware matching methods — what works for Indian names and what accuracies are reported?

### Takeaway
Reported accuracies are mostly recall-style ("share of true pairs that get the same code") on person names, not precision on place names.
- IndicSOUNDEX is the strongest published phonetic option for Indic↔Latin: 96.5% on 9,280 Hindi Latin/Devanagari name pairs and 95.7% overall. It degrades to 44% when the two spellings differ by one phoneme.
- Back-transliteration to Devanagari with AI4Bharat IndicXlit is only about 59–61% top-1 for Hindi, so it is a weak canonicalizer.
- General name-matching studies find pattern matching (Jaro-Winkler, q-grams) beats pure phonetic codes.
- For stop/station matching specifically, a learned classifier on character trigrams plus distance reached F1 > 99%, against 94% for TF-IDF + distance and 75% for distance alone (European OSM data).
- GPT-4-class LLMs are strong zero-shot entity matchers, but no Indian place-name benchmark exists.

On this project's data, a deterministic Indic-aware cascade roughly halves the unmatched rate, and its new matches look high-precision in spot checks.

### Cited Findings
- **IndicSOUNDEX (2021) results.** Accuracy = share of same-word pairs that get identical codes. No false-positive rate is reported, so these are recall-like numbers.
  - Indic/Latin name pairs: Hindi **96.49% (8,954/9,280)**, Punjabi 88.64% (39/44), Marathi 100% (355/355), Tamil 58.79%, overall **95.71% (10,198/10,655)**.
  - Same-word pairs in native vs Latin script: Hindi 93.81% (397/404), Punjabi 88.00% (176/200).
  - ASR text variants of the same phoneme string: 82.00% overall, falling from 87.73% (2 variants) to 67.41% (9 variants).
  - Pairs differing by one phonemic substitution: only **44.09% (22,662/51,401)**, rising with length (36.27% at length 3, 92.50% at length 10).
  - The paper says American Soundex's false-positive rate "can be as high as 95%" in multilingual settings.
  - Source: [DiPersio 2021](https://cdn.amazon.science/86/4e/ebc49f01492d89307dbb45d0faf2/indicsoundex-algorithm-for-text-matching.pdf)
- **Earlier Indic phonetic work, as summarized in the same paper.**
  - Chaware & Rao (2012), Hindi pairs: custom Soundex 34%, Q-gram 68%, "Indic-Phonetic" 76%; Marathi pairs: 14%, 46%, 38%.
  - Shah & Singh (2014): 100% on 100 Hindi/Gujarati/English names, but their threshold accepted codes differing in up to two characters.
  - Sources: [DiPersio 2021](https://cdn.amazon.science/86/4e/ebc49f01492d89307dbb45d0faf2/indicsoundex-algorithm-for-text-matching.pdf); [Shah & Singh, IJCSEA 2014](https://airccse.org/journal/ijcsea/papers/4314ijcsea03.pdf)
- **Other Indic Soundex variants.**
  - "SoundexHindi" (SSRN, 2020) proposes phonetic matching for Hindi written in Roman script. I did not see evaluation numbers — [SSRN author page](https://papers.ssrn.com/author=3579322)
  - A 2016 paper argues that Soundex must be customized to "the nature, type and region" of Indian name data — [GJEIS](https://gjeis.com/index.php/gjeis/article/view/839)
- **Python packages.**
  - `libindic-soundex` implements English Soundex plus a modified Soundex for Indian languages, with cross-script `compare()` — [PyPI](https://pypi.org/project/libindic-soundex)
  - `indic-soundex` README examples map Sharma/Sarma → S650 and Krishna/Krushna → K625. These are illustrations, not a benchmark — [PyPI](https://pypi.org/project/indic-soundex/)
- **Christen (2006) personal-name matching comparison on four large name sets.**
  - "No clear best matching technique".
  - Pattern-matching methods clearly outperform phonetic encodings, and simple phonetic encodings beat complex ones.
  - Phonetic encoding followed by exact code comparison is not recommended. Small threshold changes can cause large quality drops.
  - Source: [Christen, slides, ICDM workshop 2006](https://cs.anu.edu.au/people/Peter.Christen/publications/mcd2006-slides.pdf)
- **I found no benchmark of Double Metaphone or NYSIIS on Indian names.** Search results only offered generic vendor comparisons. See Gaps.
- **IndicXlit (AI4Bharat) top-1 accuracy, romanized → native.**

  | Test set | Hindi | Punjabi | Urdu |
  |---|---|---|---|
  | Dakshina | 60.56 | 47.24 | 42.12 |
  | Aksharantar native words | 55.59 | 40.27 | 48.37 |
  | Aksharantar named entities | 58.87 | 36.08 | 47.77 |

  - Native → romanized named entities: Hindi 59.22.
  - The Dakshina Hindi baseline was 50.00, so 60.56 is an improvement over the prior baseline.
  - Package: `ai4bharat-transliteration`.
  - Sources: [IndicXlit GitHub](https://github.com/AI4Bharat/IndicXlit); [Aksharantar paper, arXiv 2205.03018](https://arxiv.org/abs/2205.03018)
- **LLMs on transliteration.** A 2025 benchmark of GPT-4o/4.1/4.5, Gemma-3 and Mistral-Large against IndicXlit on Dakshina and Aksharantar (top-1 and CER) says "GPT family models generally outperform … IndicXlit for most instances". The abstract gives no numbers — [Azam et al., arXiv 2505.19851](https://arxiv.org/abs/2505.19851)
- **Vendor claim (unverified).** IndicXlit scores 58.9% top-1 on the Aksharantar Hindi test, and the vendor's 0.87 MB model scores 65.9% — [Udgam Labs "Lekhani" model card](https://huggingface.co/udgamlabs/Lekhani)
- **Rule-based script converters.** Aksharamukha supports Harvard-Kyoto, ITRANS, Velthuis, IAST, ISO, SLP1, WX and "Roman (Readable)/(Colloquial)" formats. These are standardized schemes; I found no evaluation of them on informal romanizations like "Jahangirpuri" — [Aksharamukha GitHub](https://github.com/virtualvinodh/aksharamukha/)
- **Transit-station matching (Bast, Brosi, Näther 2020).** The task is deciding whether two (name, coordinate) station records are the same station.
  - A random forest on matching character trigrams, distance and grid position reached **F1 > 99%**.
  - Best baseline, TF-IDF + distance: **≤ 94%**. Distance threshold alone: **75%**. Hand-written normalization rules and string similarity were also baselines.
  - Ground truth came from OSM for UK/Ireland and Germany/Austria/Switzerland.
  - Open-source implementation: `statsimi` (Python 3 + scikit-learn; trains models, serves an HTTP classifier, evaluates).
  - Sources: [arXiv 2012.15267](https://arxiv.org/abs/2012.15267); [ad-freiburg/statsimi](https://github.com/ad-freiburg/statsimi)
- **Character n-gram TF-IDF.** Using character n-grams as TF-IDF terms turns fuzzy matching into sparse matrix multiplication. `string_grouper` and `PolyFuzz` use ING's `sparse_dot_topn` to keep only top-N matches above a threshold — [van den Berg, "Super fast string matching"](https://bergvca.github.io/2017/10/14/super-fast-string-matching.html); [string-grouper on PyPI](https://pypi.org/project/string-grouper/0.7.2/)
- **LLM entity matching (Peeters & Bizer).** GPT-4 without task-specific training beats fine-tuned RoBERTa/Ditto on 3 of 5 benchmarks by about 4% F1. On unseen, out-of-distribution entities the gap widens to 34–57% F1. Other LLMs benefit from in-context examples and rules (+5.9 and +2.2 F1 on average) — [arXiv 2310.11244](https://arxiv.org/abs/2310.11244)
- **Indian address classification (Myntra, 2020).** Edit-distance plus phonetic pre-processing, and RoBERTa at about 90% accuracy for sub-region classification — [Mangalgi et al., arXiv 2007.03020](https://arxiv.org/abs/2007.03020)

### Inferences
- **[local experiment] Baseline replication and the new cascade.**
  - The baseline was route-restricted to the project's representative pattern, without the "nearby" step. Over 5,029,354 ticket ends on routes present in GTFS: **exact 71.29%, fuzzy 14.99%, unmatched 13.72%**.
  - Per ticket (both ends): exact 55.67%, which matches the team's 55.7%. 18.93% have at least one fuzzy end, 23.62% have an unmatched end, and 1.77% have a route not in GTFS.
- **[local experiment] Cascade steps**, applied in order, all within the ticket route's candidate stops:
  1. baseline exact;
  2. abbreviation expansion + space-free key;
  3. phonetic folded key;
  4. sorted-token folded key;
  5. consonant skeleton (unique stop only);
  6. containment of folded keys, one a prefix/suffix of the other (unique stop only);
  7. generic-word-stripped "core" key (unique only);
  8. folded-key `ratio ≥ 88` with margin ≥ 4 over the runner-up;
  9. token fuzzy ≥ 90 on the normalized text.
- **[local experiment] Cascade results, share of ticket ends.**

  | Step | % of ends |
  |---|---|
  | exact | 71.29 |
  | abbreviation + space | 4.86 |
  | phonetic | 1.47 |
  | sorted | 0.97 |
  | skeleton | 1.85 |
  | containment | 9.39 |
  | core | 1.45 |
  | folded fuzzy | 1.43 |
  | token fuzzy 90 | 0.95 |
  | **unmatched** | **6.34** (was 13.72) |

  - Of the 13.72% baseline-unmatched ends, 8.60 points are recovered: containment 4.50, abbreviation + space 1.92, core 0.88, skeleton 0.40, folded fuzzy 0.38, phonetic 0.33, token fuzzy 0.16, sorted 0.03.
  - Per ticket, the share with an unmatched end falls from **23.62% to 11.73%**, and tickets with both ends matched rise from 74.6% to 86.5%, before any geographic fallback.
- **[local experiment] Precision spot-checks** (ticket-weighted random samples of *new* matches, my judgement):

  | Step | Plausible | Notes |
  |---|---|---|
  | abbreviation + space | 15/15 | e.g. "Narela Railway X-Ing"→"Narela Railway Crossing", "Shahbad Daulatpur Gaon"→"…Village", "G.T.K Depot"→"GTK Depot" |
  | phonetic | 15/15 | e.g. "Sagar Pur Vashishth Park"→"SagarPur Vashisht Park", "Shakkar Pur School Block"→"Shakarpur School Block", "Hauz Rani"→"HaujRani", "Jeewan Park"→"Jivan park" |
  | sorted tokens | 15/15 | "P S Paharganj"→"Paharganj Police Station", etc. |
  | skeleton | 14/15 | e.g. "Tamoor Nagar"→"Taimur Nagar", "Mahrishi Balmiki Hospital"→"Maharishi Valmiki Hospital", "Vishwavidhalaya"→"Vishwa Vidyalaya", "Narauji"→"Nauroji"; one digit-collapse artefact |
  | containment | 15/15 | e.g. "Jahangir Puri Metro Station"→"Jahangirpuri Metro Station GT Road", "Health Center"→"Najafghar Health Centre" on 578DOWN, "Igi Air Port Terminal-2"→"IGI Airport Terminal 2 (Air India Office)" |
  | core | ~5/15 clearly right | e.g. "Shadi Pur Metro Station"→"Shadipur Depot", "Govindpuri Ext"→"Govind Puri Metro Station" are doubtful. **Drop it, or add a distance/sequence check** |
  | folded fuzzy | 13/15 | "R K Puram Sec-12"→"…Sec13" is wrong |
  | token fuzzy 90 | 12/15 | wrong: "R K Puram Sector-8"→"Sec-5"; "Trilok Puri Blk-20/23"→"13 Block" |

  - Known containment failure: "Kirti Ngr Rly Reser Office" → "Kirti Nagar", where the GTFS key was a shorter prefix of the ticket key. Only accept containment when the *ticket* key is contained in the *GTFS* key.
- **[local experiment] The baseline fuzzy step makes real errors.** Among the 20 highest-volume cases where baseline and cascade picked different stops (1.11% of ends overall), the cascade was right in 14, the baseline in 2, and 4 were unclear. Typical baseline errors:
  - "Dwarka Sec-21 Metro Station" → "Dwarka Sec 9 Metro Station"
  - "R.K. Puram Sec-1" → "R K Puram Sec-5" or "Sec-12"
  - "Trilok Puri 13-Block" → "… 26 Block"
  - "A 1 Janak Puri" → "C1 Janak Puri"
  - "Saket A Block" → "Saket M Block"
  - "Dhansa Stand Najafgarh" → "Chawla Stand Najafgarh"

  These are the same failure as 'S.J. Hospital' → 'T.B. Hospital'. `token_set_ratio` rewards shared words and ignores that the *differing* tokens are identifiers. **Guard every fuzzy step: numbers, single letters and acronyms must match exactly.**
- **[local experiment] Keep a guarded token-set fuzzy as the last step.** 1.22% of ends were baseline-fuzzy matches that the stricter cascade rejected. In a sample of 20, about 17 were correct, mostly the ticket name being a subset of a longer GTFS name in another order: "Isbt Anand Vihar"→"Anand Vihar ISBT Main Road", "Badarpur Border"→"Badarpur Border (T)", "Supreme Court Metro Station"→"Supreme Court / Pragati Maidan Metro Station". One was wrong: "B 10/11 Vasant Kunj"→"Vasant Kunj B 8". So keep token-set fuzzy last, with the identifier guard and a best-vs-second margin.
- **Recommended cascade (playbook).** All steps are offline Python (rapidfuzz plus ~150 lines of rules) and fast on ~10k distinct names; my full run over 64,905 (route, name) pairs took about 90 s.
  1. Symmetric canonicalization (Q1) on both ticket and GTFS names. Split **both** sides on "/" and match any part; the project currently splits only GTFS names.
  2. Exact match on keys in order of increasing aggressiveness: canonical → space-free → folded → sorted-token → skeleton (skeleton only if unique on the route).
  3. Containment, ticket ⊂ GTFS only, with a unique stop on the route.
  4. Guarded fuzzy: identifier tokens equal, score ≥ 88–90, margin ≥ 4.
  5. Geographic fallback (Q3/Q4).
  6. Curated alias table for the residual head (Q4).

  Optionally, train a `statsimi`-style random forest (character trigram overlap + distance + route membership), using the high-confidence deterministic matches as positives and same-route non-matches as negatives.
- **Phonetic codes.** IndicSOUNDEX-style codes are best used as an extra *exact key* or a blocking key, not as the final decision. The published accuracies are recall-only, and Christen warns against relying on code equality alone. The 44% one-substitution result shows codes miss single-phoneme differences (Prehladpur/Pehladpur), which edit distance on folded keys handles: in my test 'Pul Prehladpur (Badarpur)' vs 'Pul Pehladpur (BadarPur)' scored 98.
- **Back-transliteration (IndicXlit).** Low priority. Top-1 is about 59% on Hindi named entities, so mapping two Latin spellings to the same Devanagari string will often fail. It also needs a heavier deep-learning stack (fairseq/torch), which I did not test on this Windows/Python 3.13 environment. If used, compare top-k beam *sets* for overlap rather than top-1 strings, as one feature among others.
- **LLMs.** The evidence (Peeters & Bizer) supports GPT-4-class models for zero-shot matching, including unseen entities. The practical use here is a one-off offline pass over the ~1.5k residual names: give the model the route's GTFS stop list and record proposals in a reviewed alias table. Per-ticket online LLM calls are unnecessary.
- **Sentence embeddings.** Multilingual sentence embeddings are a poor fit for 1–4-token proper names with spelling noise. I found no evidence they beat character n-grams on Indian names. Character n-gram TF-IDF (`string_grouper`/`sparse_dot_topn`) is the scalable embedding-like option if a global (non-route) search is needed.

### Gaps
- No published evaluation of Double Metaphone, NYSIIS or Beider-Morse on romanized Indian *place* names. No precision/false-positive numbers for IndicSOUNDEX.
- No published benchmark of LLMs or embeddings for matching romanized Indian place/stop names.
- No labelled ground truth for this project's tickets. The local precision numbers are eyeballed samples of 15–20, not proper estimates. A stratified labelled set (e.g. 300 (route, name) pairs across the cascade steps) is needed to set thresholds.
- I did not run IndicXlit, libindic-soundex or IndicSOUNDEX locally. Installing packages was out of scope.

---

## Q3. Indian address/geocoding research and industry practice — which techniques transfer to stop names?

### Takeaway
Indian logistics, e-commerce and maps companies use the same toolkit:
- normalization (case/punctuation, camel-case splitting, duplicate-phrase removal, abbreviation expansion);
- phonetic fuzzy matching "tuned for Indian languages" on locality tokens;
- scoring addresses component by component;
- most importantly, restricting candidates geographically (pincode/H3 cell); for stops, the analogue is the ticket's route plus distance.

Reported results are system-level (locality correct for >90% of shipments; >50% lower mean geocoding error than Google Maps), not string-matching precision. The parts that transfer are the cleaning recipes, phonetic fuzzy matching on name tokens, distinguishing locality tokens from landmark/type words, and geography as a hard constraint.

### Cited Findings
- **Delhivery.**
  - Its address tool (AddFix) uses a "phonetic distance based fuzzy search, which is specifically tuned for Indian languages". It reportedly gets the locality/sub-locality right for ">90%" of shipments, with a median geocode precision of about 200 m — [Rustogi, Medium (search excerpt; page blocked)](https://medium.com/@kabirrustogi/learning-to-decode-unstructured-indian-addresses-c80ffcda2e84)
  - AddFix is patented; it splits addresses into locality, street, landmark and other components — [Business Today, 2022](https://www.businesstoday.in/amp/latest/story/delhivery-bags-patent-for-proprietary-technological-solution-addfix-335351-2022-05-27)
  - Delhivery Maps' Address Validation API "uses an LLM" to flag and correct typos, missing pincodes and locality names, with four granularity tiers (premise, street, sub-locality, locality) — [Delhivery Maps developer page](https://www.delhivery.com/maps/developer)
- **GeoIndia (Meesho).**
  - A seq2seq geocoder for Indian addresses: Flan-T5-base (220M, fully fine-tuned) vs Llama-3-8B (QLoRA), predicting H3 cells. It uses a SentencePiece tokenizer trained from scratch on 67 million Indian addresses "to handle regional variations".
  - It cuts mean distance error by >50% and P99 error by >85% versus Google Maps "in multiple states". Bihar: 62.5% mean-error reduction on seen data, 47.3% on unseen.
  - Pre-processing includes coordinate validation and the cleaning steps listed in Q1.
  - Source: [GeoIndia, EMNLP 2024 Industry](https://aclanthology.org/2024.emnlp-industry.29.pdf)
- **Delivery-hub geocoding (COLING 2025 industry).** Targets exact customer locations for delivery-hub assignment. It describes an earlier Indian geocoder, SAGEL, that ranks candidates with graph techniques (search excerpt only) — [COLING 2025 Industry 19](https://aclanthology.org/2025.coling-industry.19.pdf)
- **Swiggy (Bundl Technologies) authors.** Mine points of interest from address embeddings: addresses are pre-processed with locality names and embedded with a RoBERTa model trained on an internal address dataset (search excerpt) — [arXiv 2109.04467](https://arxiv.org/pdf/2109.04467)
- **Myntra.** Address sub-region classification at about 90% accuracy with RoBERTa; pre-processing combines edit distance and phonetic algorithms — [arXiv 2007.03020](https://arxiv.org/abs/2007.03020)
- **Google.** Its Address Validation API for India uses an ML model for parsing and correcting addresses. Documented Indian issues include misspelled locality names and variable component order — [Google Maps Platform blog](https://mapsplatform.google.com/resources/blog/announcing-address-validation-api-with-machine-learning-for-india/); [India address feedback doc](https://developers.google.com/maps/countries/india/india-address-feedback)
- **India Post DIGIPIN.**
  - A 10-character alphanumeric code for an approximately 4 m × 4 m grid cell, derived from latitude/longitude. Developed with IIT Hyderabad and ISRO's NRSC, and open-sourced.
  - Sources disagree on the launch date (2024 vs a May–June 2025 public rollout).
  - Sources: [INDIAPOST-gov/digipin](https://github.com/INDIAPOST-gov/digipin); [The Week, 31 May 2025](https://www.theweek.in/news/sci-tech/2025/05/31/what-is-digipin-india-new-technology-postal-geo-address-system-department-of-posts.html)
- **Vendors.** Describe component-wise scoring with adjustable weights, e.g. credit for a strong locality match even when the flat number is missing. No metrics reported — [HyperVerge](https://hyperverge.co/blog/address-match-onboarding-ai-india/)
- **MapmyIndia (Mappls) and Ola Krutrim.** I found no public engineering write-ups on their name normalization.

### Inferences
- **[local experiment] Geography as a constraint.** For residual names that exist in GTFS under the same folded or skeleton key but not on the ticket's route (3.11% of ticket ends after the cascade), I measured the distance from that same-key GTFS stop to the nearest stop on the ticket's route:

  | Within | Share of these ends |
  |---|---|
  | 100 m | 30.5% |
  | 200 m | 58.0% |
  | 400 m (current setting) | 78.5% |
  | 600 m | 92.6% |
  | 1,000 m | 95.7% |

  - Raising the fallback radius from 400 m to about 600 m recovers about 14 points of this group, roughly 0.4–0.5% of all ends. Validate on labelled data before adopting.
  - The cases beyond 1 km are generic names: "Telephone Exchange" (2.5–4.0 km), "Power House" (10.6 km), "Ram Pura" (15.7 km), "Dtc Colony", "Gurudwara", "Nehru Vihar", "Dichau Kalan Depot". The global name→location lookup should **exclude generic/landmark-type names** (or require route uniqueness), because the same-named place elsewhere in Delhi is the wrong place.
- **Transferable from Indian address systems, in priority order.**
  1. Treat locality tokens (Mahipalpur, Rangpuri) and type/landmark tokens (village, crossing, metro station, hospital) differently, i.e. component-wise scoring with token weights. IDF weights computed over the 4.6k GTFS names do this automatically.
  2. Phonetic fuzzy matching on locality tokens only.
  3. Camel-case and space splitting, plus duplicate-phrase removal (GeoIndia).
  4. An LLM pass for typos and aliases, used offline (Delhivery Maps' API does this online).

  DIGIPIN is not needed for name matching: tickets have no coordinates and GTFS already has lat/lon. At most, it is a convenient grid key for spatial blocking.

### Gaps
- None of the Indian industry sources report string-level precision/recall for locality-name matching; the numbers are end-to-end delivery or geocoding metrics.
- I could not open the Delhivery Medium post (HTTP 403). Its details (exact phonetic algorithm, tuning) come from search excerpts only.
- I found no MapmyIndia or Ola/Krutrim public material on transliteration-aware matching.
- The Amazon India tech blog on "loosely structured addresses" and Flipkart's address-clustering paper (Kakkar & Babu, SIGIR eCom 2018) appeared in results but I did not read them.

---

## Q4. Abbreviations and landmark aliases — how to handle them, and which gazetteers of Delhi aliases exist?

### Takeaway
Abbreviations are frequent and inconsistent on **both** sides. For example, GTFS uses "Sec" 446 times and "Sector" 103 times; "Xing" 125 times and "Crossing" 448 times. A symmetric expansion table is the single cheapest gain: about 4.9% of ticket ends in my run.

Landmark acronyms (S.J., NSIC, AIIMS, MCKR, ATS, SNPD) and alternate names need an alias table. The residual is very concentrated: after the cascade, the top 200 unmatched names cover 74% of unmatched ticket ends, so a curated table is feasible.

External gazetteers are thin:
- OSM Delhi has about 2.4k bus-stop nodes, only 228 with `name:hi`, 71 with `alt_name` and 51 with `short_name`.
- Wikidata has Hindi labels for major localities and metro stations but not ticket-style abbreviations.
- I found no official bilingual DTC stop list.

### Cited Findings
- **OSM Delhi bus stops.** My Overpass query (OSM snapshot 2026-11-16 03:08 UTC; area `ISO3166-2=IN-DL`; `highway=bus_stop` or `public_transport=platform`+`bus=yes`) returned **2,421 nodes**:

  | Tag | Nodes |
  |---|---|
  | `name` | 2,110 |
  | `name:hi` | 228 |
  | `name:ur` | 30 |
  | `name:en` | 101 |
  | `alt_name` | 71 |
  | `short_name` | 51 |
  | `official_name` | 5 |
  | `operator` | 329 |

  - `alt_name` examples: Vasant Kunj Sector A → "ILBS"; National Small Industries Corporation → "Modi Mill"; Moolchand Khairati Ram Hospital → "Moolchand Hospital"; Shakarpur School Block S-1 → "Lakshmi Nagar;Laxmi Nagar"; Inderpuri → "Indrapuri"; Airport → "Domestic Airport;Palam Airport"; Dwarka Flyover → "Palam Flyover;Palam Phatak".
  - `short_name` examples: "AIIMS", "N.S.I.C.", "MCKR Hospital", "ARSD College", "SNP Depot" (Sriniwaspuri Depot), "IP Depot" (Indraprastha Depot), "R.K. Puram Sector 7", "NDPO".
  - `name:hi` example: Shakarpur Crossing → "शकरपुर मोड़". Hindi *मोड़ (mor/more)* is used for "crossing/turn".
  - Data © OpenStreetMap contributors, ODbL, via [Overpass API](https://overpass-api.de/).
- **OSM Delhi bus mapping status.** The Delhi/Buses wiki tracks 83 DTC routes (8 complete, 25 one side complete, 50 partial); last edited 4 June 2024 — [OSM wiki Delhi/Buses](https://wiki.openstreetmap.org/wiki/Delhi/Buses)
  - An import of the DIMTS dataset (stops and routes, public domain) was at the planning stage as of 10 July 2025. Stops sharing a name within a neighbourhood would be ignored. I found no evidence it has run — [OSM wiki Delhi/Buses/Import/Plan](https://wiki.openstreetmap.org/wiki/Delhi/Buses/Import/Plan)
- **Wikidata labels** (my API query):
  - Badarpur ([Q2563426](https://www.wikidata.org/wiki/Q2563426)): hi "बदरपुर", ur label.
  - Jahangirpuri metro station ([Q862598](https://www.wikidata.org/wiki/Q862598)): hi "जहांगीरपुरी".
  - Najafgarh ([Q6959903](https://www.wikidata.org/wiki/Q6959903)): hi "नजफगढ़", with hi aliases "नजफगढ" and "नजफ़गढ़" (nukta variants).
  - Safdarjung Hospital is labelled "Safdarjang Hospital" ([Q7398430](https://www.wikidata.org/wiki/Q7398430)), with ur/pa labels but no hi label and no English alias such as "S.J. Hospital".
- **Official and third-party stop lists.**
  - The OTD portal publishes Delhi bus GTFS — [OTD documentation](https://otd.delhi.gov.in/documentation)
  - Chartr's GTFS editor covers "6,800+" Delhi stops with names and coordinates — [Chartr](https://chartr.in/products/gtfs/)
  - DTC publishes route and time-table PDFs in English, e.g. [destination bus services Oct 2025](https://dtc.delhi.gov.in/sites/default/files/2025-10/destination_bus_services_oct_2025.pdf)
  - Searches in English and Hindi ("डीटीसी बस स्टॉप नाम सूची") found **no bilingual (Hindi/English) DTC stop list**.
  - A secondary site claims DTC runs 4,270 stops on 732 routes (unverified) — [Housing.com](https://housing.com/news/dtc-bus-route-know-bus-timing-stops-and-destinations)
- **Vendor abbreviation examples.** Address matchers expand "M G Rd" → "Mahatma Gandhi Road" and handle "Fourth Ln" vs "4th Lane" — [HyperVerge](https://hyperverge.co/blog/address-match-onboarding-ai-india/)

### Inferences
- **[local experiment] Abbreviation frequency** (ticket ends, total 5.12M, vs GTFS stop-name tokens):

  | Form | Ticket ends | GTFS tokens |
  |---|---|---|
  | crossing / xing / x-ing | 261,686 / 117,308 / 31,987 | 448 / 125 / 0 |
  | sector / sec | 23,106 / 90,764 | 103 / 446 |
  | terminal / (t) | 283,791 / 87,010 | 159 / 53 |
  | extension / ext / extn | 47,443 / 14,997 / 11,377 | 39 / 16 / 8 |
  | isbt | 71,139 | 34 |
  | gtb | 18,292 | — |
  | gaon | 15,067 | 18 |
  | nh8 | 12,456 | 4 |
  | hosp | 6,408 | — |
  | bdr | 1,375 | 1 |
  | ph / phase | 1,125 / 21,714 | 11 / 70 |
  | mkt | 407 | 1 |
  | jn | 86 | 1 |

  Both sides mix forms, so expansion must be symmetric.
- **Recommended abbreviation table** (applied before tokenizing, on both sides):

  | Abbreviation(s) | Expansion / handling |
  |---|---|
  | sec, sect, sctr | sector (**but** "Delhi Sect." = Delhi Secretariat, so resolve by route context) |
  | extn, ext | extension |
  | ph, roman numerals | phase; roman numerals → digits |
  | mkt | market |
  | bdr | border |
  | xing, x-ing, x ing | crossing |
  | jn, jnc, jct | junction |
  | rd | road |
  | stn | station |
  | hosp | hospital |
  | vill, vlg, gaon | village |
  | cly, clny | colony |
  | encl | enclave |
  | ngr | nagar |
  | rly | railway |
  | engg | engineering |
  | govt | government |
  | sch | school |
  | pkt | pocket |
  | blk, blcok | block |
  | indl | industrial |
  | apts | apartment |
  | centre | center |
  | more, mor, morh, mod | mor (Hindi मोड़ "turn", ≈ crossing) |
  | chauk, chok | chowk |
  | takies | talkies |
  | p.s., ps | police station |
  | nh-8, nh 8 | nh8 |
  | (t) | optional "terminal" flag; tickets often omit it, e.g. "Badarpur Border" vs GTFS "Badarpur Border (T)" |

- **Landmark-acronym alias seeds.**
  - Expansions verified via OSM tags: AIIMS = All India Institute of Medical Sciences; NSIC = National Small Industries Corporation (also "Modi Mill"); MCKR = Moolchand Khairati Ram Hospital; SNP Depot = Sriniwaspuri Depot; IP Depot = Indraprastha Depot; ARSD = Atma Ram Sanatan Dharma College; ILBS ≈ Vasant Kunj Sector A.
  - Expansions from general knowledge, to be verified before use: S.J. = Safdarjung (S.J. Hospital, S.J. Air Port, S.J. Terminal); GTB Nagar = Guru Tegh Bahadur Nagar; ITO = Income Tax Office; BSZ Marg = Bahadur Shah Zafar Marg; IGI = Indira Gandhi International; LSR = Lady Shri Ram College; INA; GPO; PSRI; V V Depot = Vasant Vihar Depot; ATS Tower; Isbt K.Gate = ISBT Kashmere Gate.
- **[local experiment] Residual concentration.** After the cascade, 1,460 distinct ticket names remain unmatched (6.34% of ends). The top 25/50/100/200/400 names cover 29.0/41.9/57.4/74.4/89.3% of unmatched ends.
  - Top residual names include: Badarpur Border (9,260 ends; a "(T)"-suffix issue); "Nhai / District Court / Ig Hospital Dwarka Sec 10"; Mahipal Pur; District Centre Janak Puri; B Block Mangol Puri Ring Road (plus typo variants "B- Blcok…", "B-Block…"); Snpd; Inder Puri Kirshi Kunj; Majlis Park; Swaroop Nagar; Ats Tower; S.J. Terminal; Qutab Enclave; Anand Pravat; Modi Mills; Delhi Sect.; Ina Cly; L.S.R. Collage; V V Depot; Isbt K.Gate.
  - A one-off curated alias table of about 200 names, with LLM-proposed and human-reviewed candidates restricted to the route's stops, would remove about three quarters of what is left.
- **[local experiment] OSM as an alias source.** Matching the residual not-in-GTFS names against OSM `name`/`alt_name`/`short_name`/`name:en` by skeleton key resolved 68 of 820 names (0.63% of ends). Examples: Badarpur Border; "Mahipal Pur"→"Mahipalpur"; "District Centre Janak Puri"; "Mohammed/Mohamed Pur"→"Mohammadpur"; "Mckr Hospital"; "Jahangripuri Metro Station" (typo); "Prehlad Pur/Prahlad Pur"→"Prahladpur"; "Jawahar Lal Nehru Stadium"; "Gpo"; "Psri Hospital"; "Igi Stadium"→"Indira Gandhi Stadium". Each hit gives a coordinate for the geographic fallback.
  - OSM `name:hi` (228 nodes) is too sparse to support a Devanagari-pivot strategy for the 6.9k GTFS stops.
- **Mining aliases from GTFS itself.**
  - The 1,153 "/"-joined names are alias sets: split, index each part, and when matching use the first part *or any part*.
  - Co-located GTFS stops with different names (e.g. within ~50–100 m) are alias candidates too. "S.J. Hospital" exists as a GTFS name somewhere but not on the routes where tickets use it.
  - Ticket names also contain "/" (982 of 7,471 distinct names). Splitting them would address cases like 'Reddison Hotel Mahipal Pur / Rang Puri (Nh8 Circle)': its part "Rang Puri" is contained in GTFS 'Rang Puri (Airport Road)'.
- **Disposition of the team's failure examples** (from my run):

  | Example | Disposition |
  |---|---|
  | 'Aerocity' | Solved by space-free key + containment (1,817 ends on D-9101UP) |
  | 'Jahangir Puri Metro Station' | Solved by containment |
  | 'Sagar Pur Vashishth Park' | Solved by phonetic fold |
  | 'Health Center' | Solved by containment (unique on 578DOWN) |
  | 'Badarpur' | Containment works when "Badarpur Village" is the only Badarpur stop on the route; when it isn't unique it stayed unmatched (5,626 ends; the name exists elsewhere in GTFS), so it needs the geographic fallback |
  | 'S.J. Hospital' | Needs the identifier guard (reject → T.B. Hospital) plus the alias S.J. = Safdarjung or the geographic fallback (exists in GTFS elsewhere; 8,152 ends) |
  | 'Said Ul Zeb Village' | Exists in GTFS but not on the ticket's route (3,990 ends). The village is Said-ul-Ajaib (general knowledge); the GTFS on such routes reads "Saket Metro Sation / Said-ul-Ajaib", and folded fuzzy matched the ticket form "Saidulajab" to it. So: alias plus geographic fallback |
  | 'Nsic Hostel' | Alias via OSM NSIC / "Modi Mill" |
  | 'Telephone Exchange' | Generic; same-named GTFS stops are 2.5–4 km away, so it needs a route-specific manual alias |
  | 'Pul Prehladpur (Badarpur)' | Folded-key fuzzy (98) |
  | 'Reddison Hotel … / Rang Puri (Nh8 Circle)' | Split the ticket name on "/" and match parts |

### Gaps
- No official bilingual (Hindi/English) DTC/DIMTS stop list found. The OTD GTFS has English names only, and the DIMTS→OSM import has not happened.
- Wikidata coverage of Delhi bus stops is essentially limited to localities and metro stations. I did not run a systematic count.
- I did not verify libpostal's abbreviation dictionaries for Indian forms (Extn, Xing, Bdr).
- Several acronym expansions above (S.J., GTB, LSR, V V, ATS, SNPD) are general knowledge, not sourced. They should be confirmed with route-level evidence (stop sequence, coordinates) before entering the alias table.
