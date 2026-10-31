# LiveRecall experiment results

Results for the public-experiments section of the final report.
Each experiment below records its own setup, command, results and analysis.

## Shared environment and method

Each experiment records its setup, command, results and analysis in its own
section. Record any differences in VM configuration, network profile or test
parameters within the relevant experiment section.

Activate the virtual environment and run commands from the project folder.
Stop any manually running server and caption source first. The supplied runner
starts a fresh server for each independent run and uses the deterministic source.
Its default source timing is 0.20 s between revisions and a 0.35 s gap after each
final. These workloads generate three revisions per segment; the implementation
does not assume that count.

Reported medians are calculated separately for each metric across three run
summaries. Percentiles are calculated within each run before taking their median;
samples from different runs are not pooled. Values are rounded only for display.

T1-T5 were rerun on the integrated server: `develop` at commit `54b733a`
(Member 3's browser recovery plus Member 4's per-client outboxes). All runs used
a native Ubuntu 24.04.4 host (i7-13620H, 16 threads, 15 GiB RAM) with Python
3.12.3 and websockets 16.1.1. The earlier T1, T2 and T5 results, measured on the
naive broadcaster in an Ubuntu VirtualBox VM, remain in git history at commit
`1532e6a`; they were taken on a different machine, so they are not a controlled
comparison with these results.

The saved summaries match re-analysis of the corresponding CSV logs using the
supplied `analyse_results.py`. Preserve the logs before rerunning with the same
output stems, since the runner overwrites them.

## T1 Basic correctness

### Purpose and setup

Verify revision/final delivery, duplicate/stale counts and normal update
coverage with 20 clients on the normal local-network profile.

The server and simulated clients ran on the shared Ubuntu host, using
`ws://127.0.0.1:8765`. No deliberate network impairment was
added. The run used seed 3103, a 500 ms freshness threshold, and no slow readers,
forced disconnects or late joiners.

| Setting | Value |
|---|---:|
| Simulated clients | 20 |
| Requested duration per run | 20 s |
| Independent runs | 3 |
| Finalized segments generated per run | 22 |
| Revisions generated per run | 66 |

### Command

```bash
python run_demo.py --clients 20 --duration 20 --runs 3 --output-stem t1
```

### Results

| Metric | Median across 3 runs |
|---|---:|
| P50 Caption Age | 2.88 ms |
| P95 Caption Age | 4.36 ms |
| P99 Caption Age | 5.24 ms |
| Fresh Caption Ratio at 500 ms | 100% |
| Fresh Final Caption Ratio at 500 ms | 100% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 100% |

Every run recorded zero duplicates, stale updates, invalid non-final history
items and client connection errors. Each client received all 22 finals:
440 final deliveries and 1,320 accepted live updates across 20 clients per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 2.88 | 4.36 | 5.24 | [JSON](t1_run01.json) | [CSV](t1_run01.csv) |
| 2 | 2.77 | 4.35 | 4.99 | [JSON](t1_run02.json) | [CSV](t1_run02.csv) |
| 3 | 2.99 | 4.88 | 5.49 | [JSON](t1_run03.json) | [CSV](t1_run03.csv) |

### Analysis

All generated revisions and final captions reached every simulated client,
with no observed stale or duplicate updates. Completeness and update coverage
were both 100%, so the freshness result was not obtained by discarding
provisional revisions. All accepted updates and generated finals were delivered
within 500 ms in all three runs.

This supports correct normal delivery under the tested workload. The source
sends increasing revisions, so these results alone do not prove rejection of
deliberately stale/duplicate input; the separate optional regression tests check
those cases. Browser rendering and visual revision replacement require a manual
browser check. Recovery was not exercised by this workload. Every client kept up,
so no outbox coalesced anything: the 100% coverage is every revision delivered.

## T2 Public scale

### Purpose and setup

Measure normal concurrent delivery, latency, freshness, completeness and update
coverage with 100 clients.

The server and simulated clients ran on the shared Ubuntu host, using
`ws://127.0.0.1:8765`. No deliberate network impairment was
added. The run used seed 3103, a 500 ms freshness threshold, and no slow readers,
forced disconnects or late joiners.

| Setting | Value |
|---|---:|
| Simulated clients | 100 |
| Requested duration per run | 40 s |
| Independent runs | 3 |
| Finalized segments generated per run | 49 |
| Revisions generated per run | 147 |

### Command

```bash
python run_demo.py --clients 100 --duration 40 --runs 3 --output-stem t2
```

### Results

| Metric | Median across 3 runs |
|---|---:|
| P50 Caption Age | 6.76 ms |
| P95 Caption Age | 12.08 ms |
| P99 Caption Age | 15.25 ms |
| Fresh Caption Ratio at 500 ms | 100% |
| Fresh Final Caption Ratio at 500 ms | 100% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 100% |

