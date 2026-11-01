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

Used by somneel to:

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


## One useful suggestion

Describe one suggestion that materially helped the project and how you verified it.

## One suggestion that was wrong, inefficient, or required modification

Include a short generated suggestion/code fragment or precise description, explain the problem, and describe your correction.

## Responsibility statement

We understand that the team remains responsible for the submitted code, experimental results, and claims, and that every member may be asked to explain or modify relevant code during the viva.
