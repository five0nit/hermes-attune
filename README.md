# Attune
### Hermes learns what matters to you—and starts building things you didn’t have to ask for.

A native Hermes plugin whose core is **daily questions -> learned goals/project friction -> evidence-linked improvement -> scoped approval or standing preview permission -> real isolated build -> feedback**.

Not another transcript store or agent framework. Continue using Hermes' provider, native tools, command, skill, context hook and optional native cron.

## What changes with use

1. Tell Hermes the outcome and what success means.
2. A short daily check-in learns which selected project matters, what slows you down, what improvement would be useful and how much initiative you prefer. Known answers are reused; once initial learning is complete, a daily project review asks whether the friction has changed. Negative feedback asks a specific correction question.
3. Hermes observes **only owner-selected files**, then proposes an actual code improvement with changed filenames, goal/daily-answer evidence and source hashes. Its project packet includes five recent idea/result states so prior work can be reused, not unknowingly reproposed. Unknown friction must be learned before a proposal can be created.
4. **Suggest first:** approve the exact idea once. **Surprise previews:** explicitly grant a bounded project preview allowance. A preference for surprises is not a permission grant.
5. Get a separate Python preview, diff, real isolated unittest output and retained file hashes. Original project untouched. Rate useful/revise; rejection revokes preview grants/approvals, suppresses the exact change and shapes the next question.

Example: “Weekly reporting keeps wasting time” -> approved sales-tool files -> proposal for an automatic summary -> approve or use an existing preview grant -> separate working function and tests -> review the result before any merge. The executable demonstration below uses scripted fixture inputs, not live AI claims.

## Scope of v0.3.1 — submission candidate

**Implemented:** existing adaptive goals and Markdown drafts, plus explicit project enrollment, project-specific friction/success/initiative/correction questions, continuing daily review, evidence-bound changed-source proposals, one-off approvals, expiring standing preview grants, actual offline Python execution, diff/hash receipts, replay suppression, feedback and revocation. Eleven model tools, one owner `/attune` command, one bounded `pre_llm_call` context hook and bundled workflow skill.

**First build target:** small Python standard-library projects with selected `tests/test_*.py` files. An owner-selected starter project can host a new small tool. No arbitrary project discovery, package installation, browser/UI preview, JavaScript framework build, source merge, deployment, external research, account changes, posting, spending, CCT lease bridge, model training or semantic-success guarantee. Daily live provider wake/chat delivery remains unaccepted. This is a real bounded vertical slice, not the whole expanded product vision.

## Install or verify locally

Requires Python 3.11+, Hermes >=0.22.5, and the existing configured provider for model-generated work. Zero third-party Python runtime dependencies; no separate API key or daemon. **Code previews additionally require Linux, working Bubblewrap, `prlimit` and `/usr/bin/python3`.** Other platforms retain drafting/learning; preview execution fails closed with a concrete prerequisite error. No fallback to an ambient shell.

Tested Hermes host historically `b35d2fc62de629ee1d980554eeacaccac85f0f1a` (0.22.5+1); current verification receipts record the actual run. Other host versions are not certified.

```bash
pytest -o addopts= -q --tb=short
python examples/demo.py
python examples/project_demo.py --output /absolute/empty/demo-directory
hermes plugins validate /absolute/path/to/clean/plugin --install-deps --json
```

Run admission checks in a disposable home and isolated Hermes checkout; `--install-deps` bootstraps Hermes and can require host compilers/libraries. An intentional install uses `uv pip install --python /absolute/path/to/hermes-python --no-deps dist/hermes_attune-0.3.1-py3-none-any.whl`, adds `attune` to that profile's existing `plugins.enabled` list, then starts a fresh Hermes process. Preserve other enabled plugins. **No live install, restart, job or preview grant is part of local verification.** Public/catalog installation requires a published repository.

## Owner selects the scope

```text
/attune goal "Reduce manual sales reporting" "An accurate repeatable weekly summary" "Owner-supplied facts"
/attune project-add "Sales tool" /absolute/project GOAL_ID "sales.py,tests/test_sales.py,README.md"
/attune checkin
/attune projects
/attune project PROJECT_ID
```

Selection binds an active goal, one explicit directory and **1–32 exact relative source/data filenames**. No globs, symlinks, hidden files, traversal paths or credential filenames. Missing selected files can be created in the preview. The selected text packet is bounded; narrow the selection if it exceeds the cap. Model tools cannot select projects, edit grants or self-approve.

Model tools: `attune_goal`, `attune_checkin`, `attune_answer`, `attune_work`, `attune_deliver`, `attune_status`, `attune_projects`, `attune_project`, `attune_propose`, `attune_build`, `attune_build_result`.

## Suggest first / Surprise with previews

```text
/attune approve OPPORTUNITY_ID
/attune build OPPORTUNITY_ID
/attune build-result OPPORTUNITY_ID
/attune build-feedback OPPORTUNITY_ID useful
/attune build-feedback OPPORTUNITY_ID revise

/attune project-mode PROJECT_ID preview 7 1
/attune project-mode PROJECT_ID suggest
/attune project-mode PROJECT_ID off
```

`approve` permits **one exact proposed changed-source packet**, expires at the earlier of two hours/local midnight, and binds current learning/goal/source evidence. Standing preview grants last **1–30 days**, permit **1–3 claimed attempts/project/local day**, and remain restricted to selected files. Failed/interrupted attempts count too. Concurrent claims serialize in SQLite; one opportunity is never automatically re-executed. Mode changes revoke outstanding approvals and invalidate active publication. `revise` returns the project to suggest-only and prompts a correction; answering or liking a result never restores/expands authority. A changed goal, learned answer, source file, pause, expiry or revoked grant prevents stale success.

