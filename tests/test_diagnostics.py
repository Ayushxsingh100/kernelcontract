import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kernelcontract.diagnostics import run_diagnostics
from kernelcontract.models import Check, Report
from kernelcontract.cli import exit_code, render_text


class TestDiagnostics(unittest.TestCase):
    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_empty_kernel_list_is_warning(self, probe_mock, _discover_mock):
        probe_mock.return_value = ({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None)
        report = run_diagnostics()
        self.assertEqual(report.overall_status, "WARN")
        self.assertTrue(any(c.id == "kernelspec.empty" for c in report.checks))

    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({}, "Jupyter missing"))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_discovery_failure_is_failure(self, probe_mock, _discover_mock):
        probe_mock.return_value = ({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None)
        report = run_diagnostics()
        self.assertEqual(report.overall_status, "FAIL")
        self.assertTrue(any(c.id == "kernelspec.discovery" and c.status == "FAIL" for c in report.checks))

    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"python3": {"spec": {"argv": [sys.executable], "language": "python", "display_name": "Python 3"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_notebook_unknown_kernel_fails(self, probe_mock, _discover_mock):
        probe_mock.return_value = ({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {"ipykernel": {"installed": True, "version": "6.0"}}}, None)
        notebook = {"nbformat": 4, "metadata": {"kernelspec": {"name": "gone", "display_name": "Removed Python"}}, "cells": []}
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", encoding="utf-8", delete=False) as file:
            json.dump(notebook, file)
            path = file.name
        try:
            report = run_diagnostics(command="notebook", notebook_path=path)
        finally:
            os.unlink(path)
        check = next(c for c in report.checks if c.id == "notebook.kernelspec-registered")
        self.assertEqual(check.status, "FAIL")
        self.assertIn("gone", check.message)


    @patch("kernelcontract.diagnostics.resolve_executable", return_value="/tmp/external-python")
    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"external": {"spec": {"argv": ["/tmp/external-python"], "language": "python", "display_name": "External"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_external_python_kernel_is_not_executed_without_opt_in(self, probe_mock, _discover_mock, _resolve_mock):
        probe_mock.return_value = ({"version": "3.13.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None)
        report = run_diagnostics()
        self.assertEqual(probe_mock.call_count, 1)  # control Python only
        skipped = next(c for c in report.checks if c.id == "kernel.external.probe-skipped")
        self.assertEqual(skipped.status, "INFO")

    @patch("kernelcontract.diagnostics.resolve_executable", return_value="/tmp/external-python")
    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"external": {"spec": {"argv": ["/tmp/external-python"], "language": "python", "display_name": "External"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_probe_python_opt_in_probes_external_kernel(self, probe_mock, _discover_mock, _resolve_mock):
        probe_mock.return_value = ({"version": "3.13.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {"ipykernel": {"installed": True, "version": "7.0"}}}, None)
        run_diagnostics(probe_python_kernels=True)
        self.assertEqual(probe_mock.call_count, 2)

    def test_strict_exit_code(self):
        report = Report(command="doctor")
        report.add(Check(id="w", status="WARN", title="Warning", message="warning"))
        self.assertEqual(exit_code(report, strict=False), 0)
        self.assertEqual(exit_code(report, strict=True), 1)

    def test_text_report_is_clear(self):
        report = Report(command="doctor")
        report.add(Check(id="ok", status="PASS", title="Example", message="all good"))
        output = render_text(report)
        self.assertIn("did not modify packages or environments", output)
        self.assertIn("Overall status: PASS", output)
        self.assertIn("KernelContract", output)

    def test_same_path_empty_inputs_do_not_match_cwd(self):
        from kernelcontract.diagnostics import _same_path
        self.assertFalse(_same_path("", sys.executable))
        self.assertFalse(_same_path(None, sys.executable))
        self.assertFalse(_same_path("", ""))
        self.assertFalse(_same_path(None, None))
        self.assertTrue(_same_path(sys.executable, sys.executable))

    def test_notebook_missing_file_fails(self):
        report = run_diagnostics(command="notebook", notebook_path="/nonexistent/path/notebook.ipynb")
        read_check = next(c for c in report.checks if c.id == "notebook.read")
        self.assertEqual(read_check.status, "FAIL")
        self.assertIn("does not exist", read_check.message)

    def test_notebook_directory_path_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_diagnostics(command="notebook", notebook_path=temp_dir)
            read_check = next(c for c in report.checks if c.id == "notebook.read")
            self.assertEqual(read_check.status, "FAIL")
            self.assertIn("not a file", read_check.message)

    def test_notebook_invalid_json_fails(self):
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            f.write("{ invalid json")
            path = f.name
        try:
            report = run_diagnostics(command="notebook", notebook_path=path)
            read_check = next(c for c in report.checks if c.id == "notebook.read")
            self.assertEqual(read_check.status, "FAIL")
            self.assertIn("Could not read notebook JSON", read_check.message)
        finally:
            os.unlink(path)

    def test_notebook_root_not_object_fails(self):
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            f.write("[]")
            path = f.name
        try:
            report = run_diagnostics(command="notebook", notebook_path=path)
            read_check = next(c for c in report.checks if c.id == "notebook.read")
            self.assertEqual(read_check.status, "FAIL")
            self.assertIn("root must be an object", read_check.message)
        finally:
            os.unlink(path)

    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"python3": {"spec": {"argv": [sys.executable], "language": "python", "display_name": "Python 3"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_notebook_metadata_not_object_fails(self, _probe, _disc):
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            json.dump({"cells": [], "metadata": "not a dict"}, f)
            path = f.name
        try:
            report = run_diagnostics(command="notebook", notebook_path=path)
            meta_check = next(c for c in report.checks if c.id == "notebook.read")
            self.assertEqual(meta_check.status, "FAIL")
            self.assertIn("Notebook metadata must be an object", meta_check.message)
        finally:
            os.unlink(path)

    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"python3": {"spec": {"argv": [sys.executable], "language": "python", "display_name": "Python 3"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_notebook_malformed_kernelspec_warns_without_crashing(self, _probe, _disc):
        # Case 1: kernelspec field is a list instead of a dict
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            json.dump({"cells": [], "metadata": {"kernelspec": ["not", "dict"]}}, f)
            path1 = f.name
        # Case 2: kernelspec.name is a list instead of a string
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            json.dump({"cells": [], "metadata": {"kernelspec": {"name": ["unhashable", "list"]}}}, f)
            path2 = f.name
        try:
            report1 = run_diagnostics(command="notebook", notebook_path=path1)
            check1 = next(c for c in report1.checks if c.id == "notebook.kernelspec-metadata")
            self.assertEqual(check1.status, "WARN")
            self.assertIn("not an object", check1.message)

            report2 = run_diagnostics(command="notebook", notebook_path=path2)
            check2 = next(c for c in report2.checks if c.id == "notebook.kernelspec-metadata")
            self.assertEqual(check2.status, "WARN")
            self.assertIn("not declare a valid metadata.kernelspec.name string", check2.message)
        finally:
            os.unlink(path1)
            os.unlink(path2)

    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"python3": {"spec": {"argv": [sys.executable], "language": "python", "display_name": "Python 3"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_notebook_display_name_drift_warns(self, _probe, _disc):
        with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False) as f:
            json.dump({"cells": [], "metadata": {"kernelspec": {"name": "python3", "display_name": "Old Python Display"}}}, f)
            path = f.name
        try:
            report = run_diagnostics(command="notebook", notebook_path=path)
            drift_check = next(c for c in report.checks if c.id == "notebook.display-name-drift")
            self.assertEqual(drift_check.status, "WARN")
            self.assertIn("Old Python Display", drift_check.message)
            reg_check = next(c for c in report.checks if c.id == "notebook.kernelspec-registered")
            self.assertEqual(reg_check.status, "PASS")
        finally:
            os.unlink(path)

    @patch("kernelcontract.diagnostics.discover_kernelspecs")
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_kernelspec_resource_dir_and_kernel_json_validation(self, _probe, disc_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Missing resource_dir
            missing_dir = os.path.join(temp_dir, "nonexistent_dir")
            disc_mock.return_value = ({"stale": {"resource_dir": missing_dir, "spec": {"argv": [sys.executable]}}}, None)
            report = run_diagnostics()
            check = next(c for c in report.checks if c.id == "kernel.stale.resource-dir")
            self.assertEqual(check.status, "FAIL")

            # Resource dir exists, but kernel.json is missing
            ks_dir = os.path.join(temp_dir, "my_kernel")
            os.makedirs(ks_dir, exist_ok=True)
            disc_mock.return_value = ({"my_kernel": {"resource_dir": ks_dir, "spec": {"argv": [sys.executable]}}}, None)
            report = run_diagnostics()
            check = next(c for c in report.checks if c.id == "kernel.my_kernel.kernel-json")
            self.assertEqual(check.status, "FAIL")
            self.assertIn("missing", check.message)

            # kernel.json contains malformed JSON
            k_json = os.path.join(ks_dir, "kernel.json")
            with open(k_json, "w", encoding="utf-8") as kf:
                kf.write("{ malformed")
            report = run_diagnostics()
            check = next(c for c in report.checks if c.id == "kernel.my_kernel.kernel-json")
            self.assertEqual(check.status, "FAIL")
            self.assertIn("malformed", check.message)

    @patch("kernelcontract.diagnostics.discover_kernelspecs")
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_kernelspec_argv_validation(self, _probe, disc_mock):
        disc_mock.return_value = (
            {
                "empty_argv": {"spec": {"argv": []}},
                "whitespace_argv": {"spec": {"argv": ["   "]}},
                "non_list_argv": {"spec": {"argv": "not-a-list"}},
            },
            None,
        )
        report = run_diagnostics()
        for k in ("empty_argv", "whitespace_argv", "non_list_argv"):
            check = next(c for c in report.checks if c.id == f"kernel.{k}.argv")
            self.assertEqual(check.status, "FAIL")

    @patch("kernelcontract.diagnostics.discover_kernelspecs")
    @patch("kernelcontract.diagnostics.probe_python", return_value=({"version": "3.12.0", "executable": sys.executable, "prefix": sys.prefix, "packages": {}}, None))
    def test_non_python_kernel_info(self, _probe, disc_mock):
        disc_mock.return_value = ({"ir": {"spec": {"argv": [sys.executable], "language": "R", "display_name": "R"}}}, None)
        report = run_diagnostics()
        runtime_check = next(c for c in report.checks if c.id == "kernel.ir.runtime")
        self.assertEqual(runtime_check.status, "INFO")
        self.assertIn("non-Python", runtime_check.title)

    def test_server_python_path_not_found(self):
        report = run_diagnostics(server_python="/nonexistent/server/python")
        check = next(c for c in report.checks if c.id == "control-python.path")
        self.assertEqual(check.status, "FAIL")

    @patch("kernelcontract.diagnostics.probe_python")
    def test_server_python_probe_failure(self, probe_mock):
        probe_mock.return_value = (None, "Interpreter crashed with SIGSEGV")
        report = run_diagnostics(server_python=sys.executable)
        check = next(c for c in report.checks if c.id == "control-python.probe")
        self.assertEqual(check.status, "FAIL")
        self.assertIn("crashed", check.message)

    @patch("kernelcontract.diagnostics.os.path.isfile", return_value=True)
    @patch("kernelcontract.diagnostics.resolve_executable", side_effect=lambda p, *a, **k: p)
    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"p1": {"spec": {"argv": ["/custom/env/bin/python"], "language": "python"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_environment_drift_warning_when_server_python_explicit(self, probe_mock, _disc, _resolve, _isfile):
        probe_mock.side_effect = [
            ({"executable": "/server/bin/python", "prefix": "/server/env", "version": "3.12.0", "packages": {}}, None),
            ({"executable": "/custom/env/bin/python", "prefix": "/custom/env", "version": "3.12.0", "packages": {"ipykernel": {"installed": True}}}, None),
        ]
        report = run_diagnostics(server_python="/server/bin/python", probe_python_kernels=True)
        drift_check = next(c for c in report.checks if c.id == "kernel.p1.environment-drift")
        self.assertEqual(drift_check.status, "WARN")

    @patch("kernelcontract.diagnostics.resolve_executable", return_value="/custom/env/bin/python")
    @patch("kernelcontract.diagnostics.discover_kernelspecs", return_value=({"p1": {"spec": {"argv": ["/custom/env/bin/python"], "language": "python"}}}, None))
    @patch("kernelcontract.diagnostics.probe_python")
    def test_widgets_companion_check(self, probe_mock, _disc, _resolve):
        # Case 1: control has jupyterlab, kernel has ipywidgets, control lacks jupyterlab_widgets -> WARN
        probe_mock.side_effect = [
            ({"executable": sys.executable, "prefix": sys.prefix, "version": "3.12.0", "packages": {"jupyterlab": {"installed": True}, "jupyterlab_widgets": {"installed": False}}}, None),
            ({"executable": "/custom/env/bin/python", "prefix": sys.prefix, "version": "3.12.0", "packages": {"ipykernel": {"installed": True}, "ipywidgets": {"installed": True}}}, None),
        ]
        report = run_diagnostics(probe_python_kernels=True)
        w_check = next(c for c in report.checks if c.id == "kernel.p1.widgets-companion")
        self.assertEqual(w_check.status, "WARN")

        # Case 2: control has jupyterlab_widgets -> PASS
        probe_mock.side_effect = [
            ({"executable": sys.executable, "prefix": sys.prefix, "version": "3.12.0", "packages": {"jupyterlab": {"installed": True}, "jupyterlab_widgets": {"installed": True}}}, None),
            ({"executable": "/custom/env/bin/python", "prefix": sys.prefix, "version": "3.12.0", "packages": {"ipykernel": {"installed": True}, "ipywidgets": {"installed": True}}}, None),
        ]
        report2 = run_diagnostics(probe_python_kernels=True)
        w_check2 = next(c for c in report2.checks if c.id == "kernel.p1.widgets-companion")
        self.assertEqual(w_check2.status, "PASS")
