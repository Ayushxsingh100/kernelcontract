import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kernelcontract.discovery import discover_kernelspecs, is_python_kernel, probe_python, resolve_executable


class TestDiscovery(unittest.TestCase):
    def test_resolve_current_python(self):
        resolved = resolve_executable(sys.executable)
        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.isfile(resolved))

    def test_resolve_missing_absolute_executable(self):
        missing = os.path.join(os.path.abspath(os.sep), "path-that-does-not-exist-kernelcontract")
        self.assertIsNone(resolve_executable(missing))

    def test_is_python_kernel_from_language(self):
        self.assertTrue(is_python_kernel({"language": "Python"}, "/not/important"))
        self.assertFalse(is_python_kernel({"language": "R"}, "/usr/bin/python"))

    def test_probe_current_python(self):
        result, error = probe_python(sys.executable)
        self.assertIsNone(error)
        self.assertEqual(result["executable"], sys.executable)
        self.assertIn("ipykernel", result["packages"])

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_parses_supported_json_output(self, run_mock, _which_mock):
        payload = {"kernelspecs": {"python3": {"resource_dir": "/tmp/python3", "spec": {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"], "language": "python", "display_name": "Python 3"}}}}
        run_mock.return_value = Mock(returncode=0, stdout=json.dumps(payload), stderr="")
        kernels, error = discover_kernelspecs()
        self.assertIsNone(error)
        self.assertIn("python3", kernels)
        self.assertEqual(kernels["python3"]["spec"]["display_name"], "Python 3")

    @patch("kernelcontract.discovery.shutil.which", return_value=None)
    def test_discover_explains_missing_jupyter(self, _which_mock):
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("jupyter", error)

    def test_resolve_empty_and_invalid_argv0(self):
        self.assertIsNone(resolve_executable(""))
        self.assertIsNone(resolve_executable("   "))
        self.assertIsNone(resolve_executable(None))  # type: ignore

    def test_resolve_quoted_executable_with_spaces(self):
        quoted = f'"{sys.executable}"'
        resolved = resolve_executable(quoted)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved, str(Path(sys.executable).resolve()))
        self.assertTrue(os.path.samefile(resolved, sys.executable))

    @patch("kernelcontract.discovery.Path.is_file", return_value=False)
    @patch("kernelcontract.discovery.shutil.which")
    def test_resolve_windows_pathext_fallback(self, which_mock, _is_file_mock):
        fake_target = r"C:\venvs\env\Scripts\python.exe"
        which_mock.return_value = fake_target
        resolved = resolve_executable(r"C:\venvs\env\Scripts\python")
        self.assertEqual(resolved, str(os.path.abspath(fake_target)))

    def test_resolve_with_spec_env_expansion(self):
        resolved = resolve_executable("$CUSTOM_BIN/python", spec_env={"CUSTOM_BIN": os.path.dirname(sys.executable)})
        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.isfile(resolved))

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(["cmd"], 15.0))
    def test_discover_timeout(self, _run_mock, _which_mock):
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("timed out", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_non_zero_exit(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=1, stdout="", stderr="Internal Jupyter Error")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("Jupyter could not list kernelspecs", error)
        self.assertIn("Internal Jupyter Error", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_malformed_json(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout="not valid json", stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("invalid JSON", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_root_array(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout="[]", stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("unexpected JSON root structure", error)
        self.assertIn("list", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_root_null(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout="null", stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("unexpected JSON root structure", error)
        self.assertIn("NoneType", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_root_string(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout='"jupyter-kernels"', stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("unexpected JSON root structure", error)
        self.assertIn("str", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_root_number(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout="42", stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("unexpected JSON root structure", error)
        self.assertIn("int", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_missing_kernelspecs_field(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout='{"other_key": "val"}', stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("missing the required 'kernelspecs' field", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_kernelspecs_field_wrong_type(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout='{"kernelspecs": ["not", "a", "dict"]}', stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("did not contain a 'kernelspecs' object", error)
        self.assertIn("list", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_kernelspecs_field_null(self, run_mock, _which_mock):
        run_mock.return_value = Mock(returncode=0, stdout='{"kernelspecs": null}', stderr="")
        kernels, error = discover_kernelspecs()
        self.assertEqual(kernels, {})
        self.assertIn("did not contain a 'kernelspecs' object", error)
        self.assertIn("NoneType", error)

    @patch("kernelcontract.discovery.shutil.which", return_value="/fake/jupyter")
    @patch("kernelcontract.discovery.subprocess.run")
    def test_discover_json_with_surrounding_warnings(self, run_mock, _which_mock):
        payload = {"kernelspecs": {"python3": {"resource_dir": "/tmp/p3", "spec": {"argv": [sys.executable]}}}}
        stdout = f"[IPKernelApp] WARNING | config warning\n{json.dumps(payload)}\n[Extra] Info"
        run_mock.return_value = Mock(returncode=0, stdout=stdout, stderr="")
        kernels, error = discover_kernelspecs()
        self.assertIsNone(error)
        self.assertIn("python3", kernels)

    @patch("kernelcontract.discovery.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(["cmd"], 8.0))
    def test_probe_python_timeout(self, _run_mock):
        result, error = probe_python(sys.executable)
        self.assertIsNone(result)
        self.assertIn("timed out", error)

    @patch("kernelcontract.discovery.subprocess.run")
    def test_probe_python_non_zero_exit(self, run_mock):
        run_mock.return_value = Mock(returncode=127, stdout="", stderr="Interpreter missing library")
        result, error = probe_python(sys.executable)
        self.assertIsNone(result)
        self.assertIn("Interpreter probe failed", error)

    @patch("kernelcontract.discovery.subprocess.run")
    def test_probe_python_with_noisy_stdout_sentinel(self, run_mock):
        data = {
            "executable": sys.executable,
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "version": "3.12.0",
            "packages": {"ipykernel": {"installed": True, "version": "6.29.0"}},
        }
        stdout = f"Welcome banner\n__KERNELCONTRACT_PROBE_JSON__:{json.dumps(data)}\nClosing connection notice\n"
        run_mock.return_value = Mock(returncode=0, stdout=stdout, stderr="")
        result, error = probe_python(sys.executable)
        self.assertIsNone(error)
        self.assertEqual(result["executable"], sys.executable)
        self.assertTrue(result["packages"]["ipykernel"]["installed"])

    def test_is_python_kernel_inferred_from_argv(self):
        # Language omitted, but argv specifies ipykernel_launcher
        self.assertTrue(is_python_kernel({"argv": ["/bin/custom-run", "-m", "ipykernel_launcher"]}, None))
        # Language omitted, executable is pypy3
        self.assertTrue(is_python_kernel({}, "/opt/pypy/bin/pypy3"))
        # Non-python
        self.assertFalse(is_python_kernel({"argv": ["bash"]}, "/bin/bash"))
