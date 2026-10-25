# KernelContract

**Stop guessing which Jupyter kernel your notebook is using.**

KernelContract performs local, read-only diagnostics on Jupyter kernelspecs, Python executables, and notebook kernel metadata to identify configuration problems and environment drift before execution.

[![PyPI Version](https://img.shields.io/pypi/v/kernelcontract?include_prereleases)](https://pypi.org/project/kernelcontract/)
[![Python Versions](https://img.shields.io/pypi/pyversions/kernelcontract)](https://pypi.org/project/kernelcontract/)
[![MIT License](https://img.shields.io/github/license/Ayushxsingh100/kernelcontract)](https://github.com/Ayushxsingh100/kernelcontract/blob/master/LICENSE)
[![CI Status](https://github.com/Ayushxsingh100/kernelcontract/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Ayushxsingh100/kernelcontract/actions/workflows/ci.yml)

> **Alpha Release (`0.1.0a4` candidate):** KernelContract is published on [PyPI](https://pypi.org/project/kernelcontract/) (current release: [0.1.0a3](https://pypi.org/project/kernelcontract/0.1.0a3/)) and tagged on [GitHub](https://github.com/Ayushxsingh100/kernelcontract/releases). This release candidate (`0.1.0a4`) synchronizes project documentation and metadata with PyPI. It performs strictly local, read-only checks and will never modify your packages, configuration files, or notebook contents.

---

## Quick start

### Prerequisites

* **Python:** 3.10, 3.11, 3.12, or 3.13.
* **Jupyter CLI on PATH:** KernelContract has **zero external runtime dependencies** (Python standard library only), but requires that the `jupyter` command (such as via `jupyter-core`) is available on your `PATH` for kernel discovery (`jupyter kernelspec list --json`). The Jupyter CLI is not automatically bundled with KernelContract.

### Installation

#### Primary: Install from PyPI

Install the current published alpha release directly from [PyPI](https://pypi.org/project/kernelcontract/):

```bash
python -m pip install --pre kernelcontract==0.1.0a3
```

*(The `--pre` flag is required because alpha releases are pre-releases; `pip` requires `--pre` to allow installing alpha and pre-release packages).*

#### Alternative: Install from tagged GitHub release (for developers)

Developers or contributors who wish to install directly from the tagged release on GitHub can use:

```bash
python -m pip install "git+https://github.com/Ayushxsingh100/kernelcontract.git@v0.1.0a3"
```

To install the latest development snapshot (`0.1.0a4` candidate) from the default `master` branch:

```bash
python -m pip install "git+https://github.com/Ayushxsingh100/kernelcontract.git"
```

---

## The problem: silent notebook mismatches

Jupyter notebook failures are frequently caused by environment mismatches rather than faulty notebook code:

* **Missing kernels:** A shared or cloned `.ipynb` references a kernel (e.g. `pytorch-env` or `python-3.11`) that was never registered on your machine.
* **Broken executables:** A registered kernelspec points to a Python interpreter in a virtual environment that was moved, upgraded, or deleted.
* **Interpreter drift:** The Jupyter server runs in one environment while a kernel executes in another environment that lacks `ipykernel` or companion packages like `jupyterlab_widgets`.
* **Metadata drift:** A notebook declares a display name (e.g. `Python (DataScience)`) that silently points to an entirely different interpreter on disk.

When these issues occur, notebooks either fail on startup, hang, or silently fall back to an arbitrary default interpreter with different packages installed.

**KernelContract gives you deterministic, read-only visibility into your Jupyter setup before running code.**

---

## See it in action

### 1. Diagnose registered kernels: `kernelcontract doctor`

Inspect all discovered kernelspecs, check executable paths, and verify control interpreter health:

```console
$ kernelcontract doctor
KernelContract 0.1.0a4 - doctor
============================================
PASS  Current Python (control environment)
      Python 3.12.10 is executable.
INFO  Server interpreter not inferred
      The current Python is used as a control environment; it is not assumed to be the actual Jupyter server Python.
      Next: Re-run with --server-python /absolute/path/to/server/python when Jupyter runs from another environment.
PASS  Discover Jupyter kernels
      Found 1 registered kernelspec(s).
PASS  python3: executable exists
      Resolved kernelspec executable to C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe.
PASS  python3: ipykernel importable
      Python 3.12.10 starts and ipykernel is installed (version 6.29.5).

Summary: 4 pass, 1 info, 0 warning(s), 0 failure(s).
Overall status: PASS
KernelContract did not modify packages or environments.
```

### 2. Validate notebook kernel metadata: `kernelcontract notebook`

Check whether a notebook file's declared kernel exists and matches registered kernelspecs:

```console
$ kernelcontract notebook analysis.ipynb
KernelContract 0.1.0a4 - notebook
============================================
PASS  Current Python (control environment)
      Python 3.12.10 is executable.
INFO  Server interpreter not inferred
      The current Python is used as a control environment; it is not assumed to be the actual Jupyter server Python.
      Next: Re-run with --server-python /absolute/path/to/server/python when Jupyter runs from another environment.
PASS  Discover Jupyter kernels
      Found 1 registered kernelspec(s).
PASS  python3: executable exists
      Resolved kernelspec executable to C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe.
FAIL  Notebook kernel is registered
      Notebook requests kernel 'pytorch-env', but that name is not in the discovered kernelspec list.
      Next: Register the intended kernel or select an installed kernel in Jupyter and save the notebook. Do not assume a fallback kernel is equivalent.

Summary: 3 pass, 1 info, 0 warning(s), 1 failure(s).
Overall status: FAIL
KernelContract did not modify packages or environments.
```

*In this example, KernelContract caught a missing `pytorch-env` kernel before the user ran the notebook, preventing silent fallback to an unintended environment.*

---

## Key capabilities

* **Kernelspec discovery:** Enumerates registered Jupyter kernels using standard `jupyter kernelspec list --json`.
* **Executable resolution:** Resolves the `argv[0]` command across platforms, including Windows `PATHEXT` (`.exe`, `.cmd`, `.bat`), quoted paths with spaces, and environment variable expansion.
* **Environment inspection:** Checks that Python interpreters can start and verifies the presence of `ipykernel`.
* **Notebook validation:** Confirms that notebook `.ipynb` files reference valid, registered kernels and detects display-name drift.
* **Structured JSON output:** Export versioned machine-readable reports (`--json`) for automation, pre-commit hooks, and CI pipelines.
* **Strict CI mode:** Exit non-zero on warnings with `--strict` (failures always exit with code 1; passes/warnings exit 0 by default).
* **Companion package checks:** Detects presence of `jupyterlab_widgets` when the control environment contains JupyterLab and a probed kernel contains `ipywidgets`.
* **Opt-in external probing:** Probes external Python kernels only when explicitly authorized with `--probe-python`.

---

## Capability summary

| Capability | What KernelContract does |
|---|---|
| **Kernelspec Discovery** | Queries Jupyter CLI for registered kernelspecs; returns structured discovery errors if output is missing or malformed. |
| **Executable Verification** | Validates that `argv[0]` resolves to a real executable file on disk without executing third-party code. |
| **Environment Drift Detection** | Compares the control Python prefix with the kernel Python prefix to detect cross-environment execution. |
| **Notebook Validation** | Reads notebook JSON metadata and verifies that the requested `kernelspec.name` is registered on the local machine. |
| **CI & Tooling Integration** | Provides predictable exit codes (`0` for pass/warn, `1` for fail, `--strict` fails on warn) and versioned JSON output. |
| **Remediation Suggestions** | Supplies concrete, human-readable `Next:` steps for every failing or warning check. |
| **System Modification** | **None.** Operates strictly read-only; never installs, uninstalls, or modifies files or environments. |

---

## Scope and boundaries

* **Strictly read-only:** KernelContract will not repair environments, modify paths, install packages, or rewrite notebook files automatically.
* **Execution guarantee:** Passing KernelContract checks confirms kernel configuration integrity; it does not guarantee that a notebook's internal code will execute without Python runtime errors.
* **Server vs. control interpreter:** KernelContract cannot automatically determine which Python interpreter runs an existing Jupyter server process across all containers, services, and launchers. By default, the Python interpreter running KernelContract acts as the **control environment**. To specify the server Python interpreter explicitly, use:
  ```bash
  kernelcontract doctor --server-python /path/to/server/python
  ```
* **External interpreter probing:** By default, KernelContract only executes package inspection on the control Python interpreter. External interpreters are not executed unless you pass `--probe-python`.

---

## Security and privacy

* **100% Local:** Runs entirely on your machine. No telemetry, analytics, or remote network calls are made.
* **Bounded execution:** Subprocess checks employ strict execution timeouts to prevent hanging processes.
* **No shell execution:** Commands are executed directly as argument vectors (`shell=False`).
* **Security boundary on `--probe-python`:** Because a kernelspec `argv` can point to any program, running `--probe-python` executes that interpreter. Only pass `--probe-python` for kernelspecs and environments you trust.

---

## Development

KernelContract has zero external runtime dependencies and requires Python 3.10+.

```bash
git clone https://github.com/Ayushxsingh100/kernelcontract.git
cd kernelcontract
python -m venv .venv
# Activate .venv (Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate)
python -m pip install -e ".[test]"
python -m unittest discover -s tests -v
python -m pytest -q
```

Issues and feature requests are welcome at [GitHub Issues](https://github.com/Ayushxsingh100/kernelcontract/issues).

---

## Status and metadata

* **Release candidate:** `0.1.0a4` (Pre-release candidate)
* **Current PyPI release:** [`0.1.0a3`](https://pypi.org/project/kernelcontract/0.1.0a3/)
* **PyPI project page:** [https://pypi.org/project/kernelcontract/](https://pypi.org/project/kernelcontract/)
* **GitHub releases:** [https://github.com/Ayushxsingh100/kernelcontract/releases](https://github.com/Ayushxsingh100/kernelcontract/releases)
* **GitHub repository:** [https://github.com/Ayushxsingh100/kernelcontract](https://github.com/Ayushxsingh100/kernelcontract)
* **License:** [MIT License](https://github.com/Ayushxsingh100/kernelcontract/blob/master/LICENSE)

> **Note on PyPI metadata:** Package distributions published to PyPI are permanent and immutable. Version `0.1.0a3` on PyPI was built and published from release tag `v0.1.0a3`. Candidate `0.1.0a4` synchronizes this redesigned documentation so that subsequent publication will update the long description displayed on PyPI.
