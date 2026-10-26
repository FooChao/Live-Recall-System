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

## Startup observation

The runner's plain TCP port-readiness probe can produce an opening-handshake
error because it closes without sending a WebSocket HTTP request. This is
separate from the simulated clients, which recorded zero connection errors in
all six runs.

## Remaining report work

- Record T3 slow-reader results, T4 reconnect results and T5 network impairment.
- Complete a stress-test before/after optimization comparison using the same
  workload. T1 versus T2 does not satisfy this requirement.
- Record the exact Ubuntu release, Python/websockets versions, VM CPU/RAM and
  tested code commit with the final experiments; these details were not captured
  in the saved summaries.
- Repeat T1/T2 after integration and incorporate the final results and analysis
  into the required 4-5-page `report.pdf`.
