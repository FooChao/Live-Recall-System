# LiveRecall experiment results

Baseline results for the public-experiments section of the final report.
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

The saved summaries match re-analysis of the corresponding CSV logs using the
supplied `analyse_results.py`. Preserve the logs before rerunning with the same
output stems, since the runner overwrites them.

## T1 Basic correctness

### Purpose and setup

Verify revision/final delivery, duplicate/stale counts and normal update
coverage with 20 clients on the normal local-network profile.

The server and simulated clients ran inside the same Ubuntu VirtualBox VM on a
Windows host, using `ws://127.0.0.1:8765`. No deliberate network impairment was
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
| P50 Caption Age | 3.89 ms |
| P95 Caption Age | 7.42 ms |
| P99 Caption Age | 10.60 ms |
| Fresh Caption Ratio at 500 ms | 100% |
| Fresh Final Caption Ratio at 500 ms | 100% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 100% |

Every run recorded zero duplicates, stale updates, invalid non-final history
items and client connection errors. Each client received all 22 finals:
440 final deliveries and 1,320 accepted live updates across 20 clients per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 3.89 | 7.42 | 11.11 | [JSON](t1_run01.json) | [CSV](t1_run01.csv) |
| 2 | 3.91 | 9.49 | 10.60 | [JSON](t1_run02.json) | [CSV](t1_run02.csv) |
| 3 | 3.48 | 6.97 | 9.70 | [JSON](t1_run03.json) | [CSV](t1_run03.csv) |

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
browser check. Recovery was not exercised by this workload.

## T2 Public scale

### Purpose and setup

Measure normal concurrent delivery, latency, freshness, completeness and update
coverage with 100 clients.

The server and simulated clients ran inside the same Ubuntu VirtualBox VM on a
Windows host, using `ws://127.0.0.1:8765`. No deliberate network impairment was
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
| P50 Caption Age | 11.08 ms |
| P95 Caption Age | 20.76 ms |
| P99 Caption Age | 32.06 ms |
| Fresh Caption Ratio at 500 ms | 100% |
| Fresh Final Caption Ratio at 500 ms | 100% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 100% |

Every run recorded zero duplicates, stale updates, invalid non-final history
items and client connection errors. Each client received all 49 finals:
4,900 final deliveries and 14,700 accepted live updates across 100 clients per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 11.08 | 20.28 | 32.06 | [JSON](t2_run01.json) | [CSV](t2_run01.csv) |
| 2 | 11.40 | 23.90 | 41.38 | [JSON](t2_run02.json) | [CSV](t2_run02.csv) |
| 3 | 10.38 | 20.76 | 26.13 | [JSON](t2_run03.json) | [CSV](t2_run03.csv) |

### Analysis

All 100 clients received every generated revision and final caption within the
freshness threshold. Compared with T1, median P95 Caption Age increased from
7.42 ms to 20.76 ms and median P99 from 10.60 ms to 32.06 ms, while completeness
and update coverage remained 100%.

More clients require more sends per caption. The increased latency is consistent
with that extra work, but the measurements do not isolate it from VM scheduling,
client logging or other overhead. T1 and T2 also differ in duration and segment
count, so their comparison is not a controlled optimization experiment.

These results support normal operation at the tested population of 100 clients.
The broadcast path still waits for all concurrent sends before processing the
next update. T2 does not establish slow-client isolation, bounded per-client
buffering or performance above 100 clients; those require further workloads.

## T5 Network Impairment

### Purpose and setup

Evaluate caption correctness and freshness with 100 clients under network delay, jitter and packet loss.

The server and simulated clients ran inside the same Ubuntu VM using local loopback. The supplied delay_loss.sh profile applied 120 ms delay, 30 ms jitter and 3% packet loss to lo. Each experiment used 100 clients, a requested duration of 40 seconds and three independent runs. The freshness threshold was 500 ms. No slow readers, forced disconnects or late joiners were deliberately configured.

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
| P50 Caption Age | 252.27 ms |
| P95 Caption Age | 662.93 ms |
| P99 Caption Age | 946.89 ms |
| Fresh Caption Ratio at 500 ms | 90.66% |
| Fresh Final Caption Ratio at 500 ms | 91.47% |
| Final Caption Completeness | 100% |
| Normal Update Coverage | 99.97% |

Every run recorded 100 successful client connections, zero connection errors, zero duplicates, zero stale updates and zero invalid non-final history items. Every client received all 49 finalized segments, giving 4,900 final-caption deliveries per run.

| Run | P50 ms | P95 ms | P99 ms | Summary | Raw log |
|---|---:|---:|---:|---|---|
| 1 | 264.84 | 815.85 | 1167.26 | [JSON](t5_run01.json) | [CSV](t5_run01.csv) |
| 2 | 250.45 | 624.44 | 937.88 | [JSON](t5_run02.json) | [CSV](t5_run02.csv) |
| 3 | 252.27 | 662.93 | 946.89 | [JSON](t5_run03.json) | [CSV](t5_run03.csv) |

