# Team Contributions

| Member | Main responsibilities | Experiments/report sections | Agreed contribution % |
|---|---|---|---:|
| Foo Chao | Browser caption-state Map and revision replacement; stale/duplicate rejection and final-caption protection; server revision validation; scrollable live-caption area; optional regression tests; setup documentation; helped divide team tasks. | Ran T1 correctness, T2 scale and an additional 1,000-client T2max experiment; checked the results and recorded T1/T2 configurations, results and analysis for the report. | 25% |
| Jun Kiat | Implement bounded server history with time-based expiry; Implement rolling client-side history for 15/30/60 seconds recall; optional regression tests | Ran T5 network impairment; checked the results and recorded T5 configurations, results and analysis for the report. | 25% |
| Member 3 | Browser automatic reconnect; finalized resume tracking independent of local expiry; ordered HISTORY merge with revision/final protection; recovery regression tests and demo documentation. | Browser recovery tests and a local WebSocket smoke check; public T4 experiment pending. | 25% |
| Daniel Zhou | Server per-client delivery: bounded outbox per client with one sender task (`client_outbox.py`, `send_loop()`); semantic coalescing that drops obsolete queued provisionals and never drops finals; overflow policy (32 messages / 15 s lag, close with 1013 and recover through HISTORY); ordered HISTORY/live handoff fixing the missed-update race; reduced per-connection send buffering; outbox unit tests and a stalled-client server integration test; backpressure and overload design notes. | Ran T3 slow readers against the naive and outbox servers and explained why loopback buffering hides slow readers from any server; ran the required before/after comparison under the 2 Mbit/s profile with 600 clients (P95 −38%, final completeness 97.85% → 99.62%); recorded configurations, results and analysis. | 25% |

Total agreed contribution: 100%.

The remaining members should fill in their names and contributions. Git history
is supporting evidence for this statement.
