import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kernelcontract.cli import entrypoint, exit_code, main, render_text
from kernelcontract.models import Check, Report


class TestCli(unittest.TestCase):
    def test_exit_code_matrix(self):
        # Empty / PASS -> 0
        r_pass = Report(command="doctor")
        r_pass.add(Check(id="1", status="PASS", title="P", message="m"))
        self.assertEqual(exit_code(r_pass, strict=False), 0)
        self.assertEqual(exit_code(r_pass, strict=True), 0)

        # INFO only -> 0
        r_info = Report(command="doctor")
        r_info.add(Check(id="2", status="INFO", title="I", message="m"))
        self.assertEqual(exit_code(r_info, strict=False), 0)
        self.assertEqual(exit_code(r_info, strict=True), 0)

        # WARN -> 0 non-strict, 1 strict
        r_warn = Report(command="doctor")
        r_warn.add(Check(id="3", status="WARN", title="W", message="m"))
        self.assertEqual(exit_code(r_warn, strict=False), 0)
        self.assertEqual(exit_code(r_warn, strict=True), 1)

        # FAIL -> 1 always
        r_fail = Report(command="doctor")
        r_fail.add(Check(id="4", status="FAIL", title="F", message="m"))
        self.assertEqual(exit_code(r_fail, strict=False), 1)
        self.assertEqual(exit_code(r_fail, strict=True), 1)

    @patch("kernelcontract.cli.run_diagnostics")
    def test_main_doctor_text_output(self, diag_mock):
        rep = Report(command="doctor")
        rep.add(Check(id="test.pass", status="PASS", title="Everything OK", message="All checks passed."))
        diag_mock.return_value = rep

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            code = main(["doctor"])
        self.assertEqual(code, 0)
        output = captured.getvalue()
        self.assertIn("KernelContract", output)
        self.assertIn("Everything OK", output)
        self.assertIn("Overall status: PASS", output)

    @patch("kernelcontract.cli.run_diagnostics")
    def test_main_doctor_json_output(self, diag_mock):
        rep = Report(command="doctor")
        rep.add(Check(id="test.info", status="INFO", title="Info Check", message="Informative details.", details={"flag": True}))
        diag_mock.return_value = rep

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            code = main(["doctor", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(captured.getvalue())
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["command"], "doctor")
        self.assertEqual(payload["tool"], "kernelcontract")
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["checks"][0]["id"], "test.info")
        self.assertTrue(payload["checks"][0]["details"]["flag"])

    @patch("kernelcontract.cli.run_diagnostics")
    def test_main_doctor_strict_mode(self, diag_mock):
        rep = Report(command="doctor")
        rep.add(Check(id="test.warn", status="WARN", title="Warning Check", message="A warning was generated."))
        diag_mock.return_value = rep

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            code_normal = main(["doctor"])
        self.assertEqual(code_normal, 0)

        with patch("sys.stdout", captured):
            code_strict = main(["doctor", "--strict"])
        self.assertEqual(code_strict, 1)

    @patch("kernelcontract.cli.run_diagnostics")
    def test_main_notebook_command(self, diag_mock):
        rep = Report(command="notebook")
        rep.add(Check(id="notebook.read", status="PASS", title="Notebook Valid", message="Notebook reads cleanly."))
        diag_mock.return_value = rep

        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            json.dump({"cells": [], "metadata": {}}, f)
            path = f.name
        try:
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                code = main(["notebook", path, "--json"])
            self.assertEqual(code, 0)
            diag_mock.assert_called_once_with(
                command="notebook",
                notebook_path=path,
                server_python=None,
                probe_python_kernels=False,
            )
        finally:
            os.unlink(path)

    @patch("kernelcontract.cli.main", return_value=0)
    def test_entrypoint_calls_system_exit(self, main_mock):
        with self.assertRaises(SystemExit) as ctx:
            entrypoint()
        self.assertEqual(ctx.exception.code, 0)

    def test_main_requires_command(self):
        with patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main([])
            self.assertEqual(ctx.exception.code, 2)
