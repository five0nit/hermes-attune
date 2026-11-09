# Attune operations — 0.3.1

Scope: one trusted operator and one Hermes profile. Local release verification does **not** install into the live profile, reload a gateway, enroll a daily wake, call a provider or deliver a chat message. Those are separate acceptance steps.

## Install and first acceptance

1. Verify the supplied `.zip.sha256`, archive `MANIFEST.sha256` and release receipt. Use Python 3.11+ and the same Hermes interpreter that will load the plugin; preview execution additionally requires Linux, `bwrap`, `prlimit` and `/usr/bin/python3`.
2. Run `hermes plugins validate /absolute/clean/plugin --install-deps --json` in a disposable home/isolated Hermes checkout. The official validator checks manifest, capabilities, API usage, loadability and dependencies. Native release receipts separately verify eleven tools, command, hook, skill, entry-point loading and non-mutating cron handoff. Neither check exercises live inference/delivery.
3. For an explicitly approved installation, install that same wheel with `uv pip install --python /absolute/hermes-python --no-deps /absolute/hermes_attune-0.3.1-py3-none-any.whl`. Add `attune` to the intended profile's existing `plugins.enabled` list, preserving all other entries. Do not enable overrides. Global wheel installation can affect other profiles that also enable Attune: inventory them before proceeding.
4. Start a fresh Hermes process for that profile. Existing gateway processes are not proof of the new version. Reload/restart only the authorized owning profile; never restart the default gateway as a shortcut.
5. Check `/attune status` and record `data_dir`, version, paused/routine state, questions and saved schedule. Do not guess the plugin-state path; use the returned path. `/attune checkin` should ask useful short questions without granting execution.
6. Owner selects a small non-sensitive Python project and exact files, supplies real answers and approves **one** proposed improvement. Confirm real test count, preview/diff, original-file preservation and owner feedback. Selected file plaintext can reach the configured model.
7. A real model-generated useful preview and actual chat delivery are the live acceptance gate. Fixture demos and native-loader receipts do not satisfy it. Daily scheduling remains off until time, IANA timezone and destination are explicitly approved.

## Upgrade from 0.2.x

- Record current package version/module location, enabled-plugin configuration, `/attune status`, schedule ID and data directory. Preserve the previous artifact/configuration.
- `/attune pause` stops new Attune work. `/attune unschedule` returns native removal instructions, not deletion. List/inspect jobs through Hermes native cron, obtain exact owner approval, then remove only the inspected job and read back absence. Preserve unrelated/operator-modified jobs. Stored legacy IDs are hints, never ownership proof.
- Quiesce only the authorized owning process before copying state. Preserve the **whole private state directory**, not only `attune.db`: it also contains published drafts/previews referenced by SQLite. SQLite may have WAL/SHM files while open. For an online DB-only diagnostic backup use SQLite's backup API, not a raw live-file copy; this is not a complete artifact backup.
- Install the exact verified wheel, preserve existing enabled plugins and start a fresh process. Schema 1 is retained; new project tables are additive. Existing goals, answers, drafts and owner feedback must remain. Unknown schema is rejected, not reset.
- Check state continuity, SQLite `PRAGMA integrity_check`, module provenance and native loading before resuming. New project enrollment and preview grants are **not** inferred from old draft permission.
- Old draft-only cron jobs are not silently rewritten to the broader learning/project prompt. Re-enroll only on owner instruction after explicit removal. Resume does not grant preview authority or restore revoked grants.

## Native daily wake

`/attune schedule HH:MM TIMEZONE local|PLATFORM:CHAT_ID[:THREAD_ID]` validates explicit route/timezone and returns a `cronjob_request`. It changes no state and creates no job. Review the request with the owner, list existing native jobs including disabled to prevent duplicates, obtain approval, create the exact request through Hermes native cron and read back ID, time, destination and restricted toolsets. No session attachment or chained context. Attune never imports cron internals, manages providers or silently adopts/removes old jobs. Prepared request, saved job, firing and delivery require separate evidence.

## Pause, rejection and result meaning

- `/attune pause`: stop new observation/build/draft work and invalidate active publication. `/attune resume` removes this pause only.
- `/attune project-mode PROJECT_ID off`: revoke that project's observation/build authority. `suggest` keeps proposal-only behavior. Exact approvals and standing grants are separate from initiative preferences.
- `/attune build-feedback OPPORTUNITY_ID revise`: preserve historical checks, mark the idea rejected, revoke grants/outstanding approvals and ask a fresh correction. A later correction or positive preference is not re-enrollment.
- `verified`: checks passed for retained bytes and the current project context still matches. `historical_status=verified` preserves the old technical result when current `status` becomes `stale` or `rejected`. `current_build_permission` separately reports current grant/approval validity. A completed preview is not erased simply because its short publication deadline later passes.
- Hash readback still rejects modified/missing retained bytes, including for historical results. Do not present a stale/rejected preview as a current successful improvement or accept it through the `useful` path.

## Failure and recovery

- Missing sandbox prerequisite: return the concrete failure; install prerequisites only with operator authority. No ambient-shell fallback.
- Failed/zero/skipped tests, malformed/missing completion report or worker termination: not success. Per-run completion framing separates runner results from ordinary stdout; project-controlled Python/tests remain advisory, not independent attestation.
- Timeout/revocation: kill the process group, block publication and retain the claim. Failed and interrupted claims consume the granted daily attempt slot.
- `running` after a process stop: **unknown/interrupted**, never automatically replayed. There is no claim-reset command in 0.3.1. Preserve DB, preview directory and logs; review exact bytes and authority. Propose genuinely different work only after owner review. Do not delete a claim to force execution.
- Capacity: up to ten projects and 200 proposals. No archive/prune command or automatic retention exists. Stop enrollment when the cap is reached; export/back up and obtain an explicit reset/retention decision rather than editing rows or silently deleting history.
- No automatic DB repair. On corruption/unknown schema: pause, preserve state and report the exact exception. Recovery is an operator-reviewed restore/new-profile decision.

## Rollback and removal

Disable `attune` only in the intended profile and remove only an owner-approved, inspected native schedule before unloading. Preserve the complete state directory and configuration; no uninstall step deletes owner artifacts automatically. Reinstall the preserved prior wheel and verify its loader before authorizing an owning-process reload. Do **not** restore an old DB over newer events merely to downgrade code. If schema/state compatibility is uncertain, keep current state read-only and use a separate restored copy for investigation. Never change another profile to make rollback appear successful.

## Release and public gates

`docs/VERIFICATION.md` names local coverage; the bundled machine receipt binds exact artifacts and tests. `docs/HANDOFF.md` lists the remaining live/catalog/public gates. No source merge, deployment, recurring enrollment, public repository, catalog PR or competition submission is part of this release operation.
