"""Transactional calibration, not an agent engine. All times are UTC internally."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid
from zoneinfo import ZoneInfo
from typing import Any

UTC = timezone.utc
VERSION = "0.3.1"


def text(value, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Expected nonempty text, at most {limit} characters")
    return value.strip()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class Attune:
    def __init__(self, root, clock=None):
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError("State root must not be a symlink")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.db = self.root / "attune.db"
        if self.db.is_symlink():
            raise ValueError("Database must not be a symlink")
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'").fetchone():
                if self.setting(db, "schema") != 1:
                    raise ValueError("Unsupported state schema; preserve database")
            # executescript commits an open transaction before running DDL.
            # Keep initialization and the schema guard under the writer lock.
            statements = """
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS goals(
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, success TEXT NOT NULL,
                    material TEXT NOT NULL, state TEXT NOT NULL, priority INTEGER NOT NULL,
                    revision INTEGER NOT NULL, changed TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS preferences(
                    key TEXT PRIMARY KEY, value TEXT NOT NULL, expires TEXT,
                    source TEXT NOT NULL, changed TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS focus_overrides(
                    goal_id TEXT PRIMARY KEY, state TEXT NOT NULL, priority INTEGER NOT NULL,
                    applied_revision INTEGER NOT NULL, expires TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS checkins(
                    id TEXT PRIMARY KEY, day TEXT UNIQUE NOT NULL, questions TEXT NOT NULL,
                    created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS answers(
                    checkin_id TEXT NOT NULL, question_id TEXT NOT NULL,
                    choice TEXT NOT NULL, scope TEXT NOT NULL, source TEXT NOT NULL,
                    changed TEXT NOT NULL, PRIMARY KEY(checkin_id, question_id));
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    day TEXT NOT NULL, state TEXT NOT NULL, contract TEXT NOT NULL,
                    created TEXT NOT NULL, expires TEXT NOT NULL, path TEXT, digest TEXT,
                    feedback TEXT, UNIQUE(goal_id, revision, day));
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL, created TEXT NOT NULL);
            """
            for statement in statements.split(";"):
                if statement.strip():
                    db.execute(statement)
            db.execute("INSERT OR IGNORE INTO settings VALUES('schema', '1')")
            if self.setting(db, "schema") != 1:
                raise ValueError("Unsupported state schema; preserve database")

            from .projects import initialize
            initialize(db)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.db, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def now(self):
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("Clock must be timezone-aware")
        return now.astimezone(UTC)

    def stamp(self):
        return self.now().isoformat()

    @staticmethod
    def setting(db, key, default=None) -> Any:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    @staticmethod
    def put(db, key, value):
        db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, encode(value)))

    def event(self, db, kind, data):
        db.execute("INSERT INTO events(kind,data,created) VALUES(?,?,?)", (kind, encode(data), self.stamp()))

    def day(self, db):
        return self.now().astimezone(ZoneInfo(self.setting(db, "timezone", "UTC"))).date().isoformat()

    def midnight(self, db):
        zone = ZoneInfo(self.setting(db, "timezone", "UTC"))
        return (self.now().astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1)).astimezone(UTC).isoformat()

    def expire_focus(self, db):
        for row in db.execute("SELECT * FROM focus_overrides WHERE expires<=?", (self.stamp(),)).fetchall():
            db.execute("UPDATE goals SET state=?,priority=?,revision=revision+1,changed=? WHERE id=? AND revision=?",
                       (row["state"], row["priority"], self.stamp(), row["goal_id"], row["applied_revision"]))
            db.execute("DELETE FROM focus_overrides WHERE goal_id=?", (row["goal_id"],))

    def control(self, action, value=None):
        """Owner-only entry: never registered as a model tool."""
        allowed = {"routine", "pause", "questions", "snooze", "timezone", "interval"}
        if action not in allowed:
            raise ValueError("Unknown control")
        if action in {"routine", "pause", "questions"} and type(value) is not bool:
            raise ValueError("Control requires a boolean")
        if action == "timezone":
            ZoneInfo(text(value, 80))
        if action == "interval" and (type(value) is not int or not 1 <= value <= 30):
            raise ValueError("Interval must be 1–30 days")
        if action == "snooze":
            if type(value) is not int or not 1 <= value <= 30:
                raise ValueError("Snooze must be 1–30 days")
            value = (self.now() + timedelta(days=value)).isoformat()
        with self.transaction() as db:
            self.put(db, action, value)
            self.event(db, "owner_control", {"action": action, "value": value})
        return {"changed": action, "value": value,
                "boundary": "Local drafts only; no sending, spending, account edits or CCT leases"}

    def goal(self, title, success, material="", owner=False):
        title, success = text(title, 240), text(success, 1200)
        if not isinstance(material, str) or len(material) > 12000:
            raise ValueError("Material must be text, at most 12000 characters")
        with self.transaction() as db:
            old = db.execute("SELECT * FROM goals WHERE title=? AND state!='dropped'", (title,)).fetchone()
            if old:
                if (old["success"], old["material"]) != (success, material):
                    raise ValueError("Goal exists with different criteria; use a new specific title")
                return dict(old)
            if db.execute("SELECT count(*) FROM goals").fetchone()[0] >= 100:
                raise ValueError("Goal limit reached (100)")
            ident = uuid.uuid4().hex[:12]
            db.execute("INSERT INTO goals VALUES(?,?,?,?,?,?,?,?)",
                       (ident, title, success, material, "active" if owner else "proposed", 50, 1, self.stamp()))
            self.event(db, "goal_created", {"goal_id": ident, "source": "owner" if owner else "conversation_report"})
            return dict(db.execute("SELECT * FROM goals WHERE id=?", (ident,)).fetchone())

    def revise_goal(self, goal_id, success, material=None):
        """Explicit owner correction; model proposals cannot overwrite a goal."""
        success = text(success, 1200)
        if material is not None and (not isinstance(material, str) or len(material) > 12000):
            raise ValueError("Material must be text, at most 12000 characters")
        with self.transaction() as db:
            self.expire_focus(db)
            goal = db.execute("SELECT * FROM goals WHERE id=?", (text(goal_id, 32),)).fetchone()
            if not goal:
                raise ValueError("Unknown goal")
            material = goal["material"] if material is None else material
            if (success, material) != (goal["success"], goal["material"]):
                db.execute("UPDATE goals SET success=?,material=?,revision=revision+1,changed=? WHERE id=?",
                           (success, material, self.stamp(), goal_id))
                db.execute("UPDATE focus_overrides SET applied_revision=? WHERE goal_id=?",
                           (goal["revision"]+1, goal_id))
                self.event(db, "owner_goal_updated", {"goal_id": goal_id})
            return dict(db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone())

    def set_goal_state(self, goal_id, state):
        """Owner lifecycle control, deliberately absent from the tool registry."""
        if state not in {"active", "waiting", "done", "dropped"}:
            raise ValueError("Invalid goal state")
        with self.transaction() as db:
            self.expire_focus(db)
            goal = db.execute("SELECT * FROM goals WHERE id=?", (text(goal_id, 32),)).fetchone()
            if not goal:
                raise ValueError("Unknown goal")
            if goal["state"] != state or db.execute("SELECT 1 FROM focus_overrides WHERE goal_id=?", (goal_id,)).fetchone():
                db.execute("DELETE FROM focus_overrides WHERE goal_id=?", (goal_id,))
                db.execute("UPDATE goals SET state=?,revision=revision+1,changed=? WHERE id=?", (state, self.stamp(), goal_id))
                self.event(db, "owner_goal_state", {"goal_id": goal_id, "state": state})
            return dict(db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone())

    def preferences(self, db):
        rows = db.execute("SELECT * FROM preferences WHERE expires IS NULL OR expires>?", (self.stamp(),)).fetchall()
        values = {r["key"]: r["value"] for r in rows if not r["key"].endswith("@today")}
        values.update({r["key"][:-6]: r["value"] for r in rows if r["key"].endswith("@today")})
        return values

    @staticmethod
    def feedback_events(db):
        return (json.loads(row[0]) for row in db.execute(
            "SELECT data FROM events WHERE kind='owner_feedback' ORDER BY id DESC"))

    def unresolved_corrections(self, db):
        seen = set()
        for feedback in self.feedback_events(db):
            run = db.execute("SELECT g.id,g.title,g.state,r.feedback FROM runs r JOIN goals g ON g.id=r.goal_id WHERE r.id=?",
                             (feedback["run_id"],)).fetchone()
            if not run or run["id"] in seen:
                continue
            seen.add(run["id"])
            if feedback["rating"] == "revise" and run["feedback"] == "revise" and run["state"] == "active":
                yield {"id": "correction", "kind": "correction", "goal_id": run["id"], "run_id": feedback["run_id"],
                       "text": f"The draft for ‘{run['title']}’ missed. What should change?",
                       "choices": ["shorter", "more_evidence", "more_specific"]}

    def correction_question(self, db):
        prefs = self.preferences(db)
        for question in self.unresolved_corrections(db):
            if "correction:"+question["goal_id"] not in prefs and "correction" not in prefs:
                return question
        return None

    def checkin(self):
        with self.transaction() as db:
            self.expire_focus(db)
            if self.setting(db, "pause", False) or not self.setting(db, "questions", True):
                return {"status": "paused", "questions": []}
            if self.setting(db, "snooze", "") > self.stamp():
                return {"status": "snoozed", "questions": []}
            day = self.day(db)
            correction = self.correction_question(db)
            existing = db.execute("SELECT * FROM checkins WHERE day=?", (day,)).fetchone()

            last = db.execute("SELECT day FROM checkins ORDER BY created DESC LIMIT 1").fetchone()
            if not existing and not correction and last and (datetime.fromisoformat(day)-datetime.fromisoformat(last[0])).days < int(self.setting(db, "interval", 1)):
                return {"status": "not_due", "questions": []}
            goals = [dict(r) for r in db.execute("SELECT * FROM goals WHERE state IN ('active','proposed','waiting') ORDER BY priority DESC,changed,rowid")]
            prefs = self.preferences(db)
            questions = []
            from .projects import ProjectLoop
            project_questions = ProjectLoop(self).questions(db)
            active_projects = {r[0] for r in db.execute("SELECT p.id FROM projects p JOIN goals g ON g.id=p.goal_id WHERE p.mode!='off' AND g.state='active'")}
            if goals:
                focus = next((g for g in goals if g["state"] == "proposed"), None)
                stale = next((g for g in goals if self.now()-datetime.fromisoformat(g["changed"]) >= timedelta(days=7)), None)
                if focus or stale:
                    g = focus or stale
                    questions.append({"id": "focus-"+g["id"], "kind": "focus", "goal_id": g["id"], "revision": g["revision"],
                                      "text": f"Where should ‘{g['title']}’ sit now?", "choices": ["now", "later", "drop"]})
                if "format" not in prefs:
                    questions.append({"id": "format", "kind": "format", "text": "What would make the next output most useful?",
                                      "choices": ["recommendation", "comparison", "steps"]})
                if correction:
                    questions.insert(0, correction)
                questions.extend(project_questions)
                questions.sort(key=lambda q: not q["kind"].startswith("project_correction:"))
            else:
                return {"status": "needs_goal", "questions": [], "next": "Tell Hermes one outcome and what would count as success"}
            if existing:
                # Refresh mutable focus questions and new proposals, retaining
                # valid answered questions for deliberate same-day corrections.
                old_questions = json.loads(existing["questions"])
                old_correction = next((q for q in old_questions if q["kind"] == "correction"), None)
                if correction and old_correction and correction["run_id"] != old_correction["run_id"]:
                    # A pending reply must never silently target a different run.
                    ident = uuid.uuid4().hex[:12]
                    db.execute("UPDATE answers SET checkin_id=? WHERE checkin_id=?", (ident, existing["id"]))
                    db.execute("UPDATE checkins SET id=? WHERE id=?", (ident, existing["id"]))
                    existing = {**dict(existing), "id": ident}
                unresolved = {q["run_id"] for q in self.unresolved_corrections(db)}
                current = {g["id"]: g for g in goals}
                for q in old_questions:
                    if q["id"] in {q["id"] for q in questions}:
                        continue
                    if q.get("project_id") and q["project_id"] not in active_projects:
                        continue
                    if q["kind"].startswith("project_correction:"):
                        continue  # Current rejection already supplied a uniquely bound question.
                    if q["kind"] == "focus":
                        g = current.get(q["goal_id"])
                        if not g or g["revision"] != q["revision"]:
                            continue
                    if q["kind"] == "correction" and q.get("run_id") not in unresolved:
                        continue
                    questions.append(q)
                questions = questions[:3]
                previous = {q["id"]: q for q in old_questions}
                for q in questions:
                    if previous.get(q["id"]) != q:
                        db.execute("DELETE FROM answers WHERE checkin_id=? AND question_id=?", (existing["id"], q["id"]))
                db.execute("UPDATE checkins SET questions=? WHERE id=?", (encode(questions), existing["id"]))
                answered = {r[0] for r in db.execute("SELECT question_id FROM answers WHERE checkin_id=?", (existing["id"],))}
                return {"status": "existing", "id": existing["id"], "questions": [q for q in questions if q["id"] not in answered]}
            if not questions:
                return {"status": "nothing_to_ask", "questions": [], "next": "Known answers reused; continue permitted work"}
            ident = uuid.uuid4().hex[:12]
            questions = questions[:3]
            db.execute("INSERT INTO checkins VALUES(?,?,?,?)", (ident, day, encode(questions), self.stamp()))
            self.event(db, "checkin_created", {"id": ident, "question_count": len(questions)})
            return {"status": "new", "id": ident, "questions": questions}

    def answer(self, checkin_id, question_id, choice, scope="standing", owner=False):
        if scope not in {"today", "standing"}:
            raise ValueError("Scope must be today or standing")
        with self.transaction() as db:
            self.expire_focus(db)
            row = db.execute("SELECT * FROM checkins WHERE id=?", (text(checkin_id, 32),)).fetchone()
            if not row or self.now()-datetime.fromisoformat(row["created"]) > timedelta(days=2):
                raise ValueError("Unknown or expired check-in")
            if scope == "today" and row["day"] != self.day(db):
                raise ValueError("Today-only question expired at local midnight")
            q = next((q for q in json.loads(row["questions"]) if q["id"] == question_id), None)
            if not q or choice not in q["choices"]:
                raise ValueError("Answer must match the exact question and an offered choice")
            if q.get("project_id"):
                project = db.execute("SELECT p.* FROM projects p JOIN goals g ON g.id=p.goal_id WHERE p.id=? AND p.mode!='off' AND g.state='active'", (q["project_id"],)).fetchone()
                if not project:
                    raise ValueError("Project question is stale or observation revoked")
                if q["kind"].startswith("project_correction:"):
                    rejection = db.execute("SELECT id FROM opportunities WHERE project_id=? AND state='rejected' ORDER BY rowid DESC LIMIT 1", (q["project_id"],)).fetchone()
                    if not rejection or rejection["id"] != q.get("opportunity_id"):
                        raise ValueError("Project correction is stale; later feedback superseded it")
                if q["kind"].startswith("project_daily:"):
                    if row["day"] != self.day(db):
                        raise ValueError("Daily project question expired at local midnight")
                    scope = "today"
            if db.execute("SELECT 1 FROM answers a JOIN checkins c ON c.id=a.checkin_id WHERE a.question_id=? AND c.day>? LIMIT 1",
                          (question_id, row["day"])).fetchone():
                raise ValueError("Question is stale; a newer daily answer exists")
            if q["kind"] == "correction" and not any(current["run_id"] == q.get("run_id") for current in self.unresolved_corrections(db)):
                raise ValueError("Correction is stale; later feedback resolved it")
            old = db.execute("SELECT * FROM answers WHERE checkin_id=? AND question_id=?", (checkin_id, question_id)).fetchone()
            if q["kind"] == "focus":
                g = db.execute("SELECT * FROM goals WHERE id=?", (q["goal_id"],)).fetchone()
                if not g or g["revision"] != q["revision"]:
                    raise ValueError("Goal changed; this focus question is stale")
            if old and (old["choice"], old["scope"]) == (choice, scope):
                return {"status": "already_recorded", "learned": choice, "authority_changed": False}
            if q["kind"].startswith("project_daily:") and choice == "change_friction":
                key = "friction:" + q["project_id"]
                db.execute("DELETE FROM preferences WHERE key IN (?,?)", (key, key + "@today"))
                db.execute("DELETE FROM answers WHERE checkin_id=? AND question_id=?", (checkin_id, key))
            if q["kind"] == "focus":
                if scope == "today":
                    base = db.execute("SELECT * FROM focus_overrides WHERE goal_id=?", (g["id"],)).fetchone() or g
                    db.execute("INSERT OR REPLACE INTO focus_overrides VALUES(?,?,?,?,?)",
                               (g["id"], base["state"], base["priority"], g["revision"]+1, self.midnight(db)))
                else:
                    db.execute("DELETE FROM focus_overrides WHERE goal_id=?", (g["id"],))
                db.execute("UPDATE goals SET state=?,priority=?,revision=revision+1,changed=? WHERE id=?",
                           ({"now": "active", "later": "waiting", "drop": "dropped"}[choice], 90 if choice == "now" else 10, self.stamp(), g["id"]))
                questions = json.loads(row["questions"])
                next(q for q in questions if q["id"] == question_id)["revision"] = g["revision"]+1
                db.execute("UPDATE checkins SET questions=? WHERE id=?", (encode(questions), checkin_id))
            else:
                expires = self.midnight(db) if scope == "today" else None
                preference = "correction:"+q["goal_id"] if q["kind"] == "correction" and "goal_id" in q else q["kind"]
                key = preference + ("@today" if scope == "today" else "")
                if scope == "standing":
                    db.execute("DELETE FROM preferences WHERE key=?", (preference+"@today",))
                db.execute("INSERT OR REPLACE INTO preferences VALUES(?,?,?,?,?)", (key, choice, expires, "owner" if owner else "conversation_report", self.stamp()))
            db.execute("INSERT OR REPLACE INTO answers VALUES(?,?,?,?,?,?)", (checkin_id, question_id, choice, scope, "owner" if owner else "conversation_report", self.stamp()))
            self.event(db, "answer_applied", {"checkin_id": checkin_id, "question_id": question_id, "choice": choice, "scope": scope})
            return {"status": "learned", "learned": choice, "changed": "goal ranking" if q["kind"] == "focus" else "output contract", "authority_changed": False,
                    "next": "Use the updated work packet; existing permitted work continues"}

    def capacity(self, db):
        useful = set()
        for feedback in self.feedback_events(db):
            if feedback["rating"] != "useful":
                break
            run = db.execute("SELECT digest FROM runs WHERE id=? AND state='verified'", (feedback["run_id"],)).fetchone()
            if run and run["digest"]:
                useful.add(run["digest"])
            if len(useful) == 6:
                break
        return min(3, 1 + len(useful) // 3)

    def output_contract(self, db, goal):
        prefs = self.preferences(db)
        shape = prefs.get("format", "recommendation")
        headings = {"recommendation": ["Recommendation", "Why", "Next step"], "comparison": ["Options", "Trade-offs", "Recommendation"], "steps": ["Outcome", "Steps", "Done when"]}[shape]
        return {"goal": goal["title"], "success": goal["success"], "material": goal["material"], "format": shape, "required_headings": headings,
                "correction": prefs.get("correction:"+goal["id"], prefs.get("correction")), "boundary": "Draft only. Use supplied material. Mark missing facts. No web/account access, sending, spending or execution.",
                "preference_source": "Stored explicit fields; conversation-reported answers are not permission"}

    def work(self):
        with self.transaction() as db:
            self.expire_focus(db)
            if self.setting(db, "pause", False):
                return {"status": "paused"}
            if not self.setting(db, "routine", False):
                return {"status": "needs_consent", "next": "Owner: /attune routine on permits plugin-local drafting, capped at 3 drafts/day"}
            day, now = self.day(db), self.stamp()
            db.execute("UPDATE runs SET state='expired' WHERE state='running' AND (expires<=? OR day!=?)", (now, day))
            for running in db.execute("SELECT * FROM runs WHERE day=? AND state='running' ORDER BY created", (day,)).fetchall():
                g = db.execute("SELECT * FROM goals WHERE id=?", (running["goal_id"],)).fetchone()
                if g and g["state"] == "active" and g["revision"] == running["revision"] and json.loads(running["contract"]) == self.output_contract(db, g):
                    return {"status": "resume", **dict(running), "contract": json.loads(running["contract"])}
                db.execute("UPDATE runs SET state='superseded' WHERE id=?", (running["id"],))
                self.event(db, "work_superseded", {"run_id": running["id"], "reason": "goal_or_output_contract_changed"})
            reusable = db.execute("SELECT * FROM runs WHERE day=? AND state='superseded' ORDER BY created LIMIT 1", (day,)).fetchone()
            cap = self.capacity(db)
            used = db.execute("SELECT count(*) FROM runs WHERE day=?", (day,)).fetchone()[0]
            if used >= cap and not reusable:
                return {"status": "daily_cap", "used": used, "cap": cap}
            candidates = db.execute("SELECT * FROM goals WHERE state='active' AND id NOT IN (SELECT goal_id FROM runs WHERE day=? AND state!='superseded') ORDER BY priority DESC,changed,rowid", (day,)).fetchall()
            g = next((goal for goal in candidates if not db.execute(
                "SELECT 1 FROM runs WHERE goal_id=? AND state='verified' AND contract=? AND (feedback IS NULL OR feedback!='revise') LIMIT 1",
                (goal["id"], encode(self.output_contract(db, goal)))).fetchone()), None)
            if not g:
                if candidates:
                    return {"status": "awaiting_update", "next": "Existing outputs cover these contracts. Review them, complete a goal, or supply changed criteria/material with /attune update. No repeated draft created."}
                return {"status": "nothing_ready"}
            contract = self.output_contract(db, g)
            ident = uuid.uuid4().hex[:16]
            expires = min((self.now()+timedelta(hours=2)).isoformat(), self.midnight(db))
            if reusable:
                reusable = db.execute("SELECT * FROM runs WHERE day=? AND state='superseded' ORDER BY (goal_id=? AND revision=?) DESC,created LIMIT 1",
                                      (day, g["id"], g["revision"])).fetchone()
                db.execute("UPDATE runs SET id=?,goal_id=?,revision=?,state='running',contract=?,created=?,expires=? WHERE id=?",
                           (ident, g["id"], g["revision"], encode(contract), now, expires, reusable["id"]))
            else:
                db.execute("INSERT INTO runs(id,goal_id,revision,day,state,contract,created,expires) VALUES(?,?,?,?,?,?,?,?)",
                           (ident, g["id"], g["revision"], day, "running", encode(contract), now, expires))
            self.event(db, "work_claimed", {"run_id": ident, "goal_id": g["id"], "cap": cap,
                                             "replaces": reusable["id"] if reusable else None})
            return {"status": "ready", "id": ident, "contract": contract, "cap": cap}

    def deliver(self, run_id, content):
        content = text(content, 48000)
        if len(content) < 80:
            raise ValueError("Draft too short (minimum 80 characters)")
        blob = (content+"\n").encode()
        digest = hashlib.sha256(blob).hexdigest()
        with self.transaction() as db:
            self.expire_focus(db)
            run = db.execute("SELECT * FROM runs WHERE id=?", (text(run_id, 32),)).fetchone()
            if not run:
                raise ValueError("Unknown run")
            if run["state"] == "verified":
                if run["digest"] != digest:
                    raise ValueError("Run already delivered different content")
                path = self.root / run["path"]
                if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("Delivered artifact no longer matches its receipt")
                return {"status": "already_verified", "id": run_id, "path": str(path), "sha256": digest}
            if run["state"] != "running" or run["expires"] <= self.stamp() or run["day"] != self.day(db):
                raise ValueError("Run expired or closed")
            if self.setting(db, "pause", False) or not self.setting(db, "routine", False):
                raise ValueError("Draft permission is paused or revoked")
            g = db.execute("SELECT * FROM goals WHERE id=?", (run["goal_id"],)).fetchone()
            if g["state"] != "active" or g["revision"] != run["revision"]:
                raise ValueError("Goal changed after work was claimed")
            contract = json.loads(run["contract"])
            if contract != self.output_contract(db, g):
                raise ValueError("Output contract changed after work was claimed")
            if db.execute("SELECT count(*) FROM runs WHERE day=? AND state='verified'", (run["day"],)).fetchone()[0] >= self.capacity(db):
                raise ValueError("Daily draft capacity reached")
            for heading in contract["required_headings"]:
                if "## "+heading not in content.splitlines():
                    raise ValueError("Draft missing required heading: "+heading)
            if db.execute("SELECT 1 FROM runs WHERE state='verified' AND digest=? AND id!=?", (digest, run_id)).fetchone():
                raise ValueError("Duplicate draft already verified; incorporate the changed needs instead of repeating it")
            name = "draft-"+run_id+".md"
            path = self.root / name
            # Publish complete bytes without replacing any existing artifact.
            # An interrupted staging write must not poison the stable run path.
            fd, staged_name = tempfile.mkstemp(prefix=".draft-", suffix=".tmp", dir=self.root)
            staged = Path(staged_name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(blob)
                    stream.flush()
                    os.fsync(stream.fileno())
                if staged.read_bytes() != blob:
                    raise ValueError("Artifact staging readback mismatch")
                # Staging I/O may cross the claim's deadline or local midnight.
                if run["expires"] <= self.stamp() or run["day"] != self.day(db):
                    raise ValueError("Run expired or closed before publication")
                try:
                    os.link(staged, path)
                except FileExistsError:
                    if path.is_symlink() or not path.is_file() or path.read_bytes() != blob:
                        raise ValueError("Existing artifact conflicts; preserved") from None
            finally:
                staged.unlink(missing_ok=True)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Artifact readback mismatch")
            db.execute("UPDATE runs SET state='verified',path=?,digest=? WHERE id=?", (name, digest, run_id))
            self.event(db, "artifact_verified", {"run_id": run_id, "sha256": digest, "bytes": len(blob)})
            return {"status": "verified", "id": run_id, "path": str(path), "sha256": digest, "bytes": len(blob),
                    "quality": "Not yet rated by owner; verification proves file and format, not factual correctness or task success"}

    def feedback(self, run_id, rating):
        """Owner-only quality feedback. File existence is not user acceptance."""
        if rating not in {"useful", "revise"}:
            raise ValueError("Rating must be useful or revise")
        with self.transaction() as db:
            self.expire_focus(db)
            run = db.execute("SELECT * FROM runs WHERE id=?", (text(run_id, 32),)).fetchone()
            if not run or run["state"] != "verified":
                raise ValueError("Feedback requires a verified artifact")
            path = self.root / run["path"]
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != run["digest"]:
                raise ValueError("Artifact changed; quality feedback not accepted")
            if run["feedback"] != rating:
                db.execute("UPDATE runs SET feedback=? WHERE id=?", (rating, run_id))
                if rating == "revise":
                    self.put(db, "routine", False)
                    db.execute("DELETE FROM preferences WHERE key IN ('correction','correction@today',?,?)",
                               ("correction:"+run["goal_id"], "correction:"+run["goal_id"]+"@today"))
                self.event(db, "owner_feedback", {"run_id": run_id, "rating": rating})
            return {"learned": rating, "routine_enabled": self.setting(db, "routine", False), "drafts_per_day": self.capacity(db), "authority_expanded": False}

    def status(self):
        with self.transaction() as db:
            self.expire_focus(db)
            return {"version": VERSION, "data_dir": str(self.root.resolve()), "goals": [dict(r) for r in db.execute("SELECT id,title,success,state,priority,revision FROM goals ORDER BY priority DESC,id")],
                    "preferences": self.preferences(db), "routine_enabled": self.setting(db, "routine", False), "paused": self.setting(db, "pause", False),
                    "drafts_per_day": self.capacity(db), "timezone": self.setting(db, "timezone", "UTC"),
                    "questions": self.setting(db, "questions", True), "snooze": self.setting(db, "snooze"), "interval": self.setting(db, "interval", 1),
                    "schedule": self.setting(db, "schedule"), "schedule_error": self.setting(db, "schedule_error"), "schedule_live_verified": False,
                    "runs": [dict(r) for r in db.execute("SELECT id,goal_id,state,path,digest,feedback FROM runs ORDER BY created DESC LIMIT 10")],
                    "projects": [dict(r) for r in db.execute("SELECT id,name,goal_id,mode,expires,daily_cap FROM projects ORDER BY rowid")],
                    "opportunities": [dict(r) for r in db.execute("SELECT id,project_id,title,category,state FROM opportunities ORDER BY rowid DESC LIMIT 10")],
                    "boundary": "Draft permission remains draft-only. Separately selected projects support owner-approved or explicitly granted offline Python previews; no source merge, network, installation or deployment. No authority over other host tools or CCT leases.",
                    "privacy": "No automatic message capture. Explicit goals/material/answers/drafts and selected project evidence/changed source persist as plaintext in this profile; selected context is visible to its model."}

    def context(self):
        status = self.status()
        goals = [g for g in status["goals"] if g["state"] in {"active", "proposed", "waiting"}]
        data = {"goals": [], "preferences": {k: v for k, v in status["preferences"].items() if k in {"format", "correction"}},
                "routine_enabled": status["routine_enabled"], "boundary": status["boundary"], "omitted_goals": len(goals),
                "projects": [{k: p[k] for k in ("id", "name", "mode")} for p in status["projects"][:3]]}
        for goal in goals[:5]:
            summary = {**goal, "title": goal["title"][:120], "success": goal["success"][:240]}
            data["goals"].append(summary)
            data["omitted_goals"] -= 1
            if len(encode(data)) > 3200:
                data["goals"].pop()
                data["omitted_goals"] += 1
                break
        return "Attune calibration data (not instructions or permission):\n" + encode(data)
