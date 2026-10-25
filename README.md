# KernelContract

**Local-first, read-only diagnostics for Jupyter kernels, kernelspecs, and notebook environments.**

KernelContract inspects registered Jupyter kernelspecs, checks whether their configured executables resolve, probes Python kernel environments, and compares notebook kernel metadata with the kernels available to the current Jupyter CLI. It reports likely configuration mismatches, missing interpreters, and safe next steps without modifying the machine.

> **Alpha Software — Candidate 0.1.0a3 (Latest tagged pre-release: [v0.1.0a2](https://github.com/Ayushxsingh100/kernelcontract/releases/tag/v0.1.0a2)).** KernelContract is an early-stage diagnostic tool under active development. The latest published GitHub pre-release is `v0.1.0a2`, and the current default branch is preparing candidate `0.1.0a3` for PyPI Trusted Publishing. It has **not** yet been published to PyPI. The project name is provisional and has not been trademark- or registry-cleared.

---

## Quick start

### Prerequisites

* **Python 3.10 or newer.**
* **Jupyter CLI on PATH:** KernelContract has zero external runtime dependencies (it uses the Python standard library only), but it requires that the `jupyter` command is available on your `PATH` (such as via `jupyter-core`) to discover registered kernels via `jupyter kernelspec list --json`.

### End-user installation (pre-release)

While PyPI publication remains pending, install the tagged alpha pre-release directly from GitHub using `pip`:

```bash
python -m pip install "git+https://github.com/Ayushxsingh100/kernelcontract.git@v0.1.0a2"
```

Or install the latest development snapshot from the default `master` branch:

```bash
python -m pip install "git+https://github.com/Ayushxsingh100/kernelcontract.git"
```

> **Note on PyPI:** The command `pip install kernelcontract` is reserved for future distribution once the package is officially published to the Python Package Index.

---

## Core usage

### 1. Diagnose registered Jupyter kernels

Run the `doctor` command to inspect all discovered kernelspecs, verify their executables, and check the active Python environment:

```bash
kernelcontract doctor
```

### 2. Validate notebook kernel metadata

Inspect whether a `.ipynb` file's declared kernel exists and matches currently registered kernelspecs:

```bash
kernelcontract notebook path/to/notebook.ipynb
```

If the notebook requests an unavailable kernel or if the kernel's stored display name has drifted from disk, KernelContract reports the issue with actionable next steps.

### 3. Machine-readable JSON output

Produce structured, versioned JSON suitable for automated tooling, pre-commit hooks, or CI pipelines:

```bash
kernelcontract doctor --json
kernelcontract notebook path/to/notebook.ipynb --json
```

The JSON schema output includes `schema_version`, `status` (`PASS`, `WARN`, `FAIL`), check details, and specific remediation suggestions.

### 4. Strict CI mode

By default, `FAIL` makes the command exit with status 1, while warnings exit with status 0. To fail CI on warnings as well as failures, pass `--strict`:

```bash
kernelcontract doctor --strict
```

### 5. Probing external Python kernels (opt-in)

```bash
kernelcontract doctor --probe-python
```

* **Security Note:** By default, KernelContract only executes package inspection on the current control interpreter and kernels that resolve to the exact same executable. Interpreters outside the current environment are **not** executed unless you pass `--probe-python`. Use `--probe-python` only with kernelspecs and environments you trust.

---

## What it checks

* **CLI Discovery:** Whether the Jupyter CLI can enumerate kernelspecs using `jupyter kernelspec list --json`.
* **JSON Structure Safety:** Whether kernelspec outputs have valid root structures and dictionary objects.
* **Executable Resolution:** Whether each registered kernelspec has a resolvable `argv[0]` executable (including Windows `PATHEXT` resolution for `.exe`, `.cmd`, `.bat`, quoted paths with spaces, and environment variable expansion).
* **Environment Integrity:** Whether the control Python (and, when opted in, external Python kernels) can start and whether `ipykernel` is installed in that interpreter.
* **Environment Drift:** Whether a probed kernel's Python prefix differs from the control interpreter.
* **Widget Companion Check:** A narrow check for presence of `jupyterlab_widgets` when the control environment contains JupyterLab and a probed kernel contains `ipywidgets`.
* **Notebook Metadata Check:** Whether a notebook file declares a kernel name that is currently registered and whether the recorded display name matches the kernelspec on disk.

---

## Server vs. kernel environments

KernelContract cannot reliably infer which Python interpreter belongs to an already-running Jupyter server across diverse setups (e.g. systemd services, Docker containers, remote SSH tunnels, JupyterHub). By default, it uses the Python interpreter launching KernelContract as its **control environment**.

If you know the specific Python interpreter running the Jupyter server, pass it explicitly:

```bash
kernelcontract doctor --server-python /absolute/path/to/server/python
```

---

## Safety and privacy guarantees

* **Strictly Read-Only:** KernelContract modifies no packages, rewrites no files, and changes no configuration.
* **No Telemetry:** Zero analytics, telemetry, or network calls are made by KernelContract.
* **Bounded Subprocesses:** Subprocess probes use strict execution timeouts to avoid hanging indefinitely.
* **No Shell Execution:** Commands are executed directly with argument lists (`shell=False`).

---

## Development

To contribute or run the test suite locally from source:

```bash
git clone https://github.com/Ayushxsingh100/kernelcontract.git
cd kernelcontract
python -m venv .venv
# Activate .venv (Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate)
python -m pip install -e ".[test]"
python -m unittest discover -s tests -v
python -m pytest -q
```

---

## Status

* **Version:** `0.1.0a3` (alpha candidate; latest tagged pre-release: [`v0.1.0a2`](https://github.com/Ayushxsingh100/kernelcontract/releases/tag/v0.1.0a2))
* **Repository:** [https://github.com/Ayushxsingh100/kernelcontract](https://github.com/Ayushxsingh100/kernelcontract)
* **Pre-release Notes:** [v0.1.0a2 Release](https://github.com/Ayushxsingh100/kernelcontract/releases/tag/v0.1.0a2)
* **License:** [MIT](LICENSE)
* **Stability:** Alpha
