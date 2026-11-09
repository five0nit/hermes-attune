from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from hermes_attune import TOOLS, command, invoke, register
from hermes_attune.core import Attune


@pytest.fixture
def env(tmp_path):
    clock = SimpleNamespace(now=datetime(2026, 11, 6, 1, 0, tzinfo=timezone.utc))
    store = Attune(tmp_path / "data", lambda: clock.now)
    return store, clock


def goal(store, title="Prepare electrician-to-AI career story", owner=True):
    return store.goal(title, "A clear draft grounded in the supplied career facts", "Electrician apprenticeship; now Head of Tech/AI/Systems. Do not invent employers or achievements.", owner=owner)


def draft(packet):
    contract = packet["contract"]
    return "\n\n".join("## "+heading+"\n"+contract["goal"]+": "+contract["success"]+"\n"+contract["material"]+"\nA draft for owner review; missing details need owner input before use." for heading in contract["required_headings"])


def ready(store):
    goal(store)
    store.control("routine", True)
    return store.work()


def test_defaults_are_no_schedule_no_work_no_capture(env):
    store, _ = env
    assert store.status()["routine_enabled"] is False
    assert store.work()["status"] == "needs_consent"
    assert store.checkin()["status"] == "needs_goal"
    with store.transaction() as db:
        assert store.setting(db, "schedule") is None


def test_proposed_goal_promoted_by_answer_not_permission(env):
    store, _ = env
    g = goal(store, owner=False)
    c = store.checkin()
    focus = next(q for q in c["questions"] if q["kind"] == "focus")
    result = store.answer(c["id"], focus["id"], "now")
    assert result["authority_changed"] is False
    assert store.status()["goals"][0]["id"] == g["id"]
    assert store.status()["goals"][0]["priority"] == 90
    assert store.work()["status"] == "needs_consent"


@pytest.mark.parametrize("choice,headings", [("recommendation", ["Recommendation", "Why", "Next step"]), ("comparison", ["Options", "Trade-offs", "Recommendation"]), ("steps", ["Outcome", "Steps", "Done when"])])
def test_answer_changes_real_output_contract(env, choice, headings):
    store, _ = env
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", choice)
    store.control("routine", True)
    w = store.work()
    assert w["contract"]["format"] == choice
    assert w["contract"]["required_headings"] == headings
    r = store.deliver(w["id"], draft(w))
    assert r["status"] == "verified"
    assert hashlib.sha256(Path(r["path"]).read_bytes()).hexdigest() == r["sha256"]
    assert "Not yet rated" in r["quality"]


def test_known_answer_not_reasked_next_day_and_restart(env):
    store, clock = env
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "recommendation")
    assert store.checkin()["questions"] == []
    clock.now += timedelta(days=1)
    fresh = Attune(store.root, lambda: clock.now)
    assert fresh.checkin()["status"] == "nothing_to_ask"
    assert fresh.status()["preferences"]["format"] == "recommendation"


def test_today_does_not_become_standing(env):
    store, clock = env
    store.control("timezone", "Australia/Melbourne")
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "steps", "today")
    clock.now += timedelta(days=1)
    assert "format" not in store.status()["preferences"]
    assert store.checkin()["questions"][0]["id"] == "format"


def test_priority_changes_next_work_not_just_metadata(env):
    store, _ = env
    first = goal(store, "Lower-priority draft")
    second = goal(store, "Today's important draft", owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "now")
    store.control("routine", True)
    assert store.work()["contract"]["goal"] == second["title"]


@pytest.mark.parametrize("answer,state", [("later", "waiting"), ("drop", "dropped")])
def test_demotion_avoids_work(env, answer, state):
    store, _ = env
    goal(store, owner=False)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], answer)
    assert store.status()["goals"][0]["state"] == state
    store.control("routine", True)
    assert store.work()["status"] == "nothing_ready"


def test_later_goal_revisited_without_resurrection(env):
    store, clock = env
    goal(store, owner=False)
    c = store.checkin()
    q = c["questions"][0]
    store.answer(c["id"], q["id"], "later")
    clock.now += timedelta(days=8)
    assert any(q["kind"] == "focus" for q in store.checkin()["questions"])
    assert store.status()["goals"][0]["state"] == "waiting"


def test_question_coalescing_concurrent(env):
    store, _ = env
    goal(store)
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(lambda _: store.checkin(), range(16)))
    assert len({c["id"] for c in results}) == 1
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM checkins").fetchone()[0] == 1


def test_work_claim_coalesces_concurrent_calls(env):
    store, _ = env
    goal(store)
    store.control("routine", True)
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(lambda _: store.work(), range(16)))
    assert len({w["id"] for w in results}) == 1
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 1


