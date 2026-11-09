"""Adversarial lifecycle and continuation coverage for project previews."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
from threading import Event

import pytest
from test_attune import env
from test_projects import project, learn, propose, changes
from hermes_attune import invoke
from hermes_attune import sandbox
from hermes_attune.projects import ProjectLoop


def finish_learning(store, p):
    for _ in range(4):
        c = store.checkin()
        for q in c.get("questions", []):
            if q["kind"].startswith("project_daily:"):
                continue
            store.answer(c["id"], q["id"], q["choices"][0], owner=True)


def test_daily_learning_continues_and_changed_friction_changes_eligible_builds(project):
    store, clock, loop, p, _ = project
    finish_learning(store, p)
    clock.now += timedelta(days=1)
    c = store.checkin()
    q = next(q for q in c["questions"] if q["kind"].startswith("project_daily:"))
    store.answer(c["id"], q["id"], "change_friction", owner=True)
    c = store.checkin()
    friction = next(q for q in c["questions"] if q["kind"] == "friction:" + p["id"])
    store.answer(c["id"], friction["id"], "reliability", owner=True)
    # Re-delivery of the same daily answer must not erase the new learning.
    assert store.answer(c["id"], q["id"], "change_friction", owner=True)["status"] == "already_recorded"
    with pytest.raises(ValueError, match="learned project friction"):
        propose(store, loop, p)
    assert loop.observe(p["id"])["learned"]["friction:" + p["id"]] == "reliability"
    clock.now += timedelta(days=1)
    assert any(q["kind"].startswith("project_daily:") for q in store.checkin()["questions"])
    assert loop.catalog()[0]["mode"] == "suggest"


def test_repeated_rejection_binds_fresh_correction_to_exact_opportunity(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    first = propose(store, loop, p)
    loop.feedback(first["id"], "revise")
    c = store.checkin()
    old = next(q for q in c["questions"] if q["kind"].startswith("project_correction:"))
    store.answer(c["id"], old["id"], "smaller_scope", owner=True)
    second = propose(store, loop, p, "monthly")
    loop.feedback(second["id"], "revise")
    c = store.checkin()
    new = next(q for q in c["questions"] if q["kind"].startswith("project_correction:"))
    assert new["id"] != old["id"] and new["opportunity_id"] == second["id"]
    assert c["status"] != "already_answered"
    with pytest.raises(ValueError):
        store.answer(c["id"], old["id"], "smaller_scope", owner=True)
    store.answer(c["id"], new["id"], "different_approach", owner=True)


@pytest.mark.parametrize("mutation", ["pause", "revoke", "goal", "midnight", "expiry"])
def test_authority_changes_during_real_child_execution_cannot_publish_success(project, monkeypatch, mutation):
    store, clock, loop, p, _ = project
    learn(store, p["id"])
    files = changes()
    files["tests/test_sales.py"] += "    def test_wait(self):\n        import time\n        time.sleep(2)\n"
    opp = loop.propose(p["id"], "Slow preview", "Exercise live authority checks", "repetition", json.dumps(files))
    loop.approve(opp["id"])
    original = sandbox.verify
    running = Event()
    proceed = Event()
    def wrapped(path, allowed):
        calls = 0
        def gate():
            nonlocal calls
            calls += 1
            if calls == 2:  # Child has already been launched by the real verifier.
                running.set()
                assert proceed.wait(5)
            return allowed()
        return original(path, gate)
    monkeypatch.setattr(sandbox, "verify", wrapped)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(loop.execute, opp["id"])
        assert running.wait(5)
        if mutation == "pause": store.control("pause", True)
        if mutation == "revoke": loop.mode(p["id"], "off")
        if mutation == "goal": store.revise_goal(p["goal_id"], "A new success criterion")
        if mutation == "midnight": clock.now += timedelta(days=1)
        if mutation == "expiry": clock.now += timedelta(minutes=6)
        proceed.set()
        result = future.result(timeout=10)
    assert result["status"] == "failed"
    assert result["verification"]["reason"] == "authority_revoked"
    assert loop.result(opp["id"])["status"] == "failed"


def test_missing_source_or_tampered_preview_invalidates_readback(project):
    store, _, loop, p, source = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    result = loop.execute(opp["id"])
    Path(result["preview"]).joinpath("sales.py").write_text("# tampered\n")
    with pytest.raises(ValueError, match="artifact changed"):
        loop.result(opp["id"])
    (source / "sales.py").unlink()
    other = propose(store, loop, p, "monthly")
    (source / "sales.py").write_text("# new source\n")
    assert loop.execute(other["id"])["status"] == "blocked"


def test_interrupted_claim_is_not_reexecuted_or_fabricated_success(project, monkeypatch):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    def interrupted(*_): raise RuntimeError("Injected process interruption")
    monkeypatch.setattr(sandbox, "verify", interrupted)
    with pytest.raises(RuntimeError): loop.execute(opp["id"])
    fresh = ProjectLoop(type(store)(store.root, store.clock))
    assert fresh.execute(opp["id"])["status"] == "running"
    assert "not automatically replayed" in fresh.result(opp["id"])["note"]


def test_real_worker_timeout_is_failure_not_success(project):
    _, _, _, _, source = project
    (source / "tests/test_sales.py").write_text("import time, unittest\nclass TestHang(unittest.TestCase):\n    def test_wait(self): time.sleep(10)\n")
    result = sandbox.verify(source, lambda: True, timeout=.2)
    assert result["reason"] == "timeout" and not result["passed"]


def test_process_safe_daily_cap_reserves_at_most_one_attempt(project):
    store, clock, loop, p, _ = project
    learn(store, p["id"])
    loop.mode(p["id"], "preview", 1, 1)
    opportunities = [propose(store, loop, p, label) for label in ("weekly", "monthly")]
    script = """import json, sys
from datetime import datetime
from hermes_attune.core import Attune
from hermes_attune.projects import ProjectLoop
store = Attune(sys.argv[1], lambda: datetime.fromisoformat(sys.argv[3]))
print(json.dumps(ProjectLoop(store).execute(sys.argv[2])))
"""
    children = [subprocess.Popen([sys.executable, "-c", script, str(store.root), opp["id"], clock.now.isoformat()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for opp in opportunities]
    results = []
    for child in children:
        out, err = child.communicate(timeout=20)
        assert child.returncode == 0, err
        results.append(json.loads(out))
    assert sorted(r["status"] for r in results) == ["daily_cap", "verified"]
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM builds").fetchone()[0] == 1


def test_native_model_invocation_surface_runs_expanded_loop(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    packet = invoke(store, "attune_project", {"project_id": p["id"]})
    assert packet["goal"]["id"] == p["goal_id"]
    opp = invoke(store, "attune_propose", {"project_id": p["id"], "title": "Native preview", "rationale": "Reduce repeated totals", "category": "repetition", "changes_json": json.dumps(changes())})
    assert invoke(store, "attune_build", {"opportunity_id": opp["id"]})["status"] == "needs_approval"
    loop.approve(opp["id"])
    result = invoke(store, "attune_build", {"opportunity_id": opp["id"]})
    assert result["verification"]["tests_run"] == 2
    assert invoke(store, "attune_build_result", {"opportunity_id": opp["id"]}) == result
