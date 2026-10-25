"""The core deterministic checks used by both local and CI invocations."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .discovery import discover_kernelspecs, is_python_kernel, probe_python, resolve_executable
from .models import Check, Report


def _same_path(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right:
        return False
    try:
        return os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right))
    except (OSError, TypeError):
        return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _package(packages: Dict[str, Any], name: str) -> Dict[str, Any]:
    value = packages.get(name, {})
    return value if isinstance(value, dict) else {}


def _read_notebook(path: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    target = Path(path).expanduser()
    if not target.exists():
        return None, "Notebook file does not exist: {}".format(target)
    if not target.is_file():
        return None, "Notebook path is not a file: {}".format(target)
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, "Could not read notebook JSON: {}".format(exc)
    if not isinstance(data, dict):
        return None, "Notebook JSON root must be an object."
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        return None, "Notebook metadata must be an object."
    return data, None


def run_diagnostics(
    command: str = "doctor",
    notebook_path: Optional[str] = None,
    server_python: Optional[str] = None,
    probe_python_kernels: bool = False,
) -> Report:
    """Collect diagnostics. All operations are read-only and use bounded subprocesses."""
    report = Report(command=command)
    if probe_python_kernels:
        report.add(Check(
            id="security.python-probing",
            status="INFO",
            title="Python kernel probing enabled",
            message="The --probe-python option can execute each registered Python kernel executable. Use it only when you trust the kernelspecs on this machine.",
            suggestions=[],
        ))
    provided_server_python = bool(server_python)
    if server_python:
        resolved_server = resolve_executable(server_python)
        control_python = resolved_server if resolved_server else os.path.abspath(os.path.expanduser(server_python))
    else:
        control_python = sys.executable

    if not os.path.isfile(control_python):
        report.add(Check(
            id="control-python.path",
            status="FAIL",
            title="Control/server Python path",
            message="The configured Python interpreter does not exist or is not a file: {}".format(control_python),
            details={"path": control_python},
            suggestions=["Pass the absolute path to the Python interpreter used by the Jupyter server with --server-python."],
        ))
        control_probe = None
    else:
        control_probe, control_error = probe_python(control_python)
        if control_error:
            report.add(Check(
                id="control-python.probe",
                status="FAIL",
                title="Control/server Python probe",
                message=control_error,
                details={"path": control_python},
                suggestions=["Confirm the interpreter is executable and not blocked by the local environment."],
            ))
        else:
            label = "Server Python (explicitly provided)" if provided_server_python else "Current Python (control environment)"
            report.add(Check(
                id="control-python.probe",
                status="PASS",
                title=label,
                message="Python {} is executable.".format(control_probe.get("version", "unknown")),
                details={"executable": control_probe.get("executable"), "prefix": control_probe.get("prefix"), "version": control_probe.get("version")},
                suggestions=[],
            ))
            if not provided_server_python:
                report.add(Check(
                    id="control-python.role",
                    status="INFO",
                    title="Server interpreter not inferred",
                    message="The current Python is used as a control environment; it is not assumed to be the actual Jupyter server Python.",
                    details={"current_python": control_python},
                    suggestions=["Re-run with --server-python /absolute/path/to/server/python when Jupyter runs from another environment."],
                ))

    kernels, discover_error = discover_kernelspecs()
    if discover_error:
        report.add(Check(
            id="kernelspec.discovery",
            status="FAIL",
            title="Discover Jupyter kernels",
            message=discover_error,
            details={},
            suggestions=["Install or activate the environment that provides the Jupyter command, then rerun kernelcontract doctor."],
        ))
        kernels = {}
    else:
        report.add(Check(
            id="kernelspec.discovery",
            status="PASS",
            title="Discover Jupyter kernels",
            message="Found {} registered kernelspec(s).".format(len(kernels)),
            details={"count": len(kernels), "names": sorted(kernels.keys())},
            suggestions=["Register a kernel in the environment you intend to use if none of these is expected."] if not kernels else [],
        ))
        if not kernels:
            report.add(Check(
                id="kernelspec.empty",
                status="WARN",
                title="No registered kernels",
                message="Jupyter returned no registered kernelspecs.",
                details={},
                suggestions=["For a Python environment, install ipykernel in the target environment and register it with `python -m ipykernel install --user --name <name>`."],
            ))

    kernel_probes: Dict[str, Dict[str, Any]] = {}
    for name, entry in sorted(kernels.items()):
        resource_dir = entry.get("resource_dir") if isinstance(entry, dict) else None
        spec = entry.get("spec", {}) if isinstance(entry, dict) else {}
        spec = spec if isinstance(spec, dict) else {}

        if resource_dir:
            res_path = Path(resource_dir)
            if not res_path.is_dir():
                report.add(Check(
                    id="kernel.{}.resource-dir".format(name),
                    status="FAIL",
                    title="{}: kernelspec directory".format(name),
                    message="The kernelspec resource directory does not exist or is not a directory: {}".format(resource_dir),
                    details={"kernel": name, "resource_dir": resource_dir},
                    suggestions=["Remove the stale kernelspec registration or restore the missing directory."],
                ))
                continue
            kernel_json_path = res_path / "kernel.json"
            if not kernel_json_path.is_file():
                report.add(Check(
                    id="kernel.{}.kernel-json".format(name),
                    status="FAIL",
                    title="{}: kernel.json file".format(name),
                    message="The kernel.json file is missing in kernelspec directory: {}".format(kernel_json_path),
                    details={"kernel": name, "resource_dir": resource_dir},
                    suggestions=["Reinstall or re-register this kernelspec."],
                ))
                continue
            try:
                with kernel_json_path.open("r", encoding="utf-8") as kf:
                    disk_spec = json.load(kf)
                if not isinstance(disk_spec, dict):
                    report.add(Check(
                        id="kernel.{}.kernel-json".format(name),
                        status="FAIL",
                        title="{}: kernel.json format".format(name),
                        message="kernel.json root must be a JSON object: {}".format(kernel_json_path),
                        details={"kernel": name, "resource_dir": resource_dir},
                        suggestions=["Fix the format of kernel.json or re-register this kernelspec."],
                    ))
                    continue
                if not spec:
                    spec = disk_spec
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                report.add(Check(
                    id="kernel.{}.kernel-json".format(name),
                    status="FAIL",
                    title="{}: kernel.json valid".format(name),
                    message="kernel.json contains malformed JSON or cannot be read: {}".format(exc),
                    details={"kernel": name, "resource_dir": resource_dir, "error": str(exc)},
                    suggestions=["Fix syntax errors in kernel.json or re-register this kernelspec."],
                ))
                continue

        argv = spec.get("argv", [])
        if not isinstance(argv, list) or not argv or not isinstance(argv[0], str) or not argv[0].strip():
            report.add(Check(
                id="kernel.{}.argv".format(name),
                status="FAIL",
                title="{}: kernelspec executable".format(name),
                message="The kernelspec has no valid argv[0] interpreter/launcher.",
                details={"kernel": name, "argv": argv, "resource_dir": resource_dir},
                suggestions=["Inspect kernel.json and reinstall or re-register this kernelspec if it is stale."],
            ))
            continue

        spec_env = spec.get("env", {}) if isinstance(spec.get("env", {}), dict) else {}
        executable = resolve_executable(argv[0], spec_env)
        is_python = is_python_kernel(spec, executable)
        if not executable:
            report.add(Check(
                id="kernel.{}.executable".format(name),
                status="FAIL",
                title="{}: executable exists".format(name),
                message="The kernelspec executable could not be resolved: {!r}.".format(argv[0]),
                details={"kernel": name, "argv0": argv[0], "language": spec.get("language"), "resource_dir": resource_dir},
                suggestions=["If the environment was moved or deleted, recreate it and re-register the kernel. Otherwise inspect the argv field in this kernel's kernel.json."],
            ))
            continue

        report.add(Check(
            id="kernel.{}.executable".format(name),
            status="PASS",
            title="{}: executable exists".format(name),
            message="Resolved kernelspec executable to {}.".format(executable),
            details={"kernel": name, "argv0": argv[0], "resolved_executable": executable, "language": spec.get("language"), "display_name": spec.get("display_name")},
        ))

        if not is_python:
            report.add(Check(
                id="kernel.{}.runtime".format(name),
                status="INFO",
                title="{}: non-Python runtime".format(name),
                message="Executable exists; Python package checks do not apply to this kernel language.",
                details={"kernel": name, "language": spec.get("language", "unknown")},
            ))
            continue

        same_as_control = bool(control_probe and _same_path(executable, str(control_probe.get("executable", ""))))
        if not probe_python_kernels and not same_as_control:
            report.add(Check(
                id="kernel.{}.probe-skipped".format(name),
                status="INFO",
                title="{}: Python runtime probe skipped".format(name),
                message="This kernel uses a different executable from the current control interpreter. KernelContract did not execute it because kernelspec executables can run arbitrary code.",
                details={"kernel": name, "executable": executable, "control_executable": control_probe.get("executable") if control_probe else None},
                suggestions=["If you trust this kernelspec and want package/runtime checks, rerun with --probe-python."],
            ))
            continue

        probe, probe_error = probe_python(executable)
        if probe_error:
            report.add(Check(
                id="kernel.{}.probe".format(name),
                status="FAIL",
                title="{}: Python can start".format(name),
                message=probe_error,
                details={"kernel": name, "executable": executable},
                suggestions=["Run the configured interpreter directly and check whether the environment is damaged or inaccessible."],
            ))
            continue

        kernel_probes[name] = probe
        packages = probe.get("packages", {})
        ipykernel = _package(packages, "ipykernel")
        if ipykernel.get("installed"):
            report.add(Check(
                id="kernel.{}.ipykernel".format(name),
                status="PASS",
                title="{}: ipykernel importable".format(name),
                message="Python {} starts and ipykernel is installed{}.".format(
                    probe.get("version", "unknown"),
                    " (version {})".format(ipykernel.get("version")) if ipykernel.get("version") else "",
                ),
                details={"kernel": name, "python": probe.get("executable"), "prefix": probe.get("prefix"), "ipykernel": ipykernel},
            ))
        else:
            report.add(Check(
                id="kernel.{}.ipykernel".format(name),
                status="FAIL",
                title="{}: ipykernel importable".format(name),
                message="The kernel points to a Python interpreter where ipykernel was not found.",
                details={"kernel": name, "python": probe.get("executable"), "prefix": probe.get("prefix")},
                suggestions=["Install ipykernel into this exact environment, for example: {} -m pip install ipykernel".format(executable)],
            ))

        if control_probe and not _same_path(str(control_probe.get("prefix", "")), str(probe.get("prefix", ""))):
            report.add(Check(
                id="kernel.{}.environment-drift".format(name),
                status="WARN" if provided_server_python else "INFO",
                title="{}: control/kernel environments differ".format(name),
                message=(
                    "The configured server Python and this kernel use different prefixes. This may be intentional, but server-side and kernel-side packages must be installed in the correct places."
                    if provided_server_python else
                    "This kernel uses a different Python prefix from the current CLI environment. The actual server environment was not inferred, so this does not prove a server/kernel mismatch."
                ),
                details={"kernel_prefix": probe.get("prefix"), "control_prefix": control_probe.get("prefix"), "server_python_explicit": provided_server_python},
                suggestions=["Compare package locations in both environments. Keep separate environments if intentional, and install each dependency in the layer that uses it."],
            ))

        if control_probe:
            control_packages = control_probe.get("packages", {})
            kernel_packages = probe.get("packages", {})
            if _package(control_packages, "jupyterlab").get("installed") and _package(kernel_packages, "ipywidgets").get("installed"):
                frontend_widgets = _package(control_packages, "jupyterlab_widgets")
                if not frontend_widgets.get("installed"):
                    report.add(Check(
                        id="kernel.{}.widgets-companion".format(name),
                        status="WARN",
                        title="{}: JupyterLab widgets companion".format(name),
                        message="The Python kernel has ipywidgets, but the control/server environment has no jupyterlab_widgets package. Interactive widgets may not render in JupyterLab.",
                        details={"kernel": name, "ipywidgets": _package(kernel_packages, "ipywidgets"), "jupyterlab": _package(control_packages, "jupyterlab")},
                        suggestions=["If this is the environment that runs JupyterLab, install jupyterlab_widgets there; keep ipywidgets installed in each kernel environment that uses widgets."],
                    ))
                else:
                    report.add(Check(
                        id="kernel.{}.widgets-companion".format(name),
                        status="PASS",
                        title="{}: JupyterLab widgets companion present".format(name),
                        message="Both ipywidgets in the kernel and jupyterlab_widgets in the control environment are present; exact version compatibility is not certified by this check.",
                        details={"kernel": name, "ipywidgets": _package(kernel_packages, "ipywidgets"), "jupyterlab_widgets": frontend_widgets},
                    ))

    if notebook_path:
        notebook_data, notebook_error = _read_notebook(notebook_path)
        if notebook_error:
            report.add(Check(
                id="notebook.read",
                status="FAIL",
                title="Read notebook metadata",
                message=notebook_error,
                details={"path": notebook_path},
                suggestions=["Provide a readable .ipynb file containing valid JSON."],
            ))
        else:
            metadata = notebook_data.get("metadata")
            if not isinstance(metadata, dict):
                report.add(Check(
                    id="notebook.metadata",
                    status="FAIL",
                    title="Notebook metadata object",
                    message="Notebook metadata is not an object.",
                    details={"path": str(Path(notebook_path).expanduser())},
                    suggestions=["Ensure the notebook contains a valid metadata object."],
                ))
            else:
                raw_kernelspec = metadata.get("kernelspec")
                if raw_kernelspec is not None and not isinstance(raw_kernelspec, dict):
                    report.add(Check(
                        id="notebook.kernelspec-metadata",
                        status="WARN",
                        title="Notebook kernel metadata malformed",
                        message="The notebook metadata.kernelspec field is not an object.",
                        details={"path": str(Path(notebook_path).expanduser()), "kernelspec": raw_kernelspec},
                        suggestions=["Open the notebook in Jupyter, select the intended kernel, and save the notebook."],
                    ))
                elif not raw_kernelspec:
                    report.add(Check(
                        id="notebook.kernelspec-metadata",
                        status="WARN",
                        title="Notebook kernel metadata missing",
                        message="The notebook does not declare metadata.kernelspec; the intended kernel cannot be verified from metadata alone.",
                        details={"path": str(Path(notebook_path).expanduser()), "language_info": metadata.get("language_info")},
                        suggestions=["Open the notebook in Jupyter, select the intended kernel, save the notebook, and rerun the check."],
                    ))
                else:
                    declared_name = raw_kernelspec.get("name")
                    display_name = raw_kernelspec.get("display_name")
                    if not isinstance(declared_name, str) or not declared_name.strip():
                        report.add(Check(
                            id="notebook.kernelspec-metadata",
                            status="WARN",
                            title="Notebook kernel metadata invalid name",
                            message="The notebook does not declare a valid metadata.kernelspec.name string; the intended kernel cannot be verified from metadata alone.",
                            details={"path": str(Path(notebook_path).expanduser()), "kernelspec": raw_kernelspec},
                            suggestions=["Open the notebook in Jupyter, select the intended kernel, save the notebook, and rerun the check."],
                        ))
                    else:
                        declared_name = declared_name.strip()
                        if declared_name not in kernels:
                            report.add(Check(
                                id="notebook.kernelspec-registered",
                                status="FAIL",
                                title="Notebook kernel is registered",
                                message="Notebook requests kernel {!r}, but that name is not in the discovered kernelspec list.".format(declared_name),
                                details={
                                    "path": str(Path(notebook_path).expanduser()),
                                    "requested_kernel": declared_name,
                                    "requested_display_name": display_name,
                                    "available_kernels": sorted(kernels.keys()),
                                },
                                suggestions=["Register the intended kernel or select an installed kernel in Jupyter and save the notebook. Do not assume a fallback kernel is equivalent."],
                            ))
                        else:
                            spec = kernels[declared_name].get("spec", {})
                            registered_display = spec.get("display_name") if isinstance(spec, dict) else None
                            report.add(Check(
                                id="notebook.kernelspec-registered",
                                status="PASS",
                                title="Notebook kernel is registered",
                                message="Notebook kernel {!r} is present in the discovered kernelspec list.".format(declared_name),
                                details={
                                    "path": str(Path(notebook_path).expanduser()),
                                    "requested_kernel": declared_name,
                                    "notebook_display_name": display_name,
                                    "registered_display_name": registered_display,
                                },
                            ))
                            if (
                                isinstance(display_name, str)
                                and isinstance(registered_display, str)
                                and display_name != registered_display
                            ):
                                report.add(Check(
                                    id="notebook.display-name-drift",
                                    status="WARN",
                                    title="Notebook kernel display name differs",
                                    message="Notebook metadata says {!r}, while the registered kernelspec displays {!r}. The kernel name is registered, but the display name may have changed.".format(
                                        display_name, registered_display
                                    ),
                                    details={
                                        "notebook_display_name": display_name,
                                        "registered_display_name": registered_display,
                                    },
                                    suggestions=["Confirm the notebook still uses the intended kernel; update metadata only after verifying the runtime."],
                                ))

    if not report.checks:
        report.add(Check(id="report.empty", status="INFO", title="No checks run", message="No diagnostics were collected."))
    return report
