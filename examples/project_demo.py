"""Executable fixture demo: scripted inputs, real plugin gates/builds/tests.

No provider calls, source-project edits, live profile changes or cron enrollment.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import sys

# Keep the source-checkout example runnable without an editable installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hermes_attune import command, invoke
from hermes_attune.core import Attune

BASE = "def revenue(values):\n    return sum(values)\n"
BASE_TEST = "import unittest\nfrom report import revenue\nclass TestRevenue(unittest.TestCase):\n    def test_total(self): self.assertEqual(revenue([2, 3]), 5)\n"
FEATURE = '''from decimal import Decimal
import csv
import io


def summarize_csv(content):
    rows = list(csv.DictReader(io.StringIO(content)))
    return {'orders': len(rows), 'revenue': str(sum((Decimal(r['amount']) for r in rows), Decimal('0')))}
'''
FEATURE_TEST = '''import json
from report import summarize_csv

class TestCsvSummary(unittest.TestCase):
    def test_report(self):
        actual = summarize_csv('product,amount\\nTea,12.50\\nCoffee,7.25\\nTea,5.00\\n')
        self.assertEqual(actual, {'orders': 3, 'revenue': '24.75'})
        print('ACTUAL_REPORT=' + json.dumps(actual))
    def test_empty(self):
        self.assertEqual(summarize_csv('product,amount\\n'), {'orders': 0, 'revenue': '0'})
    def test_bad_amount(self):
        self.assertRaises(Exception, summarize_csv, 'product,amount\\nTea,invalid\\n')
'''
GROUP_FEATURE = '''

def summarize_by_product(content):
    totals = {}
    for row in csv.DictReader(io.StringIO(content)):
        product = row['product']
        totals[product] = totals.get(product, Decimal('0')) + Decimal(row['amount'])
    return {product: str(amount) for product, amount in totals.items()}
'''
GROUP_TEST = '''from report import summarize_by_product

class TestProductSummary(unittest.TestCase):
    def test_product_totals(self):
        actual = summarize_by_product('product,amount\\nTea,12.50\\nCoffee,7.25\\nTea,5.00\\n')
        self.assertEqual(actual, {'Tea': '17.50', 'Coffee': '7.25'})
        print('ACTUAL_PRODUCTS=' + json.dumps(actual))
'''


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def run(output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Demo output must be absent or empty; preserve existing evidence")
    output.mkdir(parents=True, exist_ok=True)
    source = output / "selected-sales-project"
    (source / "tests").mkdir(parents=True)
    (source / "report.py").write_text(BASE)
    (source / "tests/test_report.py").write_text(BASE_TEST)
    baseline = hashes(source)
    now = [datetime(2026, 11, 8, 1, tzinfo=timezone.utc)]
    store = Attune(output / "fixture-profile", lambda: now[0])
    goal = command(store, 'goal "Stop manual sales reporting" "An accurate repeatable CSV summary"')
    project = command(store, f'project-add "Sales tool" "{source}" {goal["id"]} "report.py,tests/test_report.py,README.md"')
    checkins = []
    for _ in range(3):
        c = invoke(store, "attune_checkin", {})
        checkins.append(c)
        for question in c.get("questions", []):
            choice = {"format": "steps", "friction:": "repetition", "success:": "time_saved", "initiative:": "surprise_previews", "project_daily:": "keep_focus"}
            selected = next((v for k, v in choice.items() if question["kind"].startswith(k)), question["choices"][0])
            invoke(store, "attune_answer", {"checkin_id": c["id"], "question_id": question["id"], "choice": selected})
    packet = invoke(store, "attune_project", {"project_id": project["id"]})
    assert packet["permission"]["mode"] == "suggest", "Preference must never silently grant preview permission"
    changed = {"report.py": BASE + "\n" + FEATURE, "tests/test_report.py": BASE_TEST + "\n" + FEATURE_TEST}
    opp = invoke(store, "attune_propose", {"project_id": project["id"], "title": "Replace repeated manual totals with a CSV summary", "rationale": "Daily answer identifies repetition; success asks for time saved. Preserve the old total function and add a tested accurate CSV report.", "category": "repetition", "changes_json": json.dumps(changed)})
    before_approval = invoke(store, "attune_build", {"opportunity_id": opp["id"]})
    assert before_approval["status"] == "needs_approval"
    approval = command(store, "approve " + opp["id"])
    first = invoke(store, "attune_build", {"opportunity_id": opp["id"]})
    assert first["status"] == "verified", first
    assert first["verification"]["tests_run"] == 4
    useful = command(store, "build-feedback " + opp["id"] + " useful")
    now[0] += timedelta(days=1)
    daily = invoke(store, "attune_checkin", {})
    checkins.append(daily)
    for q in daily.get("questions", []):
        if q["kind"].startswith("project_daily:"):
            invoke(store, "attune_answer", {"checkin_id": daily["id"], "question_id": q["id"], "choice": "keep_focus"})
    grant = command(store, "project-mode " + project["id"] + " preview 2 1")
    recent = invoke(store, "attune_project", {"project_id": project["id"]})["recent"]
    assert recent[0]["id"] == opp["id"] and recent[0]["state"] == "verified"
    changed["report.py"] += GROUP_FEATURE
    changed["tests/test_report.py"] += GROUP_TEST
    changed["README.md"] = "# Sales summary preview\nUse summarize_csv for decimal totals; summarize_by_product for the product breakdown.\n"
    second_opp = invoke(store, "attune_propose", {"project_id": project["id"], "title": "Add a per-product sales breakdown", "rationale": "Daily repetition/time-saved answers support eliminating another manual reporting step: group and total product sales. Preserve the first feature and add an actual new capability with a test.", "category": "repetition", "changes_json": json.dumps(changed)})
    second = invoke(store, "attune_build", {"opportunity_id": second_opp["id"]})
    assert second["status"] == "verified", second
    assert second["verification"]["tests_run"] == 5
    rejected = command(store, "build-feedback " + second_opp["id"] + " revise")
    correction = invoke(store, "attune_checkin", {})
    duplicate = None
    try:
        invoke(store, "attune_propose", {"project_id": project["id"], "title": "Same changes with new words", "rationale": "This must be suppressed", "category": "repetition", "changes_json": json.dumps(changed)})
    except ValueError as exc:
        duplicate = str(exc)
    assert duplicate and "Duplicate" in duplicate
    assert hashes(source) == baseline
    actual = next(json.loads(line.split("=", 1)[1]) for line in first["verification"]["output"].splitlines() if line.startswith("ACTUAL_REPORT="))
    products = next(json.loads(line.split("=", 1)[1]) for line in second["verification"]["output"].splitlines() if line.startswith("ACTUAL_PRODUCTS="))
    report = {"disclosure": "Scripted fixture answers/source proposals and controlled clock; real SQLite, permission gates, Linux isolated execution and retained previews. Not live AI quality or elapsed-day evidence.",
              "version": "0.3.1", "checkins": checkins, "learned": packet["learned"], "proposal": opp, "before_approval": before_approval, "approval": approval,
              "approved_build": first, "actual_computed_report": actual, "actual_product_report": products, "useful_feedback": useful, "standing_grant": grant, "standing_build": second,
              "negative_feedback": rejected, "correction": correction, "duplicate_suppression": duplicate, "source_unchanged": True,
              "projects_after_rejection": invoke(store, "attune_projects", {}), "restarted_readback": invoke(Attune(store.root, lambda: now[0]), "attune_build_result", {"opportunity_id": opp["id"]})}
    (output / "demo.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"demo": str(output / "demo.json"), "approved_build": first["status"], "standing_build": second["status"], "tests_by_build": [first["verification"]["tests_run"], second["verification"]["tests_run"]], "actual_report": actual, "actual_products": products, "source_unchanged": True, "post_rejection_mode": report["projects_after_rejection"][0]["mode"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run(args.output.absolute() if args.output else Path(tempfile.mkdtemp(prefix="attune-project-demo-")))