Every run recorded zero duplicates, stale updates, invalid non-final history
items and client connection errors. Each client received all 49 finals:
4,900 final deliveries and 14,700 accepted live updates across 100 clients per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 6.38 | 10.74 | 12.20 | [JSON](t2_run01.json) | [CSV](t2_run01.csv) |
| 2 | 6.76 | 12.62 | 15.54 | [JSON](t2_run02.json) | [CSV](t2_run02.csv) |
| 3 | 7.21 | 12.08 | 15.25 | [JSON](t2_run03.json) | [CSV](t2_run03.csv) |

### Analysis

All 100 clients received every generated revision and final caption within the
freshness threshold. Compared with T1, median P95 Caption Age increased from
4.36 ms to 12.08 ms and median P99 from 5.24 ms to 15.25 ms, while completeness
and update coverage remained 100%.

More clients require more sends per caption. The increased latency is consistent
with that extra work, but the measurements do not isolate it from scheduling,
client logging or other overhead. T1 and T2 also differ in duration and segment
count, so their comparison is not a controlled optimization experiment.

These results support normal operation at the tested population of 100 clients.
T2 does not exercise slow clients, bounded per-client buffering or overload; see
T3 and the 2 Mbit/s before/after comparison.

## T5 Network Impairment

### Purpose and setup

Evaluate caption correctness and freshness with 100 clients under network delay, jitter and packet loss.

The server and simulated clients ran on the shared Ubuntu host using local loopback. The supplied delay_loss.sh profile applied 120 ms delay, 30 ms jitter and 3% packet loss to lo. Each experiment used 100 clients, a requested duration of 40 seconds and three independent runs. The freshness threshold was 500 ms. No slow readers, forced disconnects or late joiners were deliberately configured.

### Command

```bash
sudo ./network_profiles/delay_loss.sh lo
python run_demo.py --clients 100 --duration 40 --runs 3 --output-stem t5
```

Reset the network afterwards:

```bash
sudo ./network_profiles/reset.sh lo
```

### Results

| Metric | Median across 3 runs |
|---|---:|
| P50 Caption Age | 252.55 ms |
| P95 Caption Age | 632.29 ms |
| P99 Caption Age | 911.35 ms |
| Fresh Caption Ratio at 500 ms | 93.39% |
| Fresh Final Caption Ratio at 500 ms | 90.61% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 97.85% |

Every run recorded 100 successful client connections, zero connection errors, zero duplicates, zero stale updates and zero invalid non-final history items. Every client received all 49 finalized segments, giving 4,900 final-caption deliveries per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 252.55 | 621.33 | 911.35 | [JSON](t5_run01.json) | [CSV](t5_run01.csv) |
| 2 | 257.75 | 655.72 | 1122.88 | [JSON](t5_run02.json) | [CSV](t5_run02.csv) |
| 3 | 250.06 | 632.29 | 910.94 | [JSON](t5_run03.json) | [CSV](t5_run03.csv) |

### Analysis

All three runs achieved complete final-caption delivery without observed duplicate or stale updates, but network impairment reduced freshness.

Comparing with T2, we can see that median caption age values are much higher, reflecting the impact of the network impairment, where caption events will take much longer times to reach the clients. The configured delay increases the baseline time for captions to reach clients, while jitter introduces variation in delivery time. The ratios are also no longer 100%, as many captions arrive past the threshold.

WebSocket uses TCP, so packet loss can trigger retransmissions and delay subsequent data through head-of-line blocking. 

The effects are consistent with the observed latency tail: median P50 Caption Age was 252.55 ms, compared with the substantially higher P95 of 632.29 ms and P99 of 911.35 ms. This means the slower portion of caption deliveries experienced substantially greater delay than typical deliveries.

Normal Update Coverage was below 100% (92.45% to 99.26% across runs) while final completeness stayed at 100%. A retransmission stall stops a client's socket from draining, so its outbox briefly backs up and queued provisionals are replaced by newer revisions or the final. The 1 to 4 recovered history items per run are not reconnects: a few clients finished their handshake under the added delay after the first segment was finalized, so their initial HISTORY was not empty.

## T3 Slow readers

### Purpose and setup

Check that slow readers do not make normal readers stale, and compare the naive broadcaster with the per-client outbox server under the same workload.

Both servers ran on a native Ubuntu 24.04.4 host (i7-13620H, 16 threads, 15 GiB RAM), Python 3.12.3 and websockets 16.1.1, over local loopback with no network impairment. "Before" is the naive broadcaster at commit `1532e6a` on `main`; "after" is `develop` at `54b733a` (the same server code as the `member-4` branch). Each run used 100 clients, 10 of them slow readers sleeping 500 ms after every message, a requested duration of 60 seconds and three independent runs. The freshness threshold was 500 ms.

