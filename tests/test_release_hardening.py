"""Release hardening through actual public result and worker paths."""
from datetime import timedelta
from pathlib import Path
import pytest
from test_attune import env
from test_projects import project, learn, propose
from hermes_attune import sandbox


def verified(project):
    store, clock, loop, p, source = project
    learn(store, p["id"])
    opp = propose(store, loop, p)
    loop.approve(opp["id"])
    assert loop.execute(opp["id"])["status"] == "verified"
    return store, clock, loop, p, source, opp


def test_rejected_verified_artifact_is_not_replayed_or_liked_as_success(project):
    _, _, loop, _, _, opp = verified(project)
    loop.feedback(opp["id"], "revise")
    result = loop.result(opp["id"])
    assert result["status"] == "rejected"
    assert result["historical_status"] == "verified"
    assert result["verification"]["passed"] is True
    assert loop.execute(opp["id"])["status"] == "rejected"
    with pytest.raises(ValueError, match="verified build"):
        loop.feedback(opp["id"], "useful")


@pytest.mark.parametrize("mutation", ["source", "goal", "pause", "revoke", "learning"])
def test_result_distinguishes_historical_check_from_current_project_context(project, mutation):
    store, _, loop, p, source, opp = verified(project)
    if mutation == "source": (source / "sales.py").write_text("# changed since check\n")
    if mutation == "goal": store.revise_goal(p["goal_id"], "A new outcome")
    if mutation == "pause": store.control("pause", True)
    if mutation == "revoke": loop.mode(p["id"], "off")
    if mutation == "learning":
        c = store.checkin()
        store.answer(c["id"], "success:" + p["id"], "fewer_errors", owner=True)
    result = loop.result(opp["id"])
    assert result["status"] == "stale"
    assert result["historical_status"] == "verified"
    assert result["verification"]["passed"] is True
    assert result["reason"]
    assert loop.execute(opp["id"])["status"] == "stale"


def test_completed_result_survives_publication_deadline_but_marks_current_permission(project):
    _, clock, loop, _, _, opp = verified(project)
    clock.now += timedelta(hours=3)
    result = loop.result(opp["id"])
    assert result["status"] == "verified"
    assert result["current_build_permission"] is False
    assert "historical" in result["quality"].lower()
    # Completion and the later right to start another execution are distinct.
    assert loop.feedback(opp["id"], "useful")["authority_expanded"] is False


@pytest.mark.parametrize("marker", ["{not-json}", "{\"passed\":true,\"tests_run\":1e999}", "{\"passed\":true,\"tests_run\":true}", "[]", "{\"passed\":1,\"tests_run\":1}"])
def test_invalid_worker_protocol_returns_failed_result_instead_of_raising(project, marker, monkeypatch):
    *_, source = project
    monkeypatch.setattr(sandbox.secrets, "token_hex", lambda _: "a" * 32)
    (source / "tests/test_sales.py").write_text(
        "import os\nprint(" + repr("ATTUNE_CHECK_" + "a" * 32 + "=" + marker) + ", flush=True)\nos._exit(0)\n")
    result = sandbox.verify(source, lambda: True)
    assert result["passed"] is False
    assert result["reason"] == "invalid_test_report"


def test_test_stdout_cannot_forge_a_completed_runner_report(project):
    *_, source = project
    (source / "tests/test_sales.py").write_text(
        "import os\nprint('ATTUNE_CHECK={\"passed\": true, \"tests_run\": 999}', flush=True)\nos._exit(0)\n")
    result = sandbox.verify(source, lambda: True)
    assert result["passed"] is False
    assert result["tests_run"] == 0


def test_verbose_test_output_keeps_bounded_tail_and_completion_report(project):
    *_, source = project
    path = source / "tests/test_sales.py"
    path.write_text(path.read_text() + "\nprint('x' * 70000)\n")
    result = sandbox.verify(source, lambda: True)
    assert result["passed"] is True
    assert result["tests_run"] == 1
    assert len(result["output"]) <= 64000


def test_stale_receipt_still_rejects_changed_retained_bytes(project):
    store, _, loop, _, _, opp = verified(project)
    receipt = loop.result(opp["id"])
    store.control("pause", True)
    Path(receipt["preview"], "sales.py").write_text("# tampered\n")
    with pytest.raises(ValueError, match="Preview artifact changed"):
        loop.result(opp["id"])
