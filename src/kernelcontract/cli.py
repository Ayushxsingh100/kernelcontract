"""Command-line interface for KernelContract."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from . import __version__
from .diagnostics import run_diagnostics
from .models import Report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kernelcontract",
        description="Read-only diagnostics for Jupyter kernels and Python environments.",
        epilog="No packages are installed, removed, or modified by this tool.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check registered Jupyter kernels and environment drift")
    doctor.add_argument("--server-python", help="path to the Python interpreter used by the Jupyter server (optional)")
    doctor.add_argument("--json", action="store_true", dest="json_output", help="print machine-readable JSON")
    doctor.add_argument("--strict", action="store_true", help="exit non-zero for warnings as well as failures")
    doctor.add_argument("--probe-python", action="store_true", help="execute each registered Python kernel's argv[0] for package checks; use only with trusted kernelspecs")

    notebook = subparsers.add_parser("notebook", help="check a notebook's declared kernel against registered kernels")
    notebook.add_argument("path", help="path to a .ipynb file")
    notebook.add_argument("--server-python", help="path to the Python interpreter used by the Jupyter server (optional)")
    notebook.add_argument("--json", action="store_true", dest="json_output", help="print machine-readable JSON")
    notebook.add_argument("--strict", action="store_true", help="exit non-zero for warnings as well as failures")
    notebook.add_argument("--probe-python", action="store_true", help="execute each registered Python kernel's argv[0] for package checks; use only with trusted kernelspecs")
    return parser


def render_text(report: Report) -> str:
    lines = ["KernelContract {} - {}".format(__version__, report.command), "=" * 44]
    for check in report.checks:
        lines.append("{:<5} {}".format(check.status, check.title))
        lines.append("      {}".format(check.message))
        for suggestion in check.suggestions:
            lines.append("      Next: {}".format(suggestion))
    counts = report.counts
    lines.extend([
        "",
        "Summary: {pass_count} pass, {info_count} info, {warn_count} warning(s), {fail_count} failure(s).".format(
            pass_count=counts["pass"], info_count=counts["info"], warn_count=counts["warn"], fail_count=counts["fail"]
        ),
        "Overall status: {}".format(report.overall_status),
        "KernelContract did not modify packages or environments.",
    ])
    return "\n".join(lines)


def exit_code(report: Report, strict: bool = False) -> int:
    if any(check.status == "FAIL" for check in report.checks):
        return 1
    if strict and any(check.status == "WARN" for check in report.checks):
        return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    notebook_path = args.path if args.command == "notebook" else None
    report = run_diagnostics(
        command=args.command,
        notebook_path=notebook_path,
        server_python=args.server_python,
        probe_python_kernels=args.probe_python,
    )
    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return exit_code(report, strict=args.strict)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
