"""Regressions for independently reported calibration/claim lifecycle defects."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from test_attune import env, goal, ready, draft


def test_format_change_blocks_old_delivery_before_another_claim(env):
    store, _ = env
    packet = ready(store)
    checkin = store.checkin()
    store.answer(checkin["id"], "format", "steps")
    with pytest.raises(ValueError, match="contract changed"):
        store.deliver(packet["id"], draft(packet))
    assert not list(store.root.glob("draft-*.md"))


def test_changed_format_replaces_packet_without_spending_another_slot(env):
    store, _ = env
    old = ready(store)
    checkin = store.checkin()
    store.answer(checkin["id"], "format", "steps")
    current = store.work()
    assert current["status"] == "ready"
    assert current["id"] != old["id"]
    assert current["contract"]["format"] == "steps"
    with pytest.raises(ValueError):
        store.deliver(old["id"], draft(old))
    assert store.deliver(current["id"], draft(current))["status"] == "verified"
    assert store.work()["status"] == "daily_cap"


def test_demoted_goal_is_not_resumed_and_slot_can_be_reused(env):
    store, _ = env
    goal(store, owner=False)
    checkin = store.checkin()
    question = next(q for q in checkin["questions"] if q["kind"] == "focus")
    store.answer(checkin["id"], question["id"], "now")
    store.control("routine", True)
    old = store.work()
    store.answer(checkin["id"], question["id"], "later")
    assert store.work()["status"] == "nothing_ready"
    assert store.status()["runs"][0]["state"] == "superseded"
    replacement = goal(store, "A different permitted draft")
    current = store.work()
    assert current["status"] == "ready"
    assert current["id"] != old["id"]
    assert current["contract"]["goal"] == replacement["title"]
    assert store.deliver(current["id"], draft(current))["status"] == "verified"
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM events WHERE kind='work_superseded'").fetchone()[0] == 1


def test_latest_negative_rating_resets_cap_even_for_an_old_draft(env):
    store, clock = env
    goal(store)
    store.control("routine", True)
    identifiers = []
    for i in range(4):
        ident = store.status()["goals"][0]["id"]
        store.revise_goal(ident, f"Changed owner criteria for stage {i}")
        packet = store.work()
        store.deliver(packet["id"], draft(packet))
        store.feedback(packet["id"], "useful")
        identifiers.append(packet["id"])
        clock.now += timedelta(days=1)
    assert store.status()["drafts_per_day"] == 2
    result = store.feedback(identifiers[0], "revise")
    assert result["drafts_per_day"] == 1
    assert result["routine_enabled"] is False
    for identifier in identifiers[1:]:
        for _ in range(3):
            store.feedback(identifier, "useful")
    assert store.status()["drafts_per_day"] == 1


def test_duplicate_feedback_records_only_one_event(env):
    store, _ = env
    packet = ready(store)
    store.deliver(packet["id"], draft(packet))
    for _ in range(6):
        store.feedback(packet["id"], "useful")
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM events WHERE kind='owner_feedback'").fetchone()[0] == 1


def test_same_day_negative_feedback_adds_correction_to_existing_checkin(env):
    store, _ = env
    goal(store)
    checkin = store.checkin()
    store.answer(checkin["id"], "format", "recommendation")
    store.control("routine", True)
    packet = store.work()
    store.deliver(packet["id"], draft(packet))
    store.feedback(packet["id"], "revise")
    updated = store.checkin()
    assert updated["id"] == checkin["id"]
    assert [q["kind"] for q in updated["questions"]] == ["correction"]
    store.answer(updated["id"], "correction", "more_specific")
    assert store.checkin()["questions"] == []
    assert store.work()["status"] == "needs_consent"


@pytest.mark.parametrize("zone", ["UTC", "Australia/Melbourne"])
def test_midnight_closes_old_claim_and_prevents_overlapping_deliveries(env, zone):
    store, clock = env
    store.control("timezone", zone)
    clock.now = datetime(2026, 11, 6, 23, 59, tzinfo=ZoneInfo(zone)).astimezone(timezone.utc)
    old = ready(store)
    clock.now += timedelta(minutes=2)
    with pytest.raises(ValueError, match="expired or closed"):
        store.deliver(old["id"], draft(old))
    current = store.work()
    assert current["status"] == "ready"
    assert current["id"] != old["id"]
    assert store.deliver(current["id"], draft(current))["status"] == "verified"
    with pytest.raises(ValueError):
        store.deliver(old["id"], draft(old))
    assert len(list(store.root.glob("draft-*.md"))) == 1
    assert store.work()["status"] == "daily_cap"


def test_correction_change_blocks_same_headings_with_outdated_contract(env):
    store, clock = env
    first = ready(store)
    store.deliver(first["id"], draft(first))
    store.feedback(first["id"], "revise")
    checkin = store.checkin()
    store.answer(checkin["id"], "correction", "shorter")
    store.control("routine", True)
    clock.now += timedelta(days=1)
    old = store.work()
    store.answer(checkin["id"], "correction", "more_evidence")
    with pytest.raises(ValueError, match="contract changed"):
        store.deliver(old["id"], draft(old))
    current = store.work()
    assert current["id"] != old["id"]
    assert current["contract"]["correction"] == "more_evidence"
    assert current["contract"]["required_headings"] == old["contract"]["required_headings"]