Worker: fresh filesystem/network/process namespaces, cleared environment, read-only system/selected-file mounts, no host home or ambient credentials, writable `/tmp`, 20-second wall timeout, 15-second CPU limit, 512 MiB per-process address-space ceiling, 1 MiB output-file ceiling, 64 descriptors and finite UID-wide task ceiling. Bubblewrap is a Linux process boundary, **not a VM or a whole-machine sandbox**; resource ceilings are not a cgroup aggregate budget. Project-controlled tests are advisory, not cryptographic/semantic attestation. At least one test must run, with no skipped/failed tests, before a result can be called verified. Owner acceptance remains separate.

`verified` means actual isolated checks passed for retained preview/diff bytes and current project context still matches. Result readback rechecks hashes and context: rejected or changed-context results become `rejected`/`stale`, with `historical_status=verified` preserving the original technical check. `current_build_permission` separately reports grant/approval validity; a completed preview is not erased merely because its publication deadline later passes. Per-run completion framing and strict report parsing prevent ordinary stdout from masquerading as the runner result; project-controlled Python still cannot independently attest itself. A hard process stop preserves a running claim as interrupted/unknown, not invented success or an automatic retry. Preview files never overwrite the original project; merge and deploy are deliberately absent. See [operations](docs/OPERATIONS.md) for install, upgrade, pause, backup, rollback and recovery limits.

## Existing goal and Markdown controls

```text
/attune help
/attune update GOAL_ID "Revised success" "Replacement supplied facts"
/attune complete GOAL_ID
/attune reopen GOAL_ID
/attune defer GOAL_ID
/attune drop GOAL_ID
/attune routine on
/attune feedback RUN_ID useful
/attune feedback RUN_ID revise
/attune questions off
/attune snooze 3
/attune pause
/attune resume
/attune routine off
```

`routine on` grants local **Markdown drafting only**, not code previews. Draft throughput grows 1 -> 2 -> 3/day after 3/6 distinct accepted results since the latest negative rating. Rejection disables routine drafting until owner re-enables. Contracts already fulfilled are not redrafted; no manufactured duplicate work. File/format verification does not prove factual accuracy or usefulness.

Question snooze/off/interval do not revoke existing effects. `pause` stops new Attune observation/drafts/builds and rejects active stale publication, but cannot retract completed artifacts. `project-mode off` revokes that project's observation/builds. These controls govern this plugin, not every Hermes tool or CCT capability.

## Daily wake — explicit opt-in only

```text
/attune schedule 09:00 Australia/Melbourne local
/attune unschedule
```

These commands return native cron handoffs, **not enrolled or removed jobs**. Timezone must exactly match the profile's configured IANA timezone; Attune never changes global settings or guesses a destination. `schedule` returns an explicit `cronjob_request`. Owner reviews and approves that request through Hermes native cron: list existing jobs (including disabled), avoid duplicates, create the exact request and read back ID/time/destination/toolset. The wake combines daily questions, one selected-project opportunity/preview and separately permitted drafting; toolsets are restricted to `attune` and `no_mcp`, without attached sessions or chained context. `unschedule` explains native inspection/removal; a legacy stored ID is an unverified hint. Attune never inspects or mutates host jobs or imports private scheduler APIs. Prepared request, saved job, actual firing and delivered message are separate gates.

## Verification and live gates

Historical v0.2.1: 105 canonical tests plus separate offline installed-wheel simulation; not evidence of the new build slice. Current coverage and exact receipts are documented in [verification](docs/VERIFICATION.md); current release evidence lives in `artifacts/verification/submission-v031/` beside the clean submission export. The expanded suite exercises real Bubblewrap children, actual source preservation, failure/zero-test/timeout cases, credential/network/write isolation, stale approvals/results, malformed worker reports, mid-execution pause/revocation/expiry, concurrency, daily learning, repeated rejection and retained hash readback. Scripted fixtures are not live model-generated improvements or elapsed-day usage.

Prior manual live provider acceptance remains unresolved, with routine off and no saved schedule last verified. No competition submission, catalog PR, live scheduled AI acceptance, public repository/published immutable release commit or deployment is claimed. Admission/publication evidence and remaining owner gates are listed in `docs/SUBMISSION.md`.

## Data and trust

Profile-scoped SQLite and private `draft-*.md` / `preview-*` directories. Exact location: `attune status` -> `data_dir`. Explicit goals/material/answers/drafts, selected source snapshots and generated changes persist **as plaintext**; selected tool context can reach the configured model. No automatic conversation capture or arbitrary-account inspection. No encryption/automatic retention/cleanup policy. Up to ten selected projects and 200 proposals per profile in this increment; owner-managed archival/reset remains future work. Back up before upgrades/removal.

Existing schema-1 goals/runs/feedback are retained with additive project tables; unknown schema fails closed. Draft publication still uses staged/fsynced/no-clobber hard links. Interrupted staging is not success. This is not a whole-system power-loss durability guarantee.

Trusted **single operator per Hermes profile**, not isolation between users/chats. Owner slash/CLI controls are separate from model tools. In-process plugin authority cannot constrain a separately authorized host shell, stop a malicious operator editing state, or prove semantic usefulness. The plugin launches the bounded verifier with an argv list (no shell interpolation), installs no packages and makes no direct third-party HTTP requests. Explicit scheduled model work uses Hermes' existing provider and normal usage.

MIT · Michael Costea · Bounded local release. Publication, eligibility, live activation and competition submission remain separate gates.
