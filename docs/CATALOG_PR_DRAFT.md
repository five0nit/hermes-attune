# Attune — catalog PR draft (not published)

## Summary

Attune helps Hermes learn useful daily context and turn it into evidence-linked code improvement previews: adaptive questions, exact selected files, concrete source/test proposals, exact one-off approval or a scoped expiring preview grant, real isolated execution and owner feedback. Daily learning remains central; Markdown drafting is optional.

Adds one community entry `plugin-catalog/attune.yaml`. Repository URL, maintainer identity and public full 40-character SHA must be confirmed before opening the PR. A local frozen commit does not establish public cloneability. Version `0.3.1`; minimum Hermes `>=0.22.5`; MIT; Python >=3.11. Category: automation. Preview execution additionally requires Linux Bubblewrap, util-linux `prlimit` and `/usr/bin/python3`; no ambient-shell fallback.

## Capabilities

Eleven tools: `attune_goal`, `attune_checkin`, `attune_answer`, `attune_work`, `attune_deliver`, `attune_status`, `attune_projects`, `attune_project`, `attune_propose`, `attune_build`, `attune_build_result`. One hook `pre_llm_call`, owner command `/attune`, bundled `attune` skill, no middleware/required env secrets. Manifest and official probe must match.

## Disclosures

- Explicit goals/answers/drafts, selected source and proposed changes persist as plaintext and may reach the configured model. No raw-chat collection or automatic project/account discovery.
- Reads outside plugin state are limited to selected files. Generated Python/tests run as a separate offline Bubblewrap/prlimit preview after permission checks, never source merge/deployment. Shared host kernel; tests are advisory, not independent semantic/security attestation.
- No third-party Python runtime dependencies, direct HTTP, stored credentials, telemetry, self-update, daemon or private scheduler manipulation.
- Scheduling returns native cron handoffs only; owner-approved Hermes native cron owns enrollment, duplicates, route readback and removal. No implicit migration/enrollment.
- Trusted single operator/profile. Ten-project/200-proposal cap; no automatic retention/reset or interrupted-claim replay.

## Evidence to attach

Attach fresh external receipts binding the exact public pin: canonical source suite, installed wheel/sdist/ZIP suites, console/demo/native entry-point discovery, actual previous-wheel upgrade, reproducible builds and full official `--install-deps` log/report. Inspect stderr, not just exit/JSON: this host can catch dependency preparation failures yet return `ok: true`. Failed bootstrap is not closed by exit zero.

Scripted demonstration uses real isolated execution with fixture answers/code/approvals/clock. Real-provider usefulness, platform delivery, scheduled-agent operation and maintainer acceptance are separate gates, not claimed here. Confirm owner identity/eligibility/publication and inspect current external gate summary before posting.