### Analysis

All three runs achieved complete final-caption delivery without observed duplicate or stale updates, but network impairment reduced freshness.

Comparing with T2, we can see that median caption age values are much higher, reflecting the impact of the network impairment, where caption events will take much longer times to reach the clients. The configured delay increases the baseline time for captions to reach clients, while jitter introduces variation in delivery time. The ratios are also no longer 100%, as many captions arrive past the threshold.

WebSocket uses TCP, so packet loss can trigger retransmissions and delay subsequent data through head-of-line blocking. 

The effects are consistent with the observed latency tail: median P50 Caption Age was 252.27 ms, compared with the substantially higher P95 of 662.93 ms and P99 of 946.89 ms. This means the slower portion of caption deliveries experienced substantially greater delay than typical deliveries.

## T3 Slow readers

### Purpose and setup

Check that slow readers do not make normal readers stale, and compare the naive broadcaster with the per-client outbox server under the same workload.

Both servers ran on a native Ubuntu 24.04.4 host (i7-13620H, 16 threads, 15 GiB RAM), Python 3.12.3 and websockets 16.1.1, over local loopback with no network impairment. "Before" is the naive broadcaster at commit `1532e6a` on `main`; "after" is the `member-4` branch. Each run used 100 clients, 10 of them slow readers sleeping 500 ms after every message, a requested duration of 60 seconds and three independent runs. The freshness threshold was 500 ms.

### Command

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 \
  --slow-percent 10 --slow-ms 500 --output-stem t3
```

The "before" runs used the same command with `--output-stem t3before` in a checkout of `1532e6a`.

### Results

| Metric (median of 3 runs) | Before (naive) | After (outbox) |
|---|---:|---:|
| P50 Caption Age | 6.66 ms | 6.99 ms |
| P95 Caption Age | 2254.08 ms | 2252.36 ms |
| P99 Caption Age | 24017.88 ms | 24017.76 ms |
| Fresh Caption Ratio at 500 ms | 94.65% | 94.65% |
| Fresh Final Caption Ratio at 500 ms | 90.00% | 90.00% |
| Final Caption Completeness | 95.13% | 95.13% |
| Normal-client P95 | 9.82 ms | 9.89 ms |
| Slow-client P50 / P95 | 14713 / 28076 ms | 14711 / 28069 ms |

Every run recorded 100 successful connections, zero connection errors, zero duplicates and zero stale updates.

| Run | Before P95 ms | Before summary | After P95 ms | After summary |
|---|---:|---|---:|---|
| 1 | 2252.19 | [JSON](t3before_run01.json) / [CSV](t3before_run01.csv) | 2251.34 | [JSON](t3_run01.json) / [CSV](t3_run01.csv) |
| 2 | 2254.25 | [JSON](t3before_run02.json) / [CSV](t3before_run02.csv) | 2252.36 | [JSON](t3_run02.json) / [CSV](t3_run02.csv) |
| 3 | 2254.08 | [JSON](t3before_run03.json) / [CSV](t3before_run03.csv) | 2253.96 | [JSON](t3_run03.json) / [CSV](t3_run03.csv) |

### Analysis

Normal readers stayed fresh with both servers (P95 below 10 ms), and the two servers produced the same numbers. The new server logged zero coalesced messages and zero overflow disconnects in T3, so it never detected backpressure.

The reason is buffering outside the server. A caption is about 180 bytes of JSON and about 25 bytes on the wire after permessage-deflate. Over 60 seconds the source sends 228 messages per client, and the slow reader's kernel receive buffer (87 KB initial on this host) absorbs the whole backlog. The server's writes therefore always succeed immediately. The slow reader's caption age grows linearly to about 28 seconds because it reads stale messages out of its own buffer, and its final completeness falls short only because the run ends before it has read everything.

A longer probe (one run, 10% of readers at 2000 ms per message for 120 seconds) still produced only 26 coalesced messages per slow client and no overflow. The load client never reports what it has consumed, so no server can detect a slow reader of this kind until the client's receive buffer fills.

## Before/after comparison: 2 Mbit/s bandwidth overload

### Purpose and setup

Required stress-test comparison. Constrained bandwidth makes the server's own socket buffers back up, which is when the outbox coalesces. The comparison uses the same naive "before" and outbox "after" servers and the same host as T3.

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

- Record T4 reconnect results.
- Record T3 server memory with `monitor_server.py`, which T3 asks for and was not captured.
- Record the exact Ubuntu release, Python/websockets versions, VM CPU/RAM and
  tested code commit with the final experiments; these details were not captured
  in the saved summaries.
- Repeat T1/T2 after integration and incorporate the final results and analysis
  into the required 4-5-page `report.pdf`.
