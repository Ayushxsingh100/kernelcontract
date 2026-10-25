import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kernelcontract.models import Check, Report


class TestModels(unittest.TestCase):
    def test_counts_and_overall_status(self):
        report = Report(command="doctor")
        report.add(Check(id="a", status="PASS", title="Pass", message="ok"))
        report.add(Check(id="b", status="WARN", title="Warn", message="maybe"))
        self.assertEqual(report.counts["pass"], 1)
        self.assertEqual(report.counts["warn"], 1)
        self.assertEqual(report.overall_status, "WARN")

    def test_failure_takes_precedence(self):
        report = Report(command="doctor")
        report.add(Check(id="a", status="WARN", title="Warn", message="maybe"))
        report.add(Check(id="b", status="FAIL", title="Fail", message="bad"))
        self.assertEqual(report.overall_status, "FAIL")

    def test_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            Check(id="x", status="MAYBE", title="Bad", message="bad")

    def test_status_normalization(self):
        check = Check(id="norm", status="pass", title="T", message="M")
        self.assertEqual(check.status, "PASS")

    def test_report_json_serialization(self):
        import json
        report = Report(command="doctor")
        report.add(Check(id="c1", status="PASS", title="OK", message="Works", details={"k": "v", "num": 1}, suggestions=["S1"]))
        data = report.to_dict()
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["tool"], "kernelcontract")
        self.assertEqual(data["command"], "doctor")
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["summary"]["pass"], 1)
        self.assertEqual(len(data["checks"]), 1)
        # Verify valid JSON
        serialized = json.dumps(data)
        self.assertIn('"schema_version": "1.0"', serialized)
