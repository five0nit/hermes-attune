# Attune — review dispositions

## Current 0.3.1 scope

The source suite freshly passes **154 tests**. Native-loader proof covers eleven tools, one command, one context hook, skill registration and non-enrolling native cron handoffs. Release/admission/distribution evidence is external under `artifacts/verification/submission-v031/`; missing receipts are unfinished gates. No independent final-byte certification, live usefulness, platform delivery, public pin or maintainer acceptance is inferred.

Admission hardening removes private scheduling imports and host-job/provider manipulation. Publication excludes developer-only host-internal verifiers and generated outputs. Scheduling returns explicit owner-approved native cron requests; old creation/removal tests below do not describe 0.3.1. Preview scope remains selected standard-library Python, not just drafting.

## Historical archive — not current behavior or certification

Following counts, limits, scheduler operations, findings and receipt paths refer to the named historical releases. Current operating boundaries: `OPERATIONS.md` and `VERIFICATION.md`.

## 0.3.0 final parent hardening

Baseline expanded candidate: 139 source tests. Recovered independent review output was truncated; only its stale-success concern was recoverable. Do not invent its missing findings or call this an independent final-byte certification.

Parent reproduced 11 failures through public APIs and real Bubblewrap children, then repaired:

- A verified result could remain `verified` after owner rejection, changed source/goal/learning, pause or revoked grant; it could replay as success or receive `useful`. Current state is now qualified as stale/rejected, old checks preserved separately, and retained hashes still checked.
- Worker stdout with a fixed completion marker could claim a pass without completed unittest discovery; malformed JSON could raise and booleans/non-finite numeric fields were not strictly rejected. Per-run framing and bounded typed parsing fail closed. This prevents ordinary stdout confusion, not a malicious Python test inspecting its own runner.
- Large valid stdout hid the runner footer because only the first 64 KB were retained. Bounded tail retention keeps the completion report.

Canonical final source: **154 passed**. Red logs and machine receipts are in `artifacts/verification/proactive-builds-v030/`. Result history is explicitly historical; current readback separates check outcome, project context and present grant. Installed/full-distribution validation is recorded in the final release receipt, not inferred from source tests. Operational constraints and recovery are documented in `OPERATIONS.md`.

## Historical 0.2.1 review disposition

## Current audit-and-improve disposition

Baseline **77 passed** did not cover several real lifecycle/authority gaps. Parent retained failing regressions, applied scoped repairs, and the final canonical source command passes **105 tests** (`pytest-final-v021.txt`). No new independent final-byte certification is claimed; historical reviewers supplied findings, and the parent verified the repairs.

- **Publication after expiry:** claim/day checks at admission went stale during staging I/O. A final expiry/local-day check now runs after fsync/readback and before no-clobber linking. Three controlled-clock cases cover elapsed TTL, UTC midnight and Melbourne midnight; no final artifact or leaked stage may remain on rejection.
- **Stale preference replay:** an older daily format reply could overwrite a newer daily answer. Answers now reject that replay before mutation.
- **Obsolete/retargeted corrections:** acceptance must remove old correction questions; a new rejected run/goal must not inherit an old pending reply identifier. Current latest feedback and goal state determine unresolved corrections; retargeting rotates the check-in ID and stale answers fail closed.
- **Scheduler authority drift:** prompt/toolset equality was insufficient when scripts, monitors, skills, context, provider/model or failure delivery changed. Ownership checks now reject that extra authority; readback verifies cron kind/expression and the bounded job shape.
- **Renamed saved job:** explicit unschedule follows the stored job ID, while preserving jobs whose authority no longer matches Attune's contract.
- **Delivery identifiers:** explicit supported numeric/structured destinations, including threaded routes, are preserved; display names and malformed routes are rejected before job creation. No inferred origin.
- **Missing operational visibility:** status now includes questions, snooze, interval, saved schedule and schedule error. It still explicitly says schedule execution is not live-verified.

`audit-publication-red.txt` and `audit-controls-red.txt` retain pre-fix failures. Source/native/wheel/demo/archive receipts document current checks. Native enrollment checks make no provider/chat calls.

The approved manual live test did not establish successful inference or Telegram delivery. Its retry stopped at the existing-run preservation guard; routine is off, schedule null, and the local test claim has no artifact. Initial provider outcome remains unknown. See `VERIFICATION.md` and `live-manual-gap-v021.json`; this gap is not excused by 105 passing local tests.

