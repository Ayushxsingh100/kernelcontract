# KernelContract

**Read-only diagnostics for Jupyter kernels and Python environments.**

KernelContract inspects registered Jupyter kernelspecs, checks whether their configured executables resolve, probes Python kernel environments, and compares notebook kernel metadata with the kernels available to the current Jupyter CLI. It reports likely issues and safe next steps without modifying the machine.

> **Alpha software (0.1.0a1).** This is an initial, deliberately narrow implementation. It does not diagnose every JupyterLab extension, certify exact widget-version compatibility, infer the interpreter of an already-running Jupyter server, or guarantee that a notebook will execute successfully. The project name is provisional and has not been trademark- or registry-cleared.

## Quick start

KernelContract requires Python 3.10 or newer. **The package has not been published to PyPI yet.** To try this checkout locally:

```bash
python -m pip install -e .
kernelcontract doctor
```

After a release is published, the intended end-user install command will be:

```bash
python -m pip install kernelcontract
kernelcontract doctor
```

KernelContract does not require a third-party Python package at runtime, but it expects the environment to expose the `jupyter` command and the kernels you want to inspect.

To inspect a notebook's declared kernel:

```bash
kernelcontract notebook notebooks/analysis.ipynb
```

For structured output suitable for scripts or CI:

```bash
kernelcontract doctor --json
kernelcontract notebook notebooks/analysis.ipynb --json
```

To fail CI when the report contains either warnings or failures:

```bash
kernelcontract doctor --strict
```

By default, a `FAIL` makes the command exit with status 1. Warnings do not fail the command unless `--strict` is used.

To probe every registered Python kernel, including interpreters outside the current environment:

```bash
kernelcontract doctor --probe-python
```

Use `--probe-python` only when you trust the registered kernelspecs. A kernelspec's executable can be any program, so probing it can execute code from that environment. By default, KernelContract probes the current control interpreter and only probes other kernels when their resolved executable is the same interpreter.

## What it checks

- Whether the Jupyter CLI can enumerate kernelspecs using `jupyter kernelspec list --json`.
- Whether each registered kernelspec has a resolvable `argv[0]` executable.
- Whether the current Python (and, when explicitly enabled, other Python kernels) can start and whether `ipykernel` is installed in that interpreter.
- Whether a probed kernel's Python prefix differs from the control interpreter.
- A narrow widget companion check when the control environment contains JupyterLab and a kernel contains `ipywidgets`.
- Whether a `.ipynb` file declares a kernel name that is currently registered.
- Whether the notebook's stored display name differs from the registered kernel display name.

## Server and kernel environments

KernelContract cannot reliably infer which Python interpreter belongs to an already-running Jupyter server across all launchers, operating systems, containers, and remote setups. By default, it uses the Python that launches KernelContract as its **control environment**; this is not claimed to be the server interpreter.

If you know the server interpreter, pass it explicitly:

```bash
kernelcontract doctor --server-python /absolute/path/to/server/python
```

The `--server-python` option changes which interpreter is used for the control-side package checks and environment comparison. If the server and kernels intentionally live in separate environments, a drift warning is not automatically a defect.

## Safety and privacy

- No telemetry or network calls are made by KernelContract itself.
- No package installation, upgrade, removal, or environment rewrite is performed.
- Interpreter probes are local subprocesses with timeouts.
- Kernel commands are never executed through a shell. For Python kernels, the executable is invoked with a fixed probe that checks selected package metadata. The current control interpreter is probed by default; other Python kernel interpreters require `--probe-python` unless they resolve to the same executable.
- The JSON report includes filesystem paths and package versions. Review output before sharing it publicly.

Note: the Jupyter command may load its installed extensions/configuration as part of normal Jupyter startup. Run the tool only in environments you trust.

## Development

```bash
git clone <your-repository-url>
cd kernelcontract
python -m venv .venv
# Activate .venv using the command for your operating system.
python -m pip install -e ".[test]"
python -m pytest
python -m kernelcontract doctor
```

The source uses a `src/` layout and the CLI is defined in `pyproject.toml`.

## Limits and roadmap

This release is intentionally a diagnostic baseline, not an authoritative compatibility database. Planned next steps should be driven by reproduced failures and user feedback:

1. Test the checks on Windows, macOS, Linux, and common conda/venv setups.
2. Add fixture-based integration tests for real kernelspec layouts.
3. Validate the widget companion warning against supported JupyterLab/ipywidgets combinations.
4. Consider a GitHub Action only after the JSON schema and exit-code behavior stabilize.

## Status

- Version: `0.1.0a1`
- License: MIT
- Stability: Alpha
