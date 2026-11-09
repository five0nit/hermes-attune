"""Observation retains bounded idea history, not just rejected opportunities."""
from test_attune import env
from test_projects import project, learn, propose


def test_recent_ideas_distinguish_pending_verified_and_rejected(project):
    store, _, loop, p, _ = project
    learn(store, p["id"])
    first = propose(store, loop, p)
    assert loop.observe(p["id"])["recent"][0]["state"] == "proposed"
    loop.approve(first["id"])
    assert loop.execute(first["id"])["status"] == "verified"
    second = propose(store, loop, p, "quarterly")
    loop.feedback(second["id"], "revise")
    packet = loop.observe(p["id"])
    assert [(r["id"], r["state"]) for r in packet["recent"]] == [
        (second["id"], "rejected"), (first["id"], "verified")]
    assert [r["id"] for r in packet["rejected"]] == [second["id"]]
    assert "Historical" in packet["recent_state_scope"]
    for n in range(6):
        propose(store, loop, p, "different_" + str(n))
    recent = loop.observe(p["id"])["recent"]
    assert len(recent) == 5
    assert all(r["state"] == "proposed" for r in recent)
    result = loop.result(first["id"])
    assert result["status"] == "stale"  # Later rejection revoked the project's grant generation.
    assert result["historical_status"] == "verified"