### Command

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 \
  --slow-percent 10 --slow-ms 500 --output-stem t3
```

The "before" runs used the same command with `--output-stem t3before` in a checkout of `1532e6a`.

### Results

| Metric (median of 3 runs) | Before (naive) | After (outbox) |
|---|---:|---:|
| P50 Caption Age | 6.66 ms | 7.12 ms |
| P95 Caption Age | 2254.08 ms | 2253.62 ms |
| P99 Caption Age | 24017.88 ms | 24020.49 ms |
| Fresh Caption Ratio at 500 ms | 94.65% | 94.65% |
| Fresh Final Caption Ratio at 500 ms | 90.00% | 90.00% |
| Final Caption Completeness | 95.13% | 95.13% |
| Normal-client P95 | 9.82 ms | 11.02 ms |
| Slow-client P50 / P95 | 14713 / 28076 ms | 14720 / 28089 ms |

Every run recorded 100 successful connections, zero connection errors, zero duplicates and zero stale updates.

| Run | Before P95 ms | Before summary | After P95 ms | After summary |
|---|---:|---|---:|---|
| 1 | 2252.19 | [JSON](t3before_run01.json) / [CSV](t3before_run01.csv) | 2253.68 | [JSON](t3_run01.json) / [CSV](t3_run01.csv) |
| 2 | 2254.25 | [JSON](t3before_run02.json) / [CSV](t3before_run02.csv) | 2253.62 | [JSON](t3_run02.json) / [CSV](t3_run02.csv) |
| 3 | 2254.08 | [JSON](t3before_run03.json) / [CSV](t3before_run03.csv) | 2250.23 | [JSON](t3_run03.json) / [CSV](t3_run03.csv) |

### Analysis

Normal readers stayed fresh with both servers (P95 about 10 to 11 ms), and the two servers produced effectively the same numbers. The outbox server logged zero coalesced messages and zero overflow disconnects in T3 (all 300 client records across the three runs show `coalesced=0`), so it never detected backpressure.

Server memory stayed bounded. During one additional T3 run, `monitor_server.py` sampled the server's resident memory every second for 70 seconds ([t3_memory.csv](t3_memory.csv)): 26.3 MB at startup, 31.6 MB once all clients connected, and 32.5 MB at the end, with no growth trend across the run.

The reason is buffering outside the server. A caption is about 180 bytes of JSON and about 25 bytes on the wire after permessage-deflate. Over 60 seconds the source sends 228 messages per client, and the slow reader's kernel receive buffer (87 KB initial on this host) absorbs the whole backlog. The server's writes therefore always succeed immediately. The slow reader's caption age grows linearly to about 28 seconds because it reads stale messages out of its own buffer, and its final completeness falls short only because the run ends before it has read everything.

A longer probe (one run, 10% of readers at 2000 ms per message for 120 seconds) still produced only 26 coalesced messages per slow client and no overflow. The load client never reports what it has consumed, so no server can detect a slow reader of this kind until the client's receive buffer fills.

## T4 Reconnect

### Purpose and setup

Verify incremental recovery after temporary disconnects with no duplicate final captions. Each run used 100 clients, of which 20 closed their connection at 15 seconds, stayed offline for 5 seconds and reconnected with their latest finalized position; a requested duration of 60 seconds and three independent runs on `develop` at `54b733a`. The freshness threshold was 500 ms.

### Command

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 \
  --disconnect-percent 20 --disconnect-at 15 --disconnect-seconds 5 \
  --output-stem t4
```

### Results

| Metric | Median across 3 runs |
|---|---:|
| P50 Caption Age | 6.30 ms |
| P95 Caption Age | 10.19 ms |
| P99 Caption Age | 12.87 ms |
| Fresh Caption Ratio at 500 ms | 100% |
| Fresh Final Caption Ratio at 500 ms | 98.42% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 98.25% |
| Recovery (HISTORY) P50 / P95 | 2.46 / 3.68 ms |

Every run recorded 120 successful connections (100 initial plus 20 reconnects), zero connection errors, zero duplicates, zero stale updates and zero invalid non-final history items.

| Run | P95 ms | Recovered finals | Recovery P95 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 9.81 | 140 | 4.20 | [JSON](t4_run01.json) | [CSV](t4_run01.csv) |
| 2 | 10.19 | 140 | 2.16 | [JSON](t4_run02.json) | [CSV](t4_run02.csv) |
| 3 | 10.23 | 139 | 3.68 | [JSON](t4_run03.json) | [CSV](t4_run03.csv) |

### Analysis

Every reconnecting client recovered all finals it missed: final completeness was 100% with zero duplicates, so HISTORY returned exactly the finals after each client's reported finalized position. The 20 clients recovered about 7 finals each, matching the source's rate of one final per 0.75 seconds over the 5-second gap.

