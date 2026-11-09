"""Product audit regressions: progress, changing needs and truthful release surfaces."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import sqlite3

import pytest
from test_attune import env, goal, ready, draft
from hermes_attune import command, register
from hermes_attune.core import Attune


def test_delivered_contract_does_not_repeat_and_second_goal_gets_work(env):
    store, clock = env
    first = goal(store, "First active goal")
    second = goal(store, "Second active goal")
    store.control("routine", True)
    packet = store.work()
    assert packet["contract"]["goal"] == first["title"]
    store.deliver(packet["id"], draft(packet))
    clock.now += timedelta(days=1)
    packet = store.work()
    assert packet["contract"]["goal"] == second["title"]
    store.deliver(packet["id"], draft(packet))
    clock.now += timedelta(days=1)
    assert store.work()["status"] == "awaiting_update"
    assert len(list(store.root.glob("draft-*.md"))) == 2


def test_owner_edit_preserves_identity_and_replaces_inflight_packet(env):
    store, _ = env
    old = ready(store)
    ident = store.status()["goals"][0]["id"]
    updated = command(store, f'update {ident} "A grounded comparison" "New supplied facts"')
    assert updated["id"] == ident and updated["revision"] == 2
    new = store.work()
    assert new["id"] != old["id"]
    assert new["contract"]["success"] == "A grounded comparison"
    assert new["contract"]["material"] == "New supplied facts"
    with pytest.raises(ValueError):
        store.deliver(old["id"], draft(old))
    assert store.deliver(new["id"], draft(new))["status"] == "verified"
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 1


def test_owner_can_complete_reopen_and_defer_without_model_authority(env):
    store, _ = env
    packet = ready(store)
    ident = store.status()["goals"][0]["id"]
    command(store, f"complete {ident}")
    assert store.status()["goals"][0]["state"] == "done"
    with pytest.raises(ValueError, match="Goal changed"):
        store.deliver(packet["id"], draft(packet))
    assert store.work()["status"] == "nothing_ready"
    command(store, f"reopen {ident}")
    assert store.work()["status"] == "ready"
    command(store, f"defer {ident}")
    assert store.work()["status"] == "nothing_ready"


def test_exact_duplicate_draft_is_not_a_new_result(env):
    store, clock = env
    packet = ready(store)
    content = draft(packet)
    store.deliver(packet["id"], content)
    ident = store.status()["goals"][0]["id"]
    clock.now += timedelta(days=1)
    store.revise_goal(ident, "Now include the new supplied constraint", "New constraint")
    current = store.work()
    with pytest.raises(ValueError, match="Duplicate draft"):
        store.deliver(current["id"], content)
    assert len(list(store.root.glob("draft-*.md"))) == 1
    assert store.deliver(current["id"], draft(current))["status"] == "verified"


def test_maximum_goal_inputs_keep_valid_bounded_context(env):
    store, _ = env
    for i in range(8):
        store.goal(str(i)+"🙂"*239, "\\\""*600, "fact", owner=True)
    context = store.context()
    assert len(context) <= 3400
    payload = json.loads(context.split("\n", 1)[1])
    assert payload["routine_enabled"] is False
    assert "boundary" in payload
    assert payload["omitted_goals"] > 0


def test_new_proposal_joins_answered_daily_checkin(env):
    store, _ = env
    goal(store)
    checkin = store.checkin()
    store.answer(checkin["id"], "format", "steps")
    fresh = goal(store, "New outcome from conversation", owner=False)
    refreshed = store.checkin()
    assert refreshed["id"] == checkin["id"]
    question = next(q for q in refreshed["questions"] if q["goal_id"] == fresh["id"])
    store.answer(refreshed["id"], question["id"], "now")
    assert not store.checkin()["questions"]


def test_stale_unanswered_focus_refreshes_after_owner_edit(env):
    store, _ = env
    g = goal(store, owner=False)
    first = store.checkin()
    store.revise_goal(g["id"], "Revised success")
    updated = store.checkin()
    assert updated["id"] == first["id"]
    question = next(q for q in updated["questions"] if q["kind"] == "focus")
    assert question["revision"] == 2
    assert store.answer(updated["id"], question["id"], "now")["status"] == "learned"


def test_today_answer_from_yesterday_cannot_be_silently_replayed(env):
    store, clock = env
    goal(store, owner=False)
    c = store.checkin()
    focus = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], focus["id"], "now", "today")
    clock.now += timedelta(days=1)
    with pytest.raises(ValueError, match="expired|stale"):
        store.answer(c["id"], focus["id"], "now", "today")
    assert store.status()["goals"][0]["state"] == "proposed"


def test_edit_during_today_focus_preserves_original_expiry(env):
    store, clock = env
    g = goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now", "today")
    store.revise_goal(g["id"], "New success criteria")
    clock.now += timedelta(days=1)
    assert store.status()["goals"][0]["state"] == "proposed"
    assert store.status()["goals"][0]["success"] == "New success criteria"


def test_correction_does_not_leak_into_another_goal(env):
    store, clock = env
    first = ready(store)
    store.deliver(first["id"], draft(first))
    store.feedback(first["id"], "revise")
    c = store.checkin()
    store.answer(c["id"], "correction", "shorter")
    ident = store.status()["goals"][0]["id"]
    command(store, f"complete {ident}")
    goal(store, "Unrelated outcome")
    store.control("routine", True)
    clock.now += timedelta(days=1)
    packet = store.work()
    assert packet["contract"]["correction"] is None


def test_changed_goal_then_stale_focus_replay_is_rejected(env):
    store, _ = env
    g = goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now")
    store.revise_goal(g["id"], "Changed criteria")
    with pytest.raises(ValueError, match="stale"):
        store.answer(c["id"], q["id"], "now")


def test_current_state_survives_reopen_without_migration_reset(env):
    store, clock = env
    g = goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "comparison")
    reopened = Attune(store.root, lambda: clock.now)
    assert reopened.status()["goals"][0]["id"] == g["id"]
    assert reopened.status()["preferences"]["format"] == "comparison"
    with reopened.transaction() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert reopened.setting(db, "schema") == 1


def test_initialization_and_claims_are_safe_across_instances(env):
    store, clock = env
    goal(store)
    store.control("routine", True)
    def claim(_):
        return Attune(store.root, lambda: clock.now).work()["id"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert len(set(pool.map(claim, range(16)))) == 1


def test_tied_goal_times_keep_insertion_order_not_uuid_order(env, monkeypatch):
    from types import SimpleNamespace
    from hermes_attune import core
    ids = iter(["f" * 32, "a" * 32, "b" * 32])
    monkeypatch.setattr(core.uuid, "uuid4", lambda: SimpleNamespace(hex=next(ids)))
    store, _ = env
    first = goal(store, "First")
    second = goal(store, "Second")
    assert first["id"] > second["id"]  # Force UUID order opposite to owner order.
    store.control("routine", True)
    assert store.work()["contract"]["goal"] == first["title"]


def test_admission_recorder_can_register_without_profile_state():
    from hermes_attune import TOOLS
    class Recorder:
        def __init__(self): self.tools = {}
        def register_tool(self, **kw): self.tools[kw["name"]] = kw["handler"]
        def register_command(self, *args, **kw): pass
        def register_hook(self, *args, **kw): pass
        def register_skill(self, *args, **kw): pass
    ctx = Recorder()
    register(ctx)
    assert set(ctx.tools) == set(TOOLS)
    assert json.loads(ctx.tools["attune_status"]({}))["error"] == "Hermes must provide profile-scoped plugin state"


def test_repeated_owner_rejection_allows_another_distinct_correction(env):
    store, clock = env
    packet = ready(store)
    for attempt in range(3):
        store.deliver(packet["id"], draft(packet) + f"\nOwner revision attempt {attempt}.")
        store.feedback(packet["id"], "revise")
        checkin = store.checkin()
        store.answer(checkin["id"], "correction", "shorter")
        assert store.work()["status"] == "needs_consent"
        store.control("routine", True)
        clock.now += timedelta(days=1)
        packet = store.work()
        assert packet["status"] == "ready"
        assert packet["contract"]["correction"] == "shorter"
    assert len(list(store.root.glob("draft-*.md"))) == 3
    assert store.status()["drafts_per_day"] == 1


@pytest.mark.parametrize("failure", ["partial_write", "fsync"])
def test_interrupted_publication_preserves_retry(env, monkeypatch, failure):
    from hermes_attune import core
    store, clock = env
    packet = ready(store)
    content = draft(packet)
    original_fdopen = core.os.fdopen
    class InterruptedWriter:
        def __init__(self, fd, mode): self.stream = original_fdopen(fd, mode)
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def write(self, data):
            self.stream.write(data[:25])
            self.stream.flush()
            raise OSError("injected partial write")
    def interrupted_sync(fd): raise OSError("injected fsync failure")
    with monkeypatch.context() as patch:
        if failure == "partial_write":
            patch.setattr(core.os, "fdopen", InterruptedWriter)
        else:
            patch.setattr(core.os, "fsync", interrupted_sync)
        with pytest.raises(OSError, match="injected"):
            store.deliver(packet["id"], content)
    assert not list(store.root.glob("draft-*.md"))
    assert store.status()["runs"][0]["state"] == "running"
    reopened = Attune(store.root, lambda: clock.now)
    assert reopened.work()["id"] == packet["id"]
    assert reopened.deliver(packet["id"], content)["status"] == "verified"
    assert reopened.deliver(packet["id"], content)["status"] == "already_verified"
    assert not list(store.root.glob(".draft-*.tmp"))


def test_registry_returns_structured_database_failure(tmp_path, monkeypatch):
    class Context:
        state = type("State", (), {"data_dir": tmp_path / "native"})()
        def __init__(self): self.tools, self.hooks = {}, {}
        def register_tool(self, **kw): self.tools[kw["name"]] = kw["handler"]
        def register_command(self, *args, **kw): pass
        def register_hook(self, name, handler): self.hooks[name] = handler
        def register_skill(self, *args, **kw): pass
    ctx = Context()
    register(ctx)
    def unavailable(*args, **kw): raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(Attune, "status", unavailable)
    assert "error" in json.loads(ctx.tools["attune_status"]({}))
    assert "unavailable" in ctx.hooks["pre_llm_call"]()["context"].lower()
