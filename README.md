# Team 13 - LiveRecall

## Team members

- Name / student ID / responsibility
- Foo Chao / A0272024R / Live captions, revision replacement, concurrent-client
  verification, and T1/T2 experiments.
- Tang Jun Kiat / A0269580R / What did I miss?, Bounded history, T5 experiment

## Ubuntu setup

Exact commands from a fresh Ubuntu environment.

## Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Required server

```bash
python solution_server.py --port 8765
```

## Browser client

Activate the virtual environment, then run:

```bash
python3 -m http.server 8000 --directory client
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in the Ubuntu browser.

## Optional regression tests

These tests are not assignment requirements. We use them to catch regressions
when changing our code. They do not replace the required public tests T1-T5.

### Python

Activate the virtual environment, then run from the project folder:

```bash
python -m unittest discover -s tests -v
```

Finds Python tests in `tests/` and shows each result. Checks server revision
acceptance, stale/duplicate rejection, final-caption protection, bounded history,
and per-client outbox coalescing and overflow. `test_server_backpressure.py`
starts an in-process server on a free local port with one stalled and one normal
client; the other tests need no server. Successful runs end with `OK`.

### JavaScript

Requires Node.js. Run separately from the Python tests, from the project folder:

```bash
node --test tests/client_revision.test.cjs
```

Checks browser revision replacement, stale/duplicate rejection, and final-caption
protection using simulated browser objects. No running server or browser is
needed. Node.js is only needed for these optional tests, not to run the application.

## Public deterministic tests

Run inside Ubuntu, from the project folder, after activating the virtual
environment. Stop any manually running server and caption source first; the
runner starts its own and restarts the server for each independent run.

### T1 Basic correctness

20 clients, 20 seconds per run, 3 independent runs. Uses local loopback with no
deliberate network impairment, slow readers, forced disconnects or late clients.
Freshness threshold: 500 ms.

```bash
python run_demo.py --clients 20 --duration 20 --runs 3 --output-stem t1
```

Outputs: `t1_run01.csv` / `t1_run01.json` through `t1_run03.csv` /
`t1_run03.json`, saved beside `run_demo.py`. The runner prints medians across the
three runs. Results and analysis: [T1 Basic correctness](EXPERIMENT_RESULTS.md#t1-basic-correctness).

### T2 Public scale

100 clients, 40 seconds per run, 3 independent runs. Uses local loopback with no
deliberate network impairment, slow readers, forced disconnects or late clients.
Freshness threshold: 500 ms.

```bash
python run_demo.py --clients 100 --duration 40 --runs 3 --output-stem t2
```

Outputs: `t2_run01.csv` / `t2_run01.json` through `t2_run03.csv` /
`t2_run03.json`, saved beside `run_demo.py`. The runner prints medians across the
three runs. Results and analysis: [T2 Public scale](EXPERIMENT_RESULTS.md#t2-public-scale).

### T5 Network Impairment

100 clients, 40 seconds per run, 3 independent runs. Uses local loopback with tc/netem applying 120 ms delay, 30 ms jitter and 3% packet loss. No deliberate slow readers, forced disconnects or late clients. Freshness threshold: 500 ms.

```bash
sudo ./network_profiles/delay_loss.sh lo
python run_demo.py --clients 100 --duration 40 --runs 3 --output-stem t5
```

Reset the network afterwards:

```bash
sudo ./network_profiles/reset.sh lo
```

Outputs: `t5_run01.csv` / `t5_run01.json` through `t5_run03.csv` /
`t5_run03.json`, saved beside `run_demo.py`. The runner prints medians across the
three runs. Results and analysis: [T5 Network Impairment](EXPERIMENT_RESULTS.md#t5-network-impairment).

### Additional experiments

Add each experiment's configuration, command and output files under its own
heading. T4 remains to be completed; commands are in [PUBLIC_TESTS.md](PUBLIC_TESTS.md).

### T3 Slow readers

100 clients, 60 seconds per run, 3 independent runs, 10% slow readers sleeping 500 ms after each message. Local loopback, no impairment. Freshness threshold: 500 ms.

```bash
python run_demo.py --clients 100 --duration 60 --runs 3 --slow-percent 10 --slow-ms 500 --output-stem t3
```

Outputs: `t3_run01` to `t3_run03` (`.csv` / `.json`). The naive-broadcaster comparison runs are `t3before_run01` to `t3before_run03`, produced at commit `1532e6a`. Results and analysis: [T3 Slow readers](EXPERIMENT_RESULTS.md#t3-slow-readers).

### Before/after comparison: 2 Mbit/s bandwidth overload

600 clients, 40 seconds per run, 3 independent runs, under the supplied 2 Mbit/s profile. Run once on this server and once on commit `1532e6a` (naive broadcaster) with stem `bw600_before`.

```bash
sudo ./network_profiles/bandwidth_2mbit.sh lo
python run_demo.py --clients 600 --duration 40 --runs 3 --output-stem bw600_after
sudo ./network_profiles/reset.sh lo
```

Outputs: `bw600_after_run01` to `bw600_after_run03` and `bw600_before_run01` to `bw600_before_run03` (`.csv` / `.json`). Results and analysis: [Before/after comparison](EXPERIMENT_RESULTS.md#beforeafter-comparison-2-mbits-bandwidth-overload).

Using the same output stem again overwrites the corresponding result files.

## Mandatory deterministic application demo

Exact commands/steps for `caption_source.py`, browser clients, revision replacement, recall, late join, and reconnect/recovery.

## Design notes

Briefly describe:

- revision/deduplication state;

### Bounded Server History
The server keeps recent finalized captions to support reconnect and late-join recovery without retaining the entire lecture. A 70-second retention window provides a buffer beyond the maximum 60-second history request. 

Expired entries are removed when adding captions or querying history. Responses contain recent finals newer than the client’s reported finalized position, ordered oldest first.

- reconnect/late-join recovery;
### Per-client buffering and backpressure

Each client has its own outbox (`client_outbox.py`) drained by one sender task (`send_loop()` in `solution_server.py`). The source handler only appends accepted captions to every outbox and never awaits a client socket, so a slow reader delays its own outbox and nothing else. The sender is the only code that writes to the client, which keeps delivery in order.

On `CLIENT_HELLO` the server reads its history, queues the HISTORY message and registers the client with no `await` in between. Every final is therefore either in that HISTORY snapshot or queued live after it: none is missed and none is sent twice, and live updates cannot overtake HISTORY.

### Overload behavior and trade-offs

Coalescing only happens while a message is still waiting in an outbox, which means the client is not keeping up. A client that keeps up receives every revision. When a newer update of a segment is queued, any queued provisional of that segment is dropped, because the server only accepts newer revisions, so the queued one is already obsolete. Finals are never dropped. As a result the outbox holds at most one provisional plus finals.

The outbox is bounded at 32 messages, and its oldest message may wait at most 15 seconds. A client that exceeds either bound is closed with code 1013. Queuing finals forever would let memory and caption age grow without limit. Disconnecting is safe because the client reconnects with its last finalized position, and 15 seconds is well inside the 60-second HISTORY window, so it recovers every final it missed. The cost is a short gap in live updates for that one client.

Bytes that have already left the outbox can no longer be coalesced. The server therefore limits each connection's transport buffer to 4 KiB (`write_limit`) and its kernel send buffer to 16 KiB (`SO_SNDBUF`), so a backlog stays in the outbox instead. The client's own kernel receive buffer is outside the server's control: on public T3 it holds the entire 60-second stream for a 500 ms reader, so the server never sees backpressure there.

## Optional ASR bonus

Only if attempted. Keep these dependencies separate from the mandatory server path.
