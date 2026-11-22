# Demo video script (about 2 min 30 s)

Upload limit: mp4, 10 MB. Record the browser at 1280×720, then compress (command at the end).
Before recording: start the server (`python -m uvicorn app.server:app --app-dir . --port 8000`), wait until
`http://localhost:8000/health` answers, and run each search once so the answers come back fast.

| Time | Screen | Narration (English) |
|---|---|---|
| 0:00–0:15 | `http://localhost:8000/` | "This is a journey planner for Delhi buses. Every time you see is learned from what buses actually did in October 2026 GPS, plus live positions — not from the timetable." |
| 0:15–0:45 | Default search (Kashmiri Gate → Nehru Place, Depart at 2026-11-17 08:30, Fastest) → Search; click the first option | "Each option shows walk, wait and ride. The wait says where it comes from — here, when buses actually passed this stop on past days. Next to the ride time you see the timetable's time and the time at 14:00. The safe arrival is the 85th percentile: we replay this exact journey on 21 past weekdays and recalibrate it on a separate week." |
| 0:45–1:05 | Change Time to **Arrive by** 2026-11-17 09:30 → Search | "Arrive-by gives the latest departure that made it on 85% of past days. Leaving at the timetable's latest departure gets you there on time only 30% of the time; ours, 80% on a week the model never saw." |
| 1:05–1:20 | Set Time to **Depart at** with the current date and time → Search (live) | "If you leave now, the first wait comes from live bus positions: a bus visible upstream, or one about to turn back at the terminus. The text tells you how often similar live predictions were off by more than 10 minutes." |
| 1:20–1:35 | Sort → **Fewest transfers**, then **Most comfortable** | "You can sort by fewest transfers, or by comfort, which weights crowding estimated from e-tickets." |
| 1:35–2:10 | `http://localhost:8000/passages` → pick a route (e.g. 764UP) and a day → play | "This is the evidence behind it. For any route and day you see the raw GPS, which point became each stop passage, every bus of the line moving at once, and the time–distance diagram against the timetable. Gaps and bunching are visible: buses don't keep the timetable, and many turn back before the terminus." |
| 2:10–2:30 | README results table (GitHub) | "On a held-out week, the door-to-door error is 13.6% leaving now and 16.1% planning ahead, against 24–25% for the timetable. Code, proposal and technical note are in the repository." |

## Compress to under 10 MB

```powershell
ffmpeg -i demo_raw.mp4 -vf "scale=1280:-2,fps=15" -c:v libx264 -preset slow -crf 30 -c:a aac -b:a 64k demo.mp4
```

If the file is still over 10 MB, raise `-crf` to 32–34 or scale to 960 wide.
