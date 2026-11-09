"""Expanded product slice: real offline Python execution, not a provider simulation."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pytest
from test_attune import env
from hermes_attune import TOOLS, command, invoke
from hermes_attune.projects import ProjectLoop


@pytest.fixture
def project(env, tmp_path):
    store, clock = env
    source = tmp_path / "selected-project"
    (source / "tests").mkdir(parents=True)
    (source / "sales.py").write_text("def total(values):\n    return sum(values)\n")
    (source / "tests/test_sales.py").write_text(
        "import unittest\nfrom sales import total\nclass SalesTest(unittest.TestCase):\n"
        "    def test_total(self):\n        self.assertEqual(total([2, 3]), 5)\n")
    goal = store.goal("Reduce manual reporting", "A repeatable accurate sales summary", owner=True)
    loop = ProjectLoop(store)
    p = loop.add("Sales", str(source), goal["id"], ["sales.py", "tests/test_sales.py", "README.md"])
    return store, clock, loop, p, source


def learn(store, project_id, choice="repetition"):
    c = store.checkin()
    q = next(q for q in c["questions"] if q["id"] == "friction:" + project_id)
    result = store.answer(c["id"], q["id"], choice, owner=True)
    assert result["authority_changed"] is False


def changes(label="weekly"):
    return {"sales.py": "def total(values):\n    return sum(values)\n\n"
            f"def {label}(values):\n    return {{'count': len(values), 'total': total(values)}}\n",
            "tests/test_sales.py": "import unittest\nfrom sales import total, " + label + "\n"
            "class SalesTest(unittest.TestCase):\n"
            "    def test_total(self):\n        self.assertEqual(total([2, 3]), 5)\n"
            "    def test_summary(self):\n        self.assertEqual(" + label + "([2, 3]), {'count': 2, 'total': 5})\n"}


def propose(store, loop, p, label="weekly"):
    return loop.propose(p["id"], "Automate " + label + " report", "Remove the repeated manual total step",
                        "repetition", json.dumps(changes(label)))


def test_daily_answers_shape_project_packet_without_permission(project):
    store, _, loop, p, source = project
    learn(store, p["id"])
    packet = loop.observe(p["id"])
    assert packet["learned"]["friction:" + p["id"]] == "repetition"
    assert packet["goal"]["success"] == "A repeatable accurate sales summary"
    assert packet["files"]["sales.py"]["sha256"] == hashlib.sha256((source / "sales.py").read_bytes()).hexdigest()
    assert packet["permission"]["mode"] == "suggest"
    assert "not instructions" in packet["boundary"]
    qids = {q["id"] for q in store.checkin()["questions"]}
    assert "friction:" + p["id"] not in qids


def test_real_approved_build_isolated_verified_and_replayable(project):
    store, _, loop, p, source = project
    learn(store, p["id"])
    before = {str(f.relative_to(source)): f.read_bytes() for f in source.rglob("*") if f.is_file()}
    opp = propose(store, loop, p)
    assert loop.execute(opp["id"])["status"] == "needs_approval"
    loop.approve(opp["id"])
    receipt = loop.execute(opp["id"])
    assert receipt["status"] == "verified", receipt
    assert receipt["verification"]["tests_run"] == 2
    assert receipt["verification"]["returncode"] == 0
    assert "weekly" in Path(receipt["preview"]).joinpath("sales.py").read_text()
    assert "+def weekly" in Path(receipt["diff"]).read_text()
    assert {str(f.relative_to(source)): f.read_bytes() for f in source.rglob("*") if f.is_file()} == before
    assert loop.execute(opp["id"])["status"] == "already_verified"
    fresh = ProjectLoop(type(store)(store.root, store.clock))
    assert fresh.result(opp["id"])["verification"]["tests_run"] == 2


def test_standing_preview_needs_no_per_build_approval_but_feedback_never_grants_it(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    loop.mode(p["id"], "preview", 3, 2)
    first = propose(store, loop, p)
    assert loop.execute(first["id"])["status"] == "verified"
    result = loop.feedback(first["id"], "useful")
    assert result["authority_expanded"] is False
    assert loop.catalog()[0]["daily_cap"] == 2
    second = propose(store, loop, p, "monthly")
    assert loop.execute(second["id"])["status"] == "verified"
    third = propose(store, loop, p, "yearly")
    assert loop.execute(third["id"])["status"] == "daily_cap"


def test_rejection_suppresses_same_changes_even_if_reworded_and_drives_next_question(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.feedback(opp["id"], "revise")
    with pytest.raises(ValueError, match="Duplicate"):
        loop.propose(p["id"], "Completely different title", "Rephrased pitch", "repetition", json.dumps(changes()))
    question = next(q for q in store.checkin()["questions"] if q["kind"].startswith("project_correction:"))
    assert "missed" in question["text"]
    store.answer(store.checkin()["id"], question["id"], "smaller_scope", owner=True)
    packet = loop.observe(p["id"])
    assert packet["learned"][question["kind"]] == "smaller_scope"
    assert packet["rejected"][0]["id"] == opp["id"]
    assert packet["permission"]["mode"] == "suggest"


@pytest.mark.parametrize("change", ["source", "goal", "preference", "pause", "revoke", "expiry"])
def test_stale_or_revoked_approval_never_executes(project, change):
    store, clock, loop, p, source = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    if change == "source": (source / "sales.py").write_text("# owner changed source\n")
    if change == "goal": store.revise_goal(p["goal_id"], "Different outcome")
    if change == "preference":
        c = store.checkin()
        store.answer(c["id"], "success:" + p["id"], "fewer_errors", owner=True)
    if change == "pause": store.control("pause", True)
    if change == "revoke": loop.mode(p["id"], "off")
    if change == "expiry": clock.now += timedelta(hours=3)
    result = loop.execute(opp["id"])
    assert result["status"] in {"blocked", "needs_approval"}
    assert not list(store.root.glob("preview-*/project"))


def test_no_shell_network_home_or_ambient_environment_in_worker(project, monkeypatch):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    monkeypatch.setenv("ATTUNE_TEST_AMBIENT_SECRET", "must-not-enter-worker")
    payload = changes()
    payload["tests/test_sales.py"] += (
        "    def test_containment(self):\n"
        "        import os, socket\n"
        "        self.assertNotIn('ATTUNE_TEST_AMBIENT_SECRET', os.environ)\n"
        "        self.assertFalse(os.path.exists('/home/fiv30nit/.hermes'))\n"
        "        self.assertRaises(OSError, socket.create_connection, ('1.1.1.1', 443), .2)\n"
        "        self.assertRaises(OSError, open, '/workspace/sales.py', 'w')\n")
    opp = loop.propose(p["id"], "Offline preview", "Verify bounded execution", "repetition", json.dumps(payload))
    loop.approve(opp["id"])
    receipt = loop.execute(opp["id"])
    assert receipt["status"] == "verified"
    assert receipt["verification"]["tests_run"] == 3


@pytest.mark.parametrize("payload", ["failing", "zero_tests"])
def test_failed_or_empty_verification_cannot_be_called_verified(project, payload):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    files = changes()
    files["tests/test_sales.py"] = "import unittest\n" if payload == "zero_tests" else "raise RuntimeError('injected test failure')\n"
    opp = loop.propose(p["id"], "Bad build", "Should fail honestly", "repetition", json.dumps(files))
    loop.approve(opp["id"])
    result = loop.execute(opp["id"])
    assert result["status"] == "failed"
    assert not result["verification"]["passed"]


@pytest.mark.parametrize("name", ["../escape.py", "/tmp/escape.py", ".env", "auth.json", "x/../../a.py"])
def test_unsafe_paths_rejected_before_read_or_write(project, name):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    with pytest.raises(ValueError):
        loop.propose(p["id"], "bad path", "not allowed", "repetition", json.dumps({name: "x"}))


def test_symlink_source_rejected_and_missing_sandbox_fails_closed(project, monkeypatch):
    store, _, loop, p, source = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    import hermes_attune.sandbox as sandbox
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: None)
    assert loop.execute(opp["id"])["status"] == "failed"
    (source / "sales.py").unlink()
    (source / "sales.py").symlink_to("/etc/passwd")
    with pytest.raises((ValueError, OSError)):
        loop.observe(p["id"])


def test_owner_controls_absent_from_model_tools(project):
    store, _, loop, p, _ = project
    assert {"attune_projects", "attune_project", "attune_propose", "attune_build", "attune_build_result"} <= set(TOOLS)
    with pytest.raises(KeyError): invoke(store, "attune_project_mode", {"mode": "preview"})
    with pytest.raises(ValueError): invoke(store, "attune_build", {"opportunity_id": "x", "owner": True})
    assert command(store, "project-mode " + p["id"] + " preview 2 1")["mode"] == "preview"


def test_competing_calls_execute_one_attempt_only(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ProjectLoop(store).execute(opp["id"]), range(2)))
    assert sum(r["status"] == "verified" for r in results) == 1
    assert {r["status"] for r in results} <= {"verified", "running", "already_verified"}
    with store.transaction() as db:
        assert db.execute("SELECT count(*) FROM builds").fetchone()[0] == 1
