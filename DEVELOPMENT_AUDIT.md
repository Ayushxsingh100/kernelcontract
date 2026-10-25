# KernelContract Development Audit — 0.1.0a2 Candidate

## 1. Executive Summary

An audit and cross-platform verification of KernelContract version `0.1.0a2` (pre-release candidate) was conducted.
KernelContract is an alpha diagnostic utility designed to perform read-only health checks on Jupyter kernelspecs, Python environments, and notebook metadata.

The architectural foundation of KernelContract is clean, lightweight, and adheres to zero runtime external dependencies. However, several real defects, cross-platform edge case vulnerabilities, and test coverage gaps were discovered during static inspection, execution on Windows, and edge-case testing.

---

## 2. Environment and Baseline Status

- **Operating System:** Windows 11 / Windows Server (PowerShell)
- **Python Version:** 3.12.10 (64-bit)
- **Pip Version:** 25.0.1
- **Pytest:** Not installed in global Python environment; test runner uses standard library `unittest` (`python -m unittest discover -s tests -v`).
- **Git Repository:** Not initialized in current workspace (`fatal: not a git repository`).
- **Wheel Build:** Successful (`pip wheel . --no-deps -w dist` produced `kernelcontract-0.1.0-py3-none-any.whl`).
- **Clean Venv Installation:** Verified inside `.venv_test`; console entrypoint `kernelcontract` executed successfully.

---

## 3. Verified Working Behavior

1. **Packaging & Metadata:**
   - Package follows standard `src/` layout.
   - `pyproject.toml` correctly configures setuptools backend, scripts entrypoint (`kernelcontract = "kernelcontract.cli:entrypoint"`), and classifiers.
   - Wheel builds cleanly and installs in an isolated Python virtual environment.
2. **Core Data Models (`src/kernelcontract/models.py`):**
   - `Check` enforces valid statuses (`PASS`, `INFO`, `WARN`, `FAIL`).
   - `Report` aggregates checks, computes counts, and resolves `overall_status` (`FAIL` > `WARN` > `PASS`).
   - Serialization to dict via `to_dict()` produces valid structure matching `schema_version = "1.0"`.
3. **CLI Interface (`src/kernelcontract/cli.py`):**
   - Commands `kernelcontract doctor` and `kernelcontract notebook <path>` are parsed properly.
   - Flags `--json`, `--strict`, `--server-python`, `--probe-python`, and `--version` are wired up.
   - Read-only contract: No filesystem mutations, package installations, or environment writes are performed.
4. **Current Python Probe (`src/kernelcontract/discovery.py`):**
   - Safely queries Python version, sys.prefix, and checks presence of `ipykernel`, `ipywidgets`, `jupyterlab`, `jupyterlab_widgets`, `notebook`, `widgetsnbextension` without modifying environments.
5. **Initial Unit Tests:**
   - 16 unit tests passed when `PYTHONPATH=src` was provided.

---

## 4. Claimed but Unverified Behavior

1. **Jupyter Test Discovery Without `PYTHONPATH`:**
   - `BUILD_STATUS.md` claimed running `python -m unittest discover -s tests -v` works. In reality, on a standard checkout without editable installation, `unittest` fails with `ModuleNotFoundError: No module named 'kernelcontract'` because `src/` is not on the search path by default.
2. **Cross-Platform Readiness:**
   - `BUILD_STATUS.md` explicitly noted that Windows and macOS testing had not been conducted. Real testing on Windows revealed several path, extension, and console encoding issues.
3. **Execution Against Malformed Notebooks:**
   - Claimed to validate notebook metadata, but testing with malformed metadata structures revealed unhandled Python exceptions.

---

## 5. Actual Defects Identified

### Defect 1: Unhandled Exception on Malformed Notebook Metadata (`TypeError: unhashable type: 'list'`)
- **Location:** `src/kernelcontract/diagnostics.py` (lines 284–295)
- **Description:** If a notebook contains malformed metadata where `metadata["kernelspec"]["name"]` is a list, dict, or other non-hashable type (or non-string), evaluating `elif declared_name not in kernels:` raises `TypeError: unhashable type: 'list'`.
- **Impact:** The CLI crashes with an unhandled exception instead of reporting a structured diagnostic finding.
- **Fix:** Explicitly validate that `kernelspec` is a mapping and `name` is a non-empty string before testing membership in `kernels`.

### Defect 2: Windows Executable Resolution Fails Without `.exe` Extension
- **Location:** `src/kernelcontract/discovery.py` (`resolve_executable`, lines 50–56)
- **Description:** When an `argv[0]` contains directory separators (e.g. `C:/venvs/myenv/Scripts/python`), `has_path_component` is `True`. The code only checks `candidate.is_file()`. On Windows, executables require extensions such as `.exe`. `Path.is_file()` returns `False` for `python` when the file on disk is `python.exe`.
- **Impact:** Valid Windows kernelspecs referencing Python interpreters without explicit `.exe` fail resolution.
- **Fix:** When `candidate.is_file()` is `False`, fall back to `shutil.which(expanded)` which checks `PATHEXT` on Windows even for path-qualified executables.

