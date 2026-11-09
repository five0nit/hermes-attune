from datetime import timedelta
import pytest
from test_attune import env, goal, ready, draft


def test_today_focus_reverts_at_local_midnight(env):
    store, clock = env
    store.control("timezone", "Australia/Melbourne")
    g = goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now", "today")
    store.control("routine", True)
    w = store.work()
    assert store.status()["goals"][0]["state"] == "active"
    clock.now += timedelta(hours=13)
    assert store.status()["goals"][0]["state"] == "proposed"
    assert store.status()["goals"][0]["priority"] == g["priority"]
    with pytest.raises(ValueError, match="Run expired or closed"):
        # The 2h run expiry independently prevents stale delivery.
        store.deliver(w["id"], draft(w))


def test_today_preference_restores_underlying_standing(env):
    store, clock = env
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "recommendation")
    store.answer(c["id"], "format", "steps", "today")
    assert store.status()["preferences"]["format"] == "steps"
    clock.now += timedelta(days=1)
    assert store.status()["preferences"]["format"] == "recommendation"
    assert store.checkin()["status"] == "nothing_to_ask"


def test_calendar_cadence_not_24_hour_delay(env):
    store, clock = env
    goal(store, owner=False)
    clock.now = clock.now.replace(hour=23, minute=59)
    first = store.checkin()
    clock.now += timedelta(minutes=2)
    second = store.checkin()
    assert first["id"] != second["id"]


def test_standing_preference_clears_today_override(env):
    store, clock = env
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "steps", "today")
    store.answer(c["id"], "format", "comparison", "standing")
    clock.now += timedelta(days=1)
    assert store.status()["preferences"]["format"] == "comparison"


def test_focus_answer_can_be_corrected_and_made_standing(env):
    store, clock = env
    goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now", "today")
    store.answer(c["id"], q["id"], "later", "standing")
    clock.now += timedelta(days=1)
    assert store.status()["goals"][0]["state"] == "waiting"


def test_corrected_today_focus_retains_original_base(env):
    store, clock = env
    g = goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now", "today")
    store.answer(c["id"], q["id"], "later", "today")
    clock.now += timedelta(days=1)
    restored = store.status()["goals"][0]
    assert (restored["state"], restored["priority"]) == (g["state"], g["priority"])


def test_focus_correction_invalidates_existing_packet(env):
    store, _ = env
    goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now")
    store.control("routine", True)
    w = store.work()
    store.answer(c["id"], q["id"], "later")
    with pytest.raises(ValueError, match="Goal changed"):
        store.deliver(w["id"], draft(w))
    assert not list(store.root.glob("draft-*.md"))


def test_unknown_schema_no_ddl_changes(env):
    store, _ = env
    with store.transaction() as db:
        store.put(db,"schema",999)
        db.execute("DROP TABLE focus_overrides")
    with pytest.raises(ValueError, match="Unsupported"):
        type(store)(store.root)
    with store.transaction() as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='focus_overrides'").fetchone()
