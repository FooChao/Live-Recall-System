# AI / Coding-Assistant Usage

## Tools used

### OpenAI Codex (desktop application)

Used by Foo Chao to:

- Understand the assignment requirements and starter code, and discuss the
  four-member task split and integration order.
- Explain WebSocket ordering, JavaScript Map storage, revision replacement,
  and the distinction between revision state and recovery history.
- Generate and refine browser caption replacement and server revision checks,
  including comments and TODOs for Member 2's history/recall integration.
- Generate focused JavaScript and Python unit tests for revision behavior.
- Fix the live-caption area growing as captions arrived and pushing the recall
  buttons down. Codex added a fixed-height, scrollable caption box, capped at
  45% of the viewport height, so new captions scroll inside it.
- Troubleshoot Ubuntu VM shared-folder access and Python virtual-environment
  setup, and update the README with browser startup instructions.
- Help write the experiment results after Foo Chao ran the experiments and
  checked the results personally. After judging the results to be correct,
  Foo Chao asked Codex to double-check the saved JSON summaries against the CSV
  logs, verify the reported metrics and medians, and help document the findings.

Used by Member 3 to:

- Implement automatic browser reconnect, finalized resume tracking independent
  of caption expiry, and ordered HISTORY merging through shared revision checks.
- Update the simulated browser test environment with storage, a fixed clock,
  and controlled timers, and add regression tests for recovery and local recall.
- Verify the real browser script against a local Python server over WebSockets
  using a simulated DOM, and document recovery behavior and demo steps.

### ChatGPT

Used by Jun Kiat to:

 - Understand the base code.
 - Generate parts of code for client side and server side implemention of history
 - Generate regression tests for history_store

### Claude Code

Used by Daniel Zhou to:

- Implement the per-client outbox, coalescing and overflow policy, the ordered
  HISTORY/live handoff, and the outbox and backpressure tests.
- Run and analyse T3 and the 2 Mbit/s before/after comparison, and diagnose why
  the outbox never coalesced in T3.


## One useful suggestion

Daniel Zhou: after the outbox server matched the naive server exactly on T3,
Claude Code suggested checking the server's per-client `coalesced=` log counts,
which were all zero. Inspecting the sockets with `ss` and `sysctl tcp_rmem`
showed that each slow reader's kernel receive buffer (87 KB) absorbed the whole
60-second stream of roughly 25-byte compressed frames, so no server could see
backpressure. This led to the 2 Mbit/s bandwidth comparison, where the server's
own buffers fill. We verified it there: the outbox coalesced 49,618 provisionals
over three runs and every after run beat every before run on P95 and final
completeness.

## One suggestion that was wrong, inefficient, or required modification

Daniel Zhou: the first generated backpressure integration test filled the
stalled client's socket buffers with captions of `TEXT = "x" * 2000`. The test
failed with zero coalesced messages. A probe of the socket queues showed only
about 35 bytes per message on the wire: websockets negotiates permessage-deflate
by default, and repeated text compresses to almost nothing, so the buffers never
filled. The correction was to open the test connections with
`compression=None`. The test then passed, and it fails when coalescing is
removed.

A second suggestion, running the bandwidth comparison with 1000 clients, was
also wrong: about 1,100 to 1,300 WebSocket handshakes per run timed out on both
servers, so the run measured connection setup rather than overload handling.
We reran with 600 clients.

## Responsibility statement

We understand that the team remains responsible for the submitted code, experimental results, and claims, and that every member may be asked to explain or modify relevant code during the viva.
