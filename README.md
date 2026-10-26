# Team XX - LiveRecall

## Team members

- Name / student ID / responsibility

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

### Additional experiments

Add each experiment's configuration, command and output files under its own
heading. T3-T5 and the required stress-test optimization comparison remain to be
completed; commands are in [PUBLIC_TESTS.md](PUBLIC_TESTS.md).

Using the same output stem again overwrites the corresponding result files.

## Mandatory deterministic application demo

Exact commands/steps for `caption_source.py`, browser clients, revision replacement, recall, late join, and reconnect/recovery.

## Design notes

Briefly describe:

- revision/deduplication state;
- bounded server history;
- reconnect/late-join recovery;
- per-client buffering/backpressure policy;
- overload behavior and trade-offs.

## Optional ASR bonus

Only if attempted. Keep these dependencies separate from the mandatory server path.
