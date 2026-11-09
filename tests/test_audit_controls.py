"""Independent audit regressions: stale replies and exact scheduler authority."""
from datetime import timedelta

import pytest
from test_attune import env, goal, ready, draft
from hermes_attune import schedule


def verified(store):
    packet = store.work()
    store.deliver(packet["id"], draft(packet) + "\nDistinct supplied revision: " + packet["id"])
    return packet["id"]


def test_old_format_reply_cannot_overwrite_newer_daily_answer(env):
    store, clock = env
    goal(store)
    old = store.checkin()
    store.answer(old["id"], "format", "steps", "today")
    clock.now += timedelta(days=1)
    new = store.checkin()
    store.answer(new["id"], "format", "comparison")
    with pytest.raises(ValueError, match="stale|newer"):
        store.answer(old["id"], "format", "recommendation")
    assert store.status()["preferences"]["format"] == "comparison"


@pytest.mark.parametrize("same_run", [False, True])
def test_accepted_result_removes_obsolete_correction(env, same_run):
    store, clock = env
    ready(store)
    old = verified(store)
    store.feedback(old, "revise")
    pending = store.checkin()
    if same_run:
        store.feedback(old, "useful")
    else:
        store.control("routine", True)
        clock.now += timedelta(days=1)
        store.feedback(verified(store), "useful")
    assert not any(q["kind"] == "correction" for q in store.checkin()["questions"])
    with pytest.raises(ValueError, match="stale|exact"):
        store.answer(pending["id"], "correction", "shorter")


def test_retargeted_correction_cannot_apply_reply_to_other_goal(env):
    store, clock = env
    first = goal(store, "Goal A")
    goal(store, "Goal B")
    store.control("routine", True)
    a = verified(store)
    store.feedback(a, "useful")
    clock.now += timedelta(days=1)
    b = verified(store)
    store.feedback(a, "revise")
    old = store.checkin()
    store.feedback(b, "revise")
    new = store.checkin()
    assert old["id"] != new["id"]
    with pytest.raises(ValueError, match="expired|stale|Unknown"):
        store.answer(old["id"], "correction", "shorter")
    assert "correction:" + first["id"] not in store.status()["preferences"]


@pytest.fixture
def cron(env, monkeypatch):
    store, _ = env
    monkeypatch.setattr(schedule, "host", lambda store: "UTC")
    return store


def test_schedule_returns_explicit_native_request_without_enrolling(cron):
    before = cron.status()
    result = schedule.install(cron, "09:00", "UTC", "local")
    assert result["status"] == "owner_action_required" and result["scheduled"] is False
    request = result["cronjob_request"]
    assert request["action"] == "create" and request["schedule"] == "0 9 * * *"
    assert request["enabled_toolsets"] == ["attune", "no_mcp"]
    assert request["skills"] == ["attune"] and request["deliver"] == "local"
    assert request["repeat"] is None and request["attach_to_session"] is False
    assert request["context_from"] == [] and request["continuity"] is False
    assert schedule.identity(cron) in request["prompt"]
    assert "explicit approval" in result["next"] and "duplicate" in result["next"]
    assert schedule.install(cron, "09:00", "UTC", "local") == result
    assert cron.status() == before


def test_schedule_never_imports_private_scheduler_modules(cron, monkeypatch):
    import builtins
    original = builtins.__import__
    def checked(name, *args, **kwargs):
        if name.startswith("cron") or name == "hermes_time":
            raise AssertionError("Private scheduling API used: " + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", checked)
    assert schedule.install(cron, "09:00", "UTC", "local")["scheduled"] is False
    assert schedule.remove(cron)["removed"] == 0


def test_unschedule_preserves_legacy_enrollment_as_unverified_hint(cron):
    legacy = {"id": "owner-modified-job", "name": "Do not delete"}
    with cron.transaction() as db:
        cron.put(db, "schedule", legacy)
    result = schedule.remove(cron)
    assert result["status"] == "owner_action_required" and result["removed"] == 0
    assert result["legacy_enrollment"] == legacy
    assert "only a hint" in result["next"]
    assert cron.status()["schedule"] == legacy


@pytest.mark.parametrize("target", ["local", "signal:+15551234567", "telegram:-100123:42", "slack:C123456:1712345678.001"])
def test_explicit_native_routes_preserved(cron, target):
    result = schedule.install(cron, "09:00", "UTC", target)
    assert result["deliver"] == result["cronjob_request"]["deliver"] == target


@pytest.mark.parametrize("target", ["signal:letters", "telegram:team", "telegram:not-a-chat-id", "slack:general", "telegram:123:bad", "origin", "telegram:home"])
def test_named_or_malformed_routes_rejected_before_request(cron, target):
    with pytest.raises(ValueError, match="explicit"):
        schedule.install(cron, "09:00", "UTC", target)
    assert cron.status()["schedule"] is None


@pytest.mark.parametrize("time", ["9:00", "24:00", "09:60", "00:00; touch /tmp/no", "-1:00"])
def test_malformed_schedule_time_rejected(cron, time):
    with pytest.raises(ValueError, match="HH:MM"):
        schedule.install(cron, time, "UTC", "local")


def test_profile_timezone_must_match_before_request(cron):
    with pytest.raises(ValueError, match="timezone must match"):
        schedule.install(cron, "09:00", "Australia/Melbourne", "local")
    assert cron.status()["schedule"] is None


def test_status_controls_are_unchanged_by_schedule_handoff(cron):
    cron.control("questions", False)
    cron.control("snooze", 3)
    cron.control("interval", 4)
    before = cron.status()
    schedule.install(cron, "09:00", "UTC", "local")
    assert cron.status() == before
    assert before["schedule"] is None and before["schedule_live_verified"] is False
