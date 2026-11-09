"""Offline, scripted changing-needs demo. No live inference or elapsed-day claim."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

try:
    from hermes_attune.core import Attune
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hermes_attune.core import Attune


# Fictional, public-safe workshop scenario. Each owner update changes the job.
STAGES = [
    ("Plan the initial invitation", "Saturday 10:00; free; 20 seats; venue not supplied.",
     "Invite people to a free Saturday workshop at 10:00, capped at 20 seats.",
     "The time, price and capacity are supplied. Venue and booking route are missing.",
     "Confirm the venue and booking route before distributing the invitation."),
    ("Revise the invitation for the confirmed venue", "Saturday 10:00; free; 20 seats; Community Room B.",
     "Use Community Room B in the invitation; keep Saturday 10:00, free entry and 20 seats.",
     "The owner supplied a venue. The booking route is still missing.",
     "Ask the owner for the booking route; do not invent a link."),
    ("Explain the new capacity limit", "Saturday 10:00; free; Community Room B; capacity reduced to 12 seats.",
     "Replace the 20-seat statement with a 12-seat limit everywhere in the draft.",
     "The reduced capacity makes the previous invitation inaccurate.",
     "Owner reviews the revised limit before sharing; no invitations have been sent."),
    ("Prepare an equipment reminder", "Saturday 10:00; Community Room B; free; 12 seats; participants bring a charged laptop.",
     "Add a reminder to bring a charged laptop to the free Saturday workshop.",
     "The equipment requirement is new owner-supplied material, not a model assumption.",
     "Confirm whether loan equipment exists; no availability has been supplied."),
    ("Prepare the accessibility information request", "Community Room B; access arrangements and accessibility contact not supplied.",
     "Ask the venue for access arrangements and a contact before adding accessibility claims.",
     "No verified access information was supplied; an affirmative claim would be invented.",
     "Owner obtains the venue's answer and supplies it for the next revision."),
    ("Prepare a postponement draft", "Workshop postponed; replacement date not confirmed; preserve the free 12-seat format.",
     "Draft a postponement notice without naming a replacement date.",
     "The date is now unconfirmed. Reusing the original Saturday invitation would mislead.",
     "Owner confirms the replacement date before sending anything."),
    ("Prepare the revised invitation", "New date Sunday 14:00; free; 12 seats; Community Room B; bring a charged laptop.",
     "Replace the postponement with a Sunday 14:00 invitation for Community Room B.",
     "The owner confirmed a new time and retained the free 12-seat laptop format.",
     "Owner checks the booking route and accessibility details before distributing."),
]


def run(root):
    root = Path(root)
    if (root / "attune.db").exists():
        raise ValueError("Demo requires a fresh directory; preserve previous state")
    clock = [datetime(2026, 11, 6, 1, tzinfo=timezone.utc)]
    store = Attune(root, lambda: clock[0])
    goal = store.goal("Prepare the community workshop", STAGES[0][0], STAGES[0][1], owner=False)
    questions = store.checkin()
    focus = next(q for q in questions["questions"] if q.get("goal_id") == goal["id"])
    store.answer(questions["id"], focus["id"], "now")
    store.answer(questions["id"], "format", "recommendation")
    assert store.work()["status"] == "needs_consent"
    store.control("routine", True)
    packets, receipts, owner_updates = [], [], []
    for index, (success, material, recommendation, why, next_step) in enumerate(STAGES):
        if index:
            # Deliberate owner changes, not model-created novelty or acceptance.
            owner_updates.append(store.revise_goal(goal["id"], success, material))
        packet = store.work()
        assert packet["status"] in {"ready", "resume"}, packet
        contract = packet["contract"]
        assert isinstance(contract, dict) and contract["success"] == success
        sample = f"## Recommendation\n{recommendation}\n\n## Why\n{why}\n\n## Next step\n{next_step}\n"
        receipt = store.deliver(packet["id"], sample)
        assert Path(receipt["path"]).is_file()
        packets.append(packet)
        receipts.append(receipt)
        store.feedback(packet["id"], "useful" if index < 6 else "revise")
        if index == 5:
            assert store.status()["drafts_per_day"] == 3
        clock[0] += timedelta(days=1)
        if index == 0:
            assert store.work()["status"] == "awaiting_update", "Unchanged contract must not repeat"
    assert len({r["sha256"] for r in receipts}) == len(STAGES)
    assert not store.status()["routine_enabled"]
    correction = store.checkin()
    assert any(q["kind"] == "correction" for q in correction["questions"])
    assert not any(q["kind"] == "format" for q in correction["questions"])
    result = {
        "mode": "OFFLINE SCRIPTED OWNER INPUTS, FEEDBACK AND SAMPLE DRAFTS; CONTROLLED CLOCK, NOT LIVE INFERENCE OR ELAPSED DAYS",
        "initial_questions": questions, "first_output_contract": packets[0]["contract"],
        "owner_updates": owner_updates, "verified_artifacts": receipts,
        "distinct_artifact_digests": len({r["sha256"] for r in receipts}),
        "unchanged_contract_skipped": True, "earned_drafts_per_day": 3,
        "after_correction": store.status(), "next_question": correction,
        "external_effects": [], "live_schedule": False,
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(run(Path(sys.argv[1])), ensure_ascii=False, indent=2))
    else:
        with tempfile.TemporaryDirectory(prefix="attune-demo-") as raw:
            print(json.dumps(run(Path(raw)), ensure_ascii=False, indent=2))
            print("Disposable demo state removed; pass a fresh directory to retain artifacts.", file=sys.stderr)
