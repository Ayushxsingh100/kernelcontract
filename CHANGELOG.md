# Changelog

## 0.1.0a1 — unreleased

- Initial read-only Jupyter kernelspec and Python interpreter diagnostics.
- JSON output and strict exit mode for CI integration.
- Notebook metadata check for unavailable or renamed kernels.
- Hardened kernelspec executable resolution on Windows: support paths without explicit `.exe` via PATHEXT and handle quoted executable paths with spaces.
- Added validation for missing kernelspec resource directories, missing `kernel.json` files, and malformed kernelspec JSON.
- Fixed unhandled exception (`TypeError: unhashable type: 'list'`) when inspecting notebooks with malformed kernelspec metadata.
- Made console output encoding-safe on Windows by using standard ASCII hyphen instead of unicode em-dash.
- Protected subprocess outputs from `UnicodeDecodeError` on non-UTF-8 console code pages using `encoding="utf-8", errors="replace"`.
- Improved Python probe robustness with a unique sentinel marker to isolate JSON from noisy interpreter banners and logs.
- Added automatic test environment bootstrap for standard unittest discovery without requiring manual `PYTHONPATH`.
- Expanded automated unit test suite from 16 to 52 tests covering all diagnostic, discovery, CLI, and edge cases.
