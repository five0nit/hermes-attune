# Attune — competition submission draft (0.3.1)

**Status:** verified local release candidate; not submitted, not catalog-approved, not live-activated. Working name and public identity need owner confirmation.

## One-line pitch

**Hermes learns what matters to you—and starts building things you didn't have to ask for.**

## Problem

An agent can remember facts yet keep asking the same questions, repeat finished work, miss changed priorities or treat silence as permission. More autonomy without better feedback makes that worse.

## What Attune does

Attune starts with adaptive daily questions: which project matters, what keeps slowing you down, what success looks like and how much initiative you prefer. Explicit answers become evidence for concrete code improvements to owner-selected files. Hermes proposes changed code/tests; exact idea approval or an existing scoped preview grant permits an actual offline Python preview. The owner gets the preview, diff, unittest output and hashes, then rates it. Changed priorities and negative feedback shape the next question and invalidate stale work.

Daily questions continue after onboarding. Recent ideas/results and rejected changes remain visible, unchanged code is deduplicated, and negative feedback revokes preview authority. A preference for surprises is not execution consent. Drafting remains an optional capability; it is not the whole product. The first build increment is deliberately limited to selected Python standard-library files and unittest checks, including small new tools inside an owner-selected starter project—not arbitrary frameworks, dependency installation, source merges or deployment.

## Judge demo — edit to under 90 seconds

Use `python3 examples/project_demo.py --output /absolute/path/to/a/fresh-directory` with Python 3.11+, Linux Bubblewrap and `prlimit`. Owner answers, proposal code, ratings and clock are explicitly scripted; file execution and checks are real. This is not live model generation or elapsed-day evidence.

1. Owner selects a tiny sales-report project and exact files. Daily answers identify repetitive reporting and time saved.
2. Show the concrete CSV-summary idea with goal/answer evidence and changed files. Before approval: `needs_approval`.
3. Approve that exact idea. Show the separately executed preview: 4 actual tests, 3 orders, revenue `24.75`; original project hashes unchanged.
4. Advance the controlled date and answer the daily project review. Explicitly grant bounded surprise previews; preferences alone cannot do this.
5. Show a genuinely new improvement retaining the first feature: per-product totals Tea `17.50`, Coffee `7.25`, with 5 tests. Display the preview/diff rather than claiming a source merge.
6. Rate `revise`: preview mode returns to suggest, duplicate changes remain suppressed and the next check-in asks a correction. No provider call, live schedule, source merge, deployment or public post occurs.

Read `docs/VERIFICATION.md` and bundle receipts for exact execution scope. A hash proves bytes, not factual correctness or a useful result.

## Runtime disclosures

MIT; standalone native plugin; Python 3.11+; no third-party Python runtime dependencies. Eleven tools, one owner command, one context hook and bundled skill. Requires Hermes >=0.22.5; tested only on the recorded host. Preview execution additionally needs Linux `bwrap`, `prlimit` and `/usr/bin/python3`; no ambient-shell fallback. Explicit state and selected source are plaintext and may reach the configured model. Runtime launches only the fixed offline preview verifier after permission checks, not arbitrary shell commands. Bubblewrap shares the host kernel; generated test success is not independent correctness or security certification. Optional scheduling returns an explicit native cron handoff only. Hermes native cron, after owner approval, owns enrollment, duplicate inspection, readback and removal. No private scheduler imports or provider manipulation. Local developer-only host probes and generated build outputs are excluded from the clean publishable tree. No direct HTTP, stored credentials, telemetry, self-updater or automatic raw-chat ingestion. Disposable verification performs no provider/chat calls; actual live model turns use the user's configured provider and remain unverified here.

## Checked organizer requirements and deadline conflict

The indexed official announcement requires a catalog PR, an X demo tagging `@NousResearch`, and both links in the entry form. It says keep the demo under 90 seconds and judges usefulness, reliability, polish and creativity. The post extractor returned no body, so those details are attributed to the retrieved search index of the official post, not a successful direct post read.[2]

The actual public form requires Plugin Title, Plugin Description, Email Address, Discord Username, X Demo Post Link and GitHub Link to your Hermes Plugin Pull Request. The form was read only; nothing submitted.[3]

Deadline sources conflict: the indexed announcement says November 11 at 5PM EST (November 12, 09:00 Australia/Melbourne); the form's thank-you text says November 11 at 1pm PST (November 12, 08:00 Melbourne). Its operational `formCloseTimestampLimit` is later still: `1794517200` (November 13, 08:00 Melbourne). Do not treat technical form availability as an extension. Plan before the earliest stated time, **November 12, 2026 at 08:00 Melbourne**, and confirm with the organizer. Time conversions were computed with Python `zoneinfo`; public form evidence is retained in `competition-form-v020.json`.[2][3]

Catalog submission separately requires a public cloneable repository, a loadable pinned tree, a full 40-character SHA and local validation including `--install-deps`, followed by maintainer review. Private-import warnings need explicit attention rather than treating validator `ok` as catalog acceptance.[1]

## Actual remaining submission gates

- [ ] Owner approves final name, public authorship/repository and publication.
- [ ] Resolve the conflicting stated deadlines with the organizer; confirm personal/geographic eligibility and publication identity. Primary indexed rules and actual form fields are recorded above.
- [ ] Publish a clean repository and pin a full 40-character commit SHA; local source hashes do not substitute for it.
- [x] Remove scheduler private imports; use explicit native cron handoff, no core edits/provider workaround. Freeze a clean export without development-only host probes.
- [ ] Require a fresh passed `hermes plugins validate /path/to/plugin --install-deps --json` receipt against the clean pinned tree, including successful bootstrap and reviewed warnings. Historical mutable-tree bootstrap failure is retained; inspect current external admission receipt before claiming this gate.
- [ ] Resolve the approved manual test's provider/delivery gap: no successful result is established and the preserved unverified claim must not be discarded or blindly replayed. Routine is off; no schedule was enrolled. Separate approval is still needed for any recurring profile/schedule/timezone/destination, and scheduled-agent proof remains untested.
- [ ] Record/publish the accurately labeled demo; review factual/usefulness claims.
- [ ] Open the catalog PR and submit the competition application only after separate publication approval.

Sources checked 2026-11-07; catalog rules are not competition eligibility/deadline evidence. No repository URL, SHA, screenshot, live output or acceptance is invented here.

## Sources

[1] https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission
[2] https://x.com/NousResearch/status/2118094256438936062
[3] https://form.typeform.com/to/FwJLvOln
