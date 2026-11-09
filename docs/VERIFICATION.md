# Attune 0.3.1 — verification boundaries

## Fresh canonical result

**154 passed**, Python 3.11.15, recorded Linux/WSL Hermes host. The focused schedule/control module separately passed **25 tests**. These overlap; do not add their counts.

```bash
PYTHONDONTWRITEBYTECODE=1 /absolute/hermes-python -m pytest -o addopts= -q --tb=short --junitxml=artifacts/verification/submission-v031/pytest.xml
```

The suite executes real Bubblewrap children. Coverage includes learning/replay/correction, exact project selection, approvals/grants, caps/concurrency, source preservation, network/home/credential/write isolation, zero/skipped/failed tests, timeouts, revocation/expiry, retained hashes, stale/rejected results, malformed completion reports and bounded verbose logs.

Schedule regressions verify explicit native request fields, route/timezone validation, unchanged state, no private scheduler imports and preserved legacy hints. Schedule/unschedule never inspect or mutate host jobs. Owner-approved native Hermes cron owns enrollment/removal; prepared, saved, fired and delivered are separate states.

## Exact final artifacts

Machine receipts live beside the clean submission export under `artifacts/verification/submission-v031/`. Require a passed final `release.json` whose hashes match the delivered artifacts. An absent/failed receipt is not an implied pass. The receipt stays outside its enclosing ZIP to avoid circular hashes.

The ad-hoc release harness is not another independent suite: it invokes the canonical suite on isolated installed wheel, extracted sdist and extracted handoff ZIP. Counts must match source with zero errors/failures/skips. It also checks installed module provenance, console entry point, exact source/assets/docs/tests, archive CRC/member manifests, two reproducible wheel builds, actual previous-wheel state continuity and two executed fixture previews. Verification scripts that inspect host internals remain local development tooling, not part of the published plugin tree.

Native-loader receipts must prove eleven tools, one command, one hook, bundled skill, entry-point metadata, profile-scoped state and restricted deferred catalog. They verify a non-mutating cron handoff, not cron creation or execution. Supported host identity is recorded; one host is not cross-version certification.

## Official admission

Run the documented `hermes plugins validate /absolute/clean/plugin --install-deps --json` against the frozen clean export with a disposable home and isolated host checkout. Check both JSON and the entire bootstrap log: a dependency-preparation failure followed by `ok=true` is not full admission success. Require zero failures, review every warning, and preserve command, exit status, host identity and exact pinned plugin tree.

The previous attempt against a mutable development tree reported `Dependency inputs changed while preparing publication; retry.` and scanned stale build/dev-verifier imports. It is retained as failed/incomplete evidence, not upgraded to success. 0.3.1 removes scheduler-private imports and excludes developer-only host probes/build outputs from the clean publishable tree. Final admission status is in the current admission receipt, not inferred from historical native loading.

## Executable demonstration

Installed/extracted fixture demos script owner answers, proposals, ratings and clock; execution is real. An exact-approved preview passes **4 tests**, computes **3 orders / 24.75 revenue**; a distinct scoped-grant preview passes **5 tests**, computes **Tea 17.50 / Coffee 7.25**, retaining the first feature. Original files remain unchanged. Preapproval blocks execution; rejection revokes preview permission. Retained mappings bind original paths to retained bytes.

Fixture revenue is not earned money. Generated tests are advisory, not independent semantic/security certification. An edited demo must say scripted/offline; it is not live AI generation or elapsed-day operation.

## Live/public gates remain separate

No live installation/reload, model call, chat send, recurring enrollment, merge, deployment, public repository, catalog PR or competition submission occurs in local verification. Earlier manual provider outcome remains unresolved; preserve the claim/evidence before retry. Actual model-generated usefulness/delivery requires bounded owner approval and its own receipt. Identity, eligibility, deadline and publication need owner/organizer confirmation. See `SUBMISSION.md`, `OPERATIONS.md` and the final external receipt.