### Defect 3: Quoted Executable Paths in Kernelspec `argv[0]` Fail Resolution
- **Location:** `src/kernelcontract/discovery.py` (`resolve_executable`)
- **Description:** Kernelspecs on Windows often contain quoted paths with spaces, e.g. `"\"C:\\Program Files\\Python\\python.exe\""`. `Path("\"...\"").is_file()` returns `False`, and `shutil.which` fails to resolve quoted strings.
- **Impact:** Kernelspecs with quoted argv0 fail to resolve, reporting false `FAIL` checks.
- **Fix:** Strip leading and trailing quotation marks from `argv0` before resolution.

### Defect 4: Unicode Character Corruption in Console Output on Windows
- **Location:** `src/kernelcontract/cli.py` (`render_text`, line 40)
- **Description:** The header line uses an em-dash (`"KernelContract {} — {}"`). In standard Windows command prompts and PowerShell environments with non-UTF-8 code pages (e.g., CP1252), this renders as corrupted replacement characters (``) or raises `UnicodeEncodeError` when redirected.
- **Impact:** Poor user experience and potential pipeline crashes when output is redirected to files on Windows.
- **Fix:** Use standard ASCII hyphen `-` in the text renderer header.

### Defect 5: Unhandled `UnicodeDecodeError` in Subprocess Execution on Windows
- **Location:** `src/kernelcontract/discovery.py` (`discover_kernelspecs` & `probe_python`)
- **Description:** `subprocess.run(..., capture_output=True, text=True)` defaults to the system locale encoding (`locale.getpreferredencoding()`, often `cp1252` on Windows). If Jupyter or a probed interpreter emits characters outside CP1252 to stdout or stderr, `subprocess.run` raises `UnicodeDecodeError`.
- **Impact:** Crash during discovery or interpreter probing.
- **Fix:** Specify `encoding="utf-8", errors="replace"` in `subprocess.run`.

### Defect 6: Potential `_same_path` False Matches on Empty Strings
- **Location:** `src/kernelcontract/diagnostics.py` (`_same_path`, lines 15–19)
- **Description:** `os.path.realpath("")` returns `os.getcwd()` in Python. If either argument is empty or `None`, `_same_path` could incorrectly compare against the current working directory.
- **Impact:** False positive match between an empty probe result and an executable in the current working directory.
- **Fix:** Guard against falsy/empty paths and return `False` if either input is empty.

### Defect 7: Fragile Probe Output Parsing on Noisy Interpreters
- **Location:** `src/kernelcontract/discovery.py` (`probe_python`, line 158)
- **Description:** `json.loads(proc.stdout.strip().splitlines()[-1])` assumes the very last stdout line is the probe JSON. If an environment banner, sitecustomize hook, or atexit handler prints output after the JSON line, decoding fails.
- **Impact:** Probe fails unexpectedly on legitimate interpreters that emit trailing stdout messages.
- **Fix:** Use a unique sentinel marker prefix for the JSON payload and search for it in `stdout.splitlines()`.

### Defect 8: Missing Kernelspec Directory and `kernel.json` Validation
- **Location:** `src/kernelcontract/diagnostics.py`
- **Description:** If a kernelspec entry has a stale or missing `resource_dir`, or if `kernel.json` is missing or malformed JSON, `diagnostics.py` did not explicitly check the filesystem directory or validate the `kernel.json` file on disk.
- **Impact:** Missing or malformed kernelspec directories/files were not specifically diagnosed.
- **Fix:** Add filesystem existence and JSON parsing checks for `resource_dir` and `kernel.json`.

### Defect 9: `--server-python` Flexibility
- **Location:** `src/kernelcontract/diagnostics.py` (lines 63–74)
- **Description:** `--server-python` only checked `os.path.isfile(control_python)`. If a user provided a command name (e.g. `python`) or a path without `.exe` on Windows, it failed immediately.
- **Impact:** Inconvenient CLI experience requiring exact absolute paths with `.exe`.
- **Fix:** Attempt resolution with `resolve_executable(server_python)` when `--server-python` is specified.

---

## 6. Action Taken and Fixes Implemented