## Historical v0.2.0 disposition

The following sections preserve the earlier review scope and counts, not current-byte or live certification.


## Historical v0.1 repairs (not current-byte certification)

The earlier nine regression cases failed red before six lifecycle fixes; v0.1 then passed 58 tests. Repairs covered correctable focus/baseline, current-contract revalidation at resume/delivery, demoted goal invalidation, chronological usefulness reset, same-day correction and local-midnight capacity. Historical receipts/transcripts remain outside the new bundle. The earlier independent 58-test review is not presented as a v0.2 review.

## Reproduced v0.2 product gaps and repairs

- **Repeat drafting/starvation:** unchanged delivered contracts were repeated across controlled days while another active goal received no work. Current selection skips delivered contracts, advances to the next eligible goal and reports `awaiting_update` if none remain. Owner-supplied updates, not model-created novelty, create new work.
- **Weak result distinctness:** duplicate output digests must not become new verified results or inflate learned capacity. Delivery rejects repeated bytes; legacy feedback accounting counts distinct useful digests after the latest negative rating.
- **Invalid bounded context:** maximum-sized input formerly truncated JSON text. Context now bounds values/selection before serialization, preserving complete parseable JSON below the hook's cap.
- **Missing goal lifecycle:** owner `update`, complete/reopen/defer/drop keep identity/history and reject stale in-flight work. No agent tool exposes those owner mutations or usefulness ratings.
- **Daily stale questions:** new/reactivated proposals merge into the same day's check-in; outdated unanswered focus refreshes; yesterday's temporary answer and stale revision replay are rejected. Owner editing temporary focus does not extend its original expiry.
- **Correction leakage:** new output corrections are bound to the goal that received negative feedback, not every unrelated goal. Legacy global settings remain compatible; current answers write scoped keys.
- **First-run/claim races:** schema creation uses an explicit transaction without `executescript`'s implicit commit. Multiple instances initialize/claim without duplicate reservations.
- **Nondeterministic ties:** equal priority/timestamp goals used random UUID ordering. Selection now uses insertion-order rowid; an inverse-UUID regression locks it down.
- **Admission recorder state:** official capability probing has registration APIs but no persistent `ctx.state`. Registration can complete without opening storage; an actual tool call lacking real state returns a structured error. Real registration captures profile-bound data path and never falls back to ambient worker state.

The later bounded review reproduced two additional reliability defects:

- **Repeated rejected correction:** a previous verified but owner-rejected contract was incorrectly considered fulfilled. Selection now excludes rejected outputs from fulfillment; explicit re-enablement and the existing cap remain mandatory, and duplicate bytes still cannot be delivered.
- **Interrupted draft publication:** writing directly to the final path left a partial file that blocked retry. Delivery now stages private bytes, flushes/fsyncs/readbacks, then publishes with an atomic no-clobber hard link and removes its staging file. Existing conflicts are preserved. A process kill can leave an unclaimed temporary file, not a poisoned final path.

Three new regression cases failed before those fixes (`review-final-red.txt`), then the full suite passed **77 tests**. See final source-bound receipts, not historical counts.

## Native / upgrade / admission proof

Source and rebuilt-wheel receipts use the actual host manager, bundled skill and deferred catalog. Owner updates supersede old packets; complete/reopen work; cron create/readback/idempotence/timezone protection/owner-modified-job preservation/removal are exercised only in disposable homes. Upgrade checks preserve runs, feedback and SQLite integrity from the 0.1.0 wheel. Direct official admission and Plugin Doctor pass; optional private scheduler imports remain warnings, not approved API use.

## Latest bounded independent review

A read-only source review found the two reliability defects above. Parent reproduced and repaired them, then requested a bounded read-only re-review of the frozen core and new tests. Its exact hashes/findings and parent disposition belong in `artifacts/verification/review-v020.json`; absence of that receipt must not be construed as re-review completion. Parent suites/native/ad-hoc evidence stand independently. No reviewer closes operator acceptance or public submission gates.

## Remaining limits

No scheduled provider response/platform delivery; no full isolated CLI `--install-deps` catalog run; no public commit/PR/application. No sandbox/security approval, factual correctness or human-usefulness claim. Fixed effect scope remains local drafting only. See `SUBMISSION.md` for owner/maintainer gates.