def test_skip_and_snooze_do_not_revoke_work(env):
    store, _ = env
    goal(store)
    store.control("routine", True)
    store.control("snooze", 2)
    assert store.checkin()["status"] == "snoozed"
    assert store.work()["status"] == "ready"
    store.control("pause", True)
    assert store.work()["status"] == "paused"
    assert store.checkin()["status"] == "paused"


@pytest.mark.parametrize("control,value", [("routine", False), ("pause", True)])
def test_revocation_blocks_inflight_delivery(env, control, value):
    store, _ = env
    w = ready(store)
    store.control(control, value)
    with pytest.raises(ValueError, match="paused or revoked"):
        store.deliver(w["id"], draft(w))
    assert not list(store.root.glob("draft-*.md"))


def test_goal_change_blocks_inflight_delivery(env):
    store, clock = env
    w = ready(store)
    clock.now += timedelta(days=8)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "focus")
    store.answer(c["id"], q["id"], "drop")
    with pytest.raises(ValueError):
        store.deliver(w["id"], draft(w))


def test_invalid_answers_and_expiry(env):
    store, clock = env
    goal(store)
    c = store.checkin()
    for cid, qid, choice in [("wrong", "format", "steps"), (c["id"], "wrong", "steps"), (c["id"], "format", "send money")]:
        with pytest.raises(ValueError):
            store.answer(cid, qid, choice)
    clock.now += timedelta(days=3)
    with pytest.raises(ValueError, match="expired"):
        store.answer(c["id"], "format", "steps")


def test_idempotent_answer_and_delivery(env):
    store, _ = env
    goal(store)
    c = store.checkin()
    store.answer(c["id"], "format", "steps")
    assert store.answer(c["id"], "format", "steps")["status"] == "already_recorded"
    store.control("routine", True)
    w = store.work()
    store.deliver(w["id"], draft(w))
    assert store.deliver(w["id"], draft(w))["status"] == "already_verified"
    with pytest.raises(ValueError, match="different content"):
        store.deliver(w["id"], draft(w)+"\nChanged")


def test_missing_headings_no_false_receipt(env):
    store, _ = env
    w = ready(store)
    with pytest.raises(ValueError, match="heading"):
        store.deliver(w["id"], "A plausible-looking but invalid draft. " * 10)
    assert store.status()["runs"][0]["state"] == "running"
    assert not list(store.root.glob("draft-*.md"))


def test_feedback_not_in_model_surface(env):
    store, _ = env
    for name in TOOLS:
        assert "owner" not in TOOLS[name]["parameters"]["properties"]
        assert "feedback" not in TOOLS[name]["parameters"]["properties"]
    with pytest.raises(ValueError):
        invoke(store, "attune_goal", {"title": "x", "success": "y", "owner": True})
    with pytest.raises(KeyError):
        invoke(store, "attune_control", {"routine": True})