Fresh Final Caption Ratio is 98.42% rather than 100% because recovered finals are, by definition, older than 500 ms when they arrive. Normal Update Coverage is 98.25% because provisional revisions sent while a client was offline are not recovered; only finals are durable state.

Recovery took 2 to 4 ms at P95 on loopback. The server queues HISTORY and registers the client in one step, so live updates that arrive during recovery are queued behind HISTORY rather than missed.

## Before/after comparison: 2 Mbit/s bandwidth overload

### Purpose and setup

Required stress-test comparison. Constrained bandwidth makes the server's own socket buffers back up, which is when the outbox coalesces. The comparison uses the same naive "before" server and host as T3; "after" is the `member-4` branch, whose server code is identical to `develop` at `54b733a`.

The supplied `bandwidth_2mbit.sh` profile applied a 2 Mbit/s token-bucket limit (400 ms queueing latency) to lo. Each run used 600 clients, a requested duration of 40 seconds and three independent runs. Each client costs roughly 5 kbit/s once TCP/IP headers and ACKs are counted, so 600 clients offer about 1.5 times the link capacity.

### Command

```bash
sudo ./network_profiles/bandwidth_2mbit.sh lo
python run_demo.py --clients 600 --duration 40 --runs 3 --output-stem bw600_after
sudo ./network_profiles/reset.sh lo
```

The "before" runs used `--output-stem bw600_before` in a checkout of `1532e6a`, under the same profile.

### Results

| Metric (median of 3 runs) | Before (naive) | After (outbox) |
|---|---:|---:|
| P50 Caption Age | 1228.30 ms | 1170.41 ms |
| P95 Caption Age | 4583.83 ms | 2851.54 ms |
| P99 Caption Age | 9842.87 ms | 6182.79 ms |
| Fresh Caption Ratio at 500 ms | 0.69% | 0.52% |
| Fresh Final Caption Ratio at 500 ms | 0.64% | 0.00% |
| Final Caption Completeness | 97.85% | 99.62% |
| Normal Update Coverage | 92.74% | 74.56% |
| Mid-stream reconnects | 27 | 20 |

All runs recorded zero duplicates and zero stale updates, and every client connected. The after server coalesced 49,618 provisional revisions across its three runs and disconnected no client for overflow.

| Run | Before P95 ms | Before completeness | Before summary | After P95 ms | After completeness | After summary |
|---|---:|---:|---|---:|---:|---|
| 1 | 4666 | 97.85% | [JSON](bw600_before_run01.json) / [CSV](bw600_before_run01.csv) | 3795 | 99.62% | [JSON](bw600_after_run01.json) / [CSV](bw600_after_run01.csv) |
| 2 | 4584 | 97.81% | [JSON](bw600_before_run02.json) / [CSV](bw600_before_run02.csv) | 2707 | 100.00% | [JSON](bw600_after_run02.json) / [CSV](bw600_after_run02.csv) |
| 3 | 4173 | 98.73% | [JSON](bw600_before_run03.json) / [CSV](bw600_before_run03.csv) | 2852 | 99.16% | [JSON](bw600_after_run03.json) / [CSV](bw600_after_run03.csv) |

### Analysis

Coalescing cut P95 caption age by 38% (4584 to 2852 ms) and P99 by 37% (9843 to 6183 ms), and raised final completeness from 97.85% to 99.62%. Every after run beat every before run on P95 and on completeness. When a client's outbox backs up, queued provisionals of the current segment are replaced by newer revisions or by the final, so the bandwidth they would have used goes to finals instead.

The cost is Normal Update Coverage, which fell from 92.74% to 74.56%: clients behind a congested link no longer see every intermediate revision. The assignment permits this, because finals and the latest revision of the active segment are always kept.

Coalescing does not make an overloaded link fresh. Median caption age stayed around 1.2 seconds and the fresh ratios stayed near zero for both servers, because the token bucket's own 400 ms queue stays full and 600 clients' kernel send buffers together hold more than the link can drain quickly. Reducing that would need a server-wide limit on bytes in flight rather than per-client limits.

An earlier attempt with 1000 clients is not reported as a comparison: about 1,100 to 1,300 WebSocket handshakes per run timed out on both servers, and about 30% of clients never received a caption, so that run measured connection setup rather than overload handling.

## Startup observation

The runner's plain TCP port-readiness probe can produce an opening-handshake
error because it closes without sending a WebSocket HTTP request. This is
separate from the simulated clients, which recorded zero connection errors in
all nine runs.

## Remaining report work

- Incorporate the final results and analysis into the required 4-5-page
  `report.pdf`.
- Rerun the affected experiments if `solution_server.py` or `client_outbox.py`
  changes before submission.