1. **Defects 1–9 resolved across `src/kernelcontract/`:**
   - `src/kernelcontract/discovery.py`:
     - Added quote stripping and `shutil.which` PATHEXT fallback to `resolve_executable` for Windows paths omitting `.exe`.
     - Added `encoding="utf-8", errors="replace"` to all `subprocess.run` invocations.
     - Hardened JSON extraction in `discover_kernelspecs` to extract JSON from amidst stdout log lines.
     - Integrated sentinel marker `__KERNELCONTRACT_PROBE_JSON__:` into `probe_python` to isolate probe JSON from noisy interpreter startup banners.
     - Broadened `is_python_kernel` to infer Python kernel status from `argv` when `language` is omitted.
   - `src/kernelcontract/diagnostics.py`:
     - Hardened `_same_path` to reject empty or `None` paths, preventing false equality matches against `cwd`.
     - Validated existence of kernelspec `resource_dir` and verified that `kernel.json` exists and contains valid JSON.
     - Validated that `argv` is a non-empty list and `argv[0]` is a non-empty string.
     - Added type-safe checking for notebook `metadata`, `kernelspec`, and `kernelspec.name` to prevent unhandled exceptions on non-dict / non-string structures.
     - Added resolution of `--server-python` via `resolve_executable`.
   - `src/kernelcontract/cli.py`:
     - Replaced unicode em-dash with ASCII hyphen in text report header to prevent encoding errors on non-UTF-8 terminals.
   - `tests/`:
     - Added `test_cli.py` and expanded `test_models.py`, `test_discovery.py`, and `test_diagnostics.py`.
     - Added automatic `src/` bootstrap across test modules so `python -m unittest discover -s tests -v` succeeds out-of-the-box without requiring manual `PYTHONPATH` configuration.

---

## 7. Automated Test Verification Results

All tests executed via:
`python -m unittest discover -s tests -v`

**Total tests:** 52
**Passed:** 52
**Failures:** 0
**Errors:** 0

Coverage areas verified:
- Model statuses, counts, precedence, and JSON serialization.
- CLI argument parsing, text/JSON rendering, exit code semantics (standard and strict mode).
- Jupyter discovery missing, timeout, non-zero return code, malformed JSON, and JSON surrounded by logs.
- Executable resolution for current Python, missing paths, quoted paths with spaces, and Windows PATHEXT extensions.
- Interpreter probing for timeout, failure, and sentinel extraction from noisy banners.
- Kernelspec validation for missing directories, missing `kernel.json`, and malformed JSON.
- Notebook inspection for missing files, directory paths, invalid JSON syntax, root non-object, metadata non-object, malformed kernelspec, missing name, unregistered kernels, and display name drift.
- Security-sensitive opt-in probing (untrusted kernels skipped by default unless `--probe-python` is specified).

---

## 8. Quality and Security Review Pass

1. **Subprocess Safety:**
   - Confirmed `shell=False` is used in every subprocess invocation (`subprocess.run`).
   - Arguments are passed as lists without shell interpolation.
   - Bounded timeouts (`timeout=15.0` for Jupyter discovery, `timeout=8.0` for interpreter probes).
2. **Opt-in Probing:**
   - Non-control Python kernels are NEVER executed unless the user explicitly passes `--probe-python`.
   - Probing the control interpreter runs a fixed, read-only script querying `importlib.metadata` and `sys`.
3. **No Side Effects:**
   - KernelContract modifies no files, no packages, and no environment state.
   - All operations are strictly read-only diagnostics.
4. **Cross-Platform Compatibility:**
   - ASCII-only text report header avoids Windows CP1252 / pipe redirection encoding crashes.
   - Subprocess stdout/stderr uses `utf-8` decoding with replacement characters.
   - File paths with spaces and Windows backslashes are resolved cleanly.

---

## 9. Remote CI Validation and Candidate 0.1.0a2 Hardening

Following the creation of the public repository (`https://github.com/Ayushxsingh100/kernelcontract`), remote GitHub Actions CI executed on Ubuntu and Windows across Python 3.10 through 3.13.

### Defects Discovered and Fixed in 0.1.0a2:
1. **Windows PATHEXT Extension Resolution on Python 3.10 & 3.11:**
   - On Windows with Python < 3.12, `shutil.which` failed to resolve commands with mixed path separators (e.g. `$CUSTOM_BIN/python`).
   - Fix: Normalized path separators via `os.path.normpath` and explicitly iterated Windows `PATHEXT` (`.COM`, `.EXE`, `.BAT`, `.CMD`) directly with `Path`, guaranteeing uniform resolution across all Python versions.
2. **Linux Symlink Canonicalization in Test Assertions:**
   - On Ubuntu GitHub-hosted runners, `sys.executable` was a symlink to versioned interpreter binaries.
   - Fix: Updated `test_resolve_quoted_executable_with_spaces` to compare against `str(Path(sys.executable).resolve())` and assert filesystem equivalence via `os.path.samefile()`.
3. **GitHub Actions Modernization:**
   - Modernized workflow actions to `actions/checkout@v7` and `actions/setup-python@v7` to eliminate Node.js 20 deprecation warnings on current runners.

### Tag Integrity:
- The existing tag `v0.1.0a1` remains intact pointing to the initial release commit `0f32ae55ec4d3b5cd10b1b36da986d8ae07b55a4`.
- Version `0.1.0a2` represents the next alpha pre-release candidate.