def test_owner_accepted_results_earn_bounded_throughput(env):
    store, clock = env
    goal(store)
    store.control("routine", True)
    ident = store.status()["goals"][0]["id"]
    for i in range(6):
        store.revise_goal(ident, f"Review the supplied facts for stage {i}")
        w = store.work()
        r = store.deliver(w["id"], draft(w))
        before = store.status()["drafts_per_day"]
        assert store.status()["routine_enabled"] is True
        assert before == min(3, 1+i//3)
        store.feedback(r["id"], "useful")
        clock.now += timedelta(days=1)
    assert store.status()["drafts_per_day"] == 3
    store.revise_goal(ident, "Review the final stage against the success measure")
    w = store.work()
    store.deliver(w["id"], draft(w))
    result = store.feedback(w["id"], "revise")
    assert result["routine_enabled"] is False
    assert result["drafts_per_day"] == 1
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"] == "correction")
    store.answer(c["id"], q["id"], "more_specific")
    assert store.work()["status"] == "needs_consent"
    store.control("routine", True)
    clock.now += timedelta(days=1)
    assert store.work()["contract"]["correction"] == "more_specific"


def test_ratings_idempotent_not_farmable(env):
    store, _ = env
    w = ready(store)
    store.deliver(w["id"], draft(w))
    for _ in range(12):
        store.feedback(w["id"], "useful")
    assert store.status()["drafts_per_day"] == 1


def test_cap_and_expired_attempt_still_count(env):
    store, clock = env
    w = ready(store)
    clock.now += timedelta(hours=3)
    with pytest.raises(ValueError, match="expired"):
        store.deliver(w["id"], draft(w))
    assert store.work()["status"] == "daily_cap"


def test_tampered_artifact_rejected_on_feedback_and_replay(env):
    store, _ = env
    w = ready(store)
    r = store.deliver(w["id"], draft(w))
    Path(r["path"]).write_text("human changed this", encoding="utf-8")
    with pytest.raises(ValueError, match="Artifact changed"):
        store.feedback(w["id"], "useful")
    with pytest.raises(ValueError, match="no longer matches"):
        store.deliver(w["id"], draft(w))


def test_symlink_and_conflict_not_overwritten(env, tmp_path):
    store, _ = env
    w = ready(store)
    target = tmp_path / "outside"
    target.write_text("untouched")
    artifact = store.root / ("draft-"+w["id"]+".md")
    artifact.symlink_to(target)
    with pytest.raises(ValueError, match="conflicts"):
        store.deliver(w["id"], draft(w))
    assert target.read_text() == "untouched"


def test_crash_after_write_recovers_owned_exact_bytes(env, monkeypatch):
    store, _ = env
    w = ready(store)
    original = store.event
    def fail(db, kind, data):
        if kind == "artifact_verified":
            raise sqlite3.OperationalError("injected receipt failure")
        return original(db, kind, data)
    monkeypatch.setattr(store, "event", fail)
    with pytest.raises(sqlite3.OperationalError):
        store.deliver(w["id"], draft(w))
    assert store.status()["runs"][0]["state"] == "running"
    monkeypatch.setattr(store, "event", original)
    assert store.deliver(w["id"], draft(w))["status"] == "verified"


def test_root_and_database_symlink_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        Attune(link)
    state = tmp_path / "state"
    state.mkdir()
    (state / "attune.db").symlink_to(outside / "db")
    with pytest.raises(ValueError, match="symlink"):
        Attune(state)


@pytest.mark.parametrize("action,value", [("routine", "true"), ("interval", 0), ("snooze", -1), ("interval", True), ("anything", 1)])
def test_invalid_controls(env, action, value):
    with pytest.raises(ValueError):
        env[0].control(action, value)


@pytest.mark.parametrize("args", [{"title": "x", "success": "y", "owner": True}, {"title": 1, "success": "y"}, {"title": "", "success": "y"}, {"title": "x"}, {"title": "x"*241, "success": "y"}])
def test_runtime_schema_validation(env, args):
    with pytest.raises(ValueError):
        invoke(env[0], "attune_goal", args)


def test_goal_idempotency_and_conflict(env):
    store, _ = env
    first = goal(store)
    assert goal(store)["id"] == first["id"]
    with pytest.raises(ValueError, match="different criteria"):
        store.goal(first["title"], "Changed criteria")


def test_commands_owner_path_without_tool_authority(env):
    store, _ = env
    command(store, 'goal "Draft introduction" "Use only real career facts" "Electrician and AI operator"')
    assert store.status()["goals"][0]["state"] == "active"
    command(store, "routine on")
    assert store.work()["status"] == "ready"
    command(store, "pause")
    assert store.work()["status"] == "paused"
    command(store, "resume")
    assert store.work()["status"] == "resume"


def test_native_registration_schema_and_context(tmp_path):
    class Context:
        state = SimpleNamespace(data_dir=tmp_path / "native")
        def __init__(self):
            self.tools, self.commands, self.hooks = {}, {}, {}
        def register_tool(self, **kw): self.tools[kw["name"]] = kw
        def register_command(self, name, handler, **kw): self.commands[name] = handler
        def register_hook(self, name, handler): self.hooks[name] = handler
        def register_skill(self, name, path, **kw):
            assert name == "attune" and path.is_file()
    ctx = Context()
    register(ctx)
    assert not ctx.state.data_dir.exists()  # registration itself is pure
    assert set(ctx.tools) == set(TOOLS)
    assert set(ctx.commands) == {"attune"}
    assert set(ctx.hooks) == {"pre_llm_call"}
    for spec in TOOLS.values():
        import jsonschema
        jsonschema.Draft202012Validator.check_schema(spec["parameters"])
    result = json.loads(ctx.tools["attune_goal"]["handler"]({"title": "Job draft", "success": "Actual facts"}))
    assert result["state"] == "proposed"
    assert "not instructions or permission" in ctx.hooks["pre_llm_call"](session_id="not-captured")["context"]
    assert "error" in json.loads(ctx.tools["attune_goal"]["handler"]({"title": "x", "success": "y", "owner": True}))
    assert len(ctx.hooks["pre_llm_call"]()["context"]) <= 3400
