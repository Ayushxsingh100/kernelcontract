"""Read-only discovery of Jupyter kernelspecs and safe interpreter probes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Tuple


PYTHON_LANGUAGE_NAMES = {"python", "python2", "python3"}


def _expanded_env(spec_env: Dict[str, Any]) -> Dict[str, str]:
    env = os.environ.copy()
    entries = {
        key: value
        for key, value in spec_env.items()
        if isinstance(key, str) and isinstance(value, str)
    }
    # Kernelspec env entries are added to the parent environment. Expand only
    # values declared by the kernelspec; applying Template to every inherited
    # variable could fail on unrelated values containing a literal '$'.
    env.update(entries)
    for key, value in entries.items():
        try:
            env[key] = Template(value).safe_substitute(env)
        except ValueError:
            # Treat malformed template syntax as a literal environment value.
            env[key] = value
    return env


def resolve_executable(argv0: str, spec_env: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Resolve the first kernelspec argv item without invoking a shell."""
    if not argv0 or not isinstance(argv0, str):
        return None
    cleaned = argv0.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    if not cleaned:
        return None

    env = _expanded_env(spec_env or {})
    try:
        expanded = Template(os.path.expanduser(cleaned)).safe_substitute(env)
    except ValueError:
        expanded = os.path.expanduser(cleaned)
    # Expand conventional $VAR and %VAR% forms as well. Template above handles
    # variables added by the kernelspec; expandvars handles platform syntax.
    expanded = os.path.expandvars(expanded)
    has_path_component = os.path.isabs(expanded) or os.sep in expanded or (os.altsep and os.altsep in expanded)
    if has_path_component:
        candidate = Path(expanded)
        try:
            if candidate.is_file() and (os.name == "nt" or os.access(str(candidate), os.X_OK)):
                return str(candidate.resolve())
        except OSError:
            pass
        # On Windows, path components may omit .exe; check PATHEXT with normalized slashes
        if os.name == "nt":
            norm_expanded = os.path.normpath(expanded)
            pathext = [ext for ext in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if ext]
            for ext in pathext:
                target = Path(norm_expanded + ext if not norm_expanded.lower().endswith(ext.lower()) else norm_expanded)
                try:
                    if target.is_file():
                        return str(target.resolve())
                except OSError:
                    pass
            which_path = shutil.which(norm_expanded)
            if which_path:
                return str(Path(which_path).resolve())
        else:
            which_path = shutil.which(expanded)
            if which_path:
                return str(Path(which_path).resolve())
        return None
    resolved = shutil.which(expanded, path=env.get("PATH"))
    return str(Path(resolved).resolve()) if resolved else None


def discover_kernelspecs(timeout: float = 15.0) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """Return {name: {resource_dir, spec}} using Jupyter's supported JSON CLI."""
    jupyter = shutil.which("jupyter")
    if not jupyter:
        return {}, (
            "Could not find the 'jupyter' command on PATH. Run KernelContract in the "
            "environment that provides Jupyter, then try again."
        )
    try:
        proc = subprocess.run(
            [jupyter, "kernelspec", "list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {}, "'jupyter kernelspec list --json' timed out after {} seconds.".format(timeout)
    except OSError as exc:
        return {}, "Could not run Jupyter's kernelspec command: {}".format(exc)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "no diagnostic text").strip()
        return {}, "Jupyter could not list kernelspecs (exit {}). {}".format(proc.returncode, detail[:800])
    raw_stdout = proc.stdout.strip()
    try:
        payload = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        # Some Jupyter plugins or logging hooks print warnings to stdout; attempt to locate JSON boundaries
        start = raw_stdout.find("{")
        end = raw_stdout.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                payload = json.loads(raw_stdout[start : end + 1])
            except json.JSONDecodeError:
                return {}, "Jupyter returned invalid JSON for kernelspecs: {}".format(exc)
        else:
            return {}, "Jupyter returned invalid JSON for kernelspecs: {}".format(exc)

    raw_specs = payload.get("kernelspecs")
    if not isinstance(raw_specs, dict):
        return {}, "Jupyter's kernelspec JSON did not contain a 'kernelspecs' object."

    result: Dict[str, Dict[str, Any]] = {}
    for name, entry in raw_specs.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        spec = entry.get("spec")
        if not isinstance(spec, dict):
            spec = {}
        result[name] = {
            "resource_dir": entry.get("resource_dir"),
            "spec": spec,
        }
    return result, None


_PROBE_SENTINEL = "__KERNELCONTRACT_PROBE_JSON__:"


def probe_python(interpreter: str, timeout: float = 8.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Run a short, read-only probe in an interpreter; never install or modify packages."""
    code = r'''
import importlib.metadata as md
import importlib.util
import json
import sys

def package(name):
    try:
        version = md.version(name)
        return {"installed": True, "version": version}
    except Exception:
        try:
            installed = importlib.util.find_spec(name.replace("-", "_")) is not None
        except Exception:
            installed = False
        return {"installed": installed, "version": None}

payload = {
    "executable": sys.executable,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "version": ".".join(map(str, sys.version_info[:3])),
    "packages": {
        "ipykernel": package("ipykernel"),
        "ipywidgets": package("ipywidgets"),
        "jupyterlab": package("jupyterlab"),
        "jupyterlab_widgets": package("jupyterlab_widgets"),
        "notebook": package("notebook"),
        "widgetsnbextension": package("widgetsnbextension"),
    },
}
print("__KERNELCONTRACT_PROBE_JSON__:" + json.dumps(payload))
'''
    try:
        proc = subprocess.run(
            [interpreter, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None, "Python probe timed out after {} seconds.".format(timeout)
    except OSError as exc:
        return None, "Could not start interpreter: {}".format(exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "no diagnostic text").strip()
        return None, "Interpreter probe failed (exit {}). {}".format(proc.returncode, detail[:800])

    lines = proc.stdout.strip().splitlines()
    json_text: Optional[str] = None
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith(_PROBE_SENTINEL):
            json_text = stripped[len(_PROBE_SENTINEL):]
            break
    if json_text is None and lines:
        json_text = lines[-1].strip()

    if not json_text:
        return None, "Interpreter returned empty probe output."

    try:
        result = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return None, "Interpreter returned unexpected probe output: {}".format(exc)
    return result, None


def is_python_kernel(spec: Dict[str, Any], resolved_executable: Optional[str]) -> bool:
    language = str(spec.get("language", "")).strip().lower()
    if language in PYTHON_LANGUAGE_NAMES:
        return True
    if language:
        return False
    # If language was omitted from kernelspec, inspect argv and executable
    argv = spec.get("argv", [])
    if isinstance(argv, list):
        for arg in argv:
            if isinstance(arg, str) and ("ipykernel" in arg.lower() or "ipykernel_launcher" in arg.lower()):
                return True
    if not resolved_executable:
        return False
    name = Path(resolved_executable).name.lower()
    return name.startswith(("python", "pypy"))
