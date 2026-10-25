"""Small, dependency-free data models for diagnostic results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


VALID_STATUSES = {"PASS", "INFO", "WARN", "FAIL"}


@dataclass
class Check:
    """One diagnostic observation."""

    id: str
    status: str
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.status = self.status.upper()
        if self.status not in VALID_STATUSES:
            raise ValueError("status must be one of PASS, INFO, WARN, FAIL")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    """A complete diagnostic report."""

    command: str
    checks: List[Check] = field(default_factory=list)
    schema_version: str = "1.0"

    def add(self, check: Check) -> None:
        self.checks.append(check)

    @property
    def counts(self) -> Dict[str, int]:
        return {
            status.lower(): sum(1 for check in self.checks if check.status == status)
            for status in ("PASS", "INFO", "WARN", "FAIL")
        }

    @property
    def overall_status(self) -> str:
        if any(check.status == "FAIL" for check in self.checks):
            return "FAIL"
        if any(check.status == "WARN" for check in self.checks):
            return "WARN"
        return "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": "kernelcontract",
            "command": self.command,
            "status": self.overall_status,
            "summary": self.counts,
            "checks": [check.to_dict() for check in self.checks],
        }
