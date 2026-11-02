# Team 13 - LiveRecall

## Team members

- Name / student ID / responsibility
- Foo Chao / A0272024R / Live captions, revision replacement, concurrent-client
  verification, and T1/T2 experiments.
- Tang Jun Kiat / A0269580R / What did I miss?, Bounded history, T5 experiment
- Somneel Saha / A0276045A / Browser reconnect, finalized resume tracking,
  history recovery, and recovery regression tests.

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
acceptance, stale/duplicate rejection, and final-caption protection without
starting a server or connecting clients. Successful runs end with `OK`.

### JavaScript

Requires Node.js. Run separately from the Python tests, from the project folder:

```bash
node --test tests/client_revision.test.cjs
```

Checks revision replacement, final-caption protection, automatic reconnect,
finalized resume after local expiry, ordered history merging, and local recall.
The tests use simulated browser objects, a fixed clock, and controlled timers;
no running server or browser is needed. Node.js is only needed for these optional
tests, not to run the application.

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
heading. T3-T4 and the required stress-test optimization comparison remain to be
completed; commands are in [PUBLIC_TESTS.md](PUBLIC_TESTS.md).

Using the same output stem again overwrites the corresponding result files.

## Mandatory deterministic application demo

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for commands and browser steps covering
revision replacement, recall, late join, and automatic reconnect/recovery.

## Design notes

Briefly describe:

- revision/deduplication state;

### Bounded Server History
The server keeps recent finalized captions to support reconnect and late-join recovery without retaining the entire lecture. A 70-second retention window provides a buffer beyond the maximum 60-second history request. 

Expired entries are removed when adding captions or querying history. Responses contain recent finals newer than the client’s reported finalized position, ordered oldest first.

### Browser reconnect and late join

The browser retries closed WebSockets after one second, including failed
connection attempts. Each hello requests 60 seconds of available finalized
history and reports the latest accepted finalized segment/revision. Provisional
updates never advance this position. The position lives separately from the
70-second caption Map, so local expiry cannot reset it. Reloading the page starts
with an empty Map and a fresh `(0, 0)` position; reconnecting within the page keeps
both local state and the client ID.

Live updates and HISTORY items share revision acceptance: duplicates and stale
revisions are ignored and a final cannot be overwritten. Recovered rows are
inserted in segment order, even when newer live rows already exist. The merged
Map supplies the existing 15/30/60-second local recall views; recall clicks do not
send history requests. Only finals available within the server's requested
60-second window can be recovered after a disconnect.

Integration dependency for Member 4: `handle_client()` currently sends HISTORY
before registering for live broadcasts. An update during that await can be
missed. The server still needs one ordered HISTORY/live handoff and one sender
per client; browser merging alone cannot close this gap.

- per-client buffering/backpressure policy;
- overload behavior and trade-offs.

## Optional ASR bonus

Only if attempted. Keep these dependencies separate from the mandatory server path.
