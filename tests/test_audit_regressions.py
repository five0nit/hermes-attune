"""Audit-loop regressions; use controlled clocks and isolated profile state."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from test_attune import env, ready, draft
from hermes_attune import core


@pytest.mark.parametrize("zone,midnight", [("UTC", False), ("UTC", True), ("Australia/Melbourne", True)])
def test_publication_rechecks_expiry_after_staging_io(env, monkeypatch, zone, midnight):
    store, clock = env
    store.control("timezone", zone)
    if midnight:
        clock.now = datetime(2026, 11, 6, 23, 59, tzinfo=ZoneInfo(zone)).astimezone(timezone.utc)
    packet = ready(store)
    sync = core.os.fsync

    def delayed_sync(fd):
        sync(fd)
        clock.now += timedelta(minutes=2) if midnight else timedelta(hours=3)

    with monkeypatch.context() as patch:
        patch.setattr(core.os, "fsync", delayed_sync)
        with pytest.raises(ValueError, match="expired|closed"):
            store.deliver(packet["id"], draft(packet))
    assert not list(store.root.glob("draft-*.md"))
    assert not list(store.root.glob(".draft-*.tmp"))
    assert store.status()["runs"][0]["state"] == "running"
    if midnight:
        current = store.work()
        assert current["id"] != packet["id"]
        assert store.deliver(current["id"], draft(current))["status"] == "verified"
        assert store.work()["status"] == "daily_cap"
    else:
        assert store.work()["status"] == "daily_cap"
