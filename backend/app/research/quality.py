"""Research quality control: a check on the research itself, run after every report is assembled.

It answers the questions the specification asks. Did every conclusion rest on a source? Did verification run?
Is anything stale or contradictory? Was the historical sample big enough? Did anything appear in the report that
no agent measured? The answer is a PASS, WARN or FAIL with the reasons attached, so a weak report cannot look
the same as a strong one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.research.contracts import ResearchReport

# Words that would turn a research report into a recommendation or a promise.
FORBIDDEN_CLAIMS = re.compile(
    r"\b(guarantee[sd]?|guaranteed|will (?:rise|fall|go up|go down)|sure ?shot|certain to|risk[- ]free|"
    r"multibagger|jackpot|can't lose|cannot lose)\b",
    re.I,
)
Status = str  # PASS | WARN | FAIL


@dataclass(frozen=True, slots=True)
class QualityCheck:
    key: str
    status: Status
    message: str
    detail: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class QualityReport:
    status: Status
    checks: list[QualityCheck]

    @property
    def issues(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status != "PASS"]


def _worst(statuses: list[Status]) -> Status:
    if "FAIL" in statuses:
        return "FAIL"
    return "WARN" if "WARN" in statuses else "PASS"


def check_report(report: ResearchReport) -> QualityReport:
    checks: list[QualityCheck] = []

    # 1. every assessed score component must cite at least one piece of evidence
    unsupported = [c.label for c in report.score.components if c.available and not c.evidence]
    checks.append(
        QualityCheck(
            key="components_have_evidence",
            status="FAIL" if unsupported else "PASS",
            message=(
                f"{len(unsupported)} scored component(s) carry no evidence: {', '.join(unsupported)}"
                if unsupported
                else "Every scored component carries its evidence."
            ),
            detail={"components": unsupported},
        )
    )

    # 2. evidence that names a source must name one the report actually lists
    known = {s.key for s in report.sources}
    dangling = sorted(
        {
            e.source_key
            for c in report.score.components
            for e in c.evidence
            if e.source_key and e.source_key not in known
        }
    )
    checks.append(
        QualityCheck(
            key="sources_resolve",
            status="FAIL" if dangling else "PASS",
            message=(
                f"Evidence cites {len(dangling)} source(s) the report does not list: {', '.join(dangling)}"
                if dangling
                else "Every cited source is listed in the report."
            ),
        )
    )

    # 3. verification
    ran = bool(report.verification.claims)
    conflicts = report.verification.conflicts_found
    checks.append(
        QualityCheck(
            key="verification_ran",
            status="PASS" if ran else "WARN",
            message=(
                "Data verification ran." if ran else "Data verification did not run at this research depth."
            ),
        )
    )
    if conflicts:
        checks.append(
            QualityCheck(
                key="no_conflicts",
                status="WARN",
                message=f"{conflicts} verification claim(s) found conflicting values; no value was chosen.",
            )
        )

    # 4. freshness and data provenance
    stale_codes = {w.code for w in report.warnings}
    if "STALE_DATA" in stale_codes:
        checks.append(
            QualityCheck(key="data_fresh", status="WARN", message="Market data was stale when this ran.")
        )
    if report.is_synthetic:
        checks.append(
            QualityCheck(
                key="real_data",
                status="WARN",
                message="Built on synthetic test data, so no conclusion about the real market can be drawn.",
            )
        )

    # 5. historical sample
    if report.historical is not None:
        matched = report.historical.matched
        checks.append(
            QualityCheck(
                key="historical_sample",
                status="PASS" if matched else "WARN",
                message=(
                    f"Historical sample is adequate ({matched.occurrences} occurrences)."
                    if matched
                    else "No historical sample of this setup was large enough, so no historical edge is claimed."
                ),
            )
        )

    # 6. score coverage
    coverage = report.score_coverage_pct
    checks.append(
        QualityCheck(
            key="score_coverage",
            status="PASS" if coverage >= 90 else "WARN",
            message=f"The score covers {coverage:.0f}% of the scoring weights.",
            detail={"not_assessed": [c.label for c in report.score.components if not c.available]},
        )
    )

    # 7. nothing in the narrative may promise an outcome
    narrative = " ".join([*report.why_listed, *report.risks, *report.invalidation, *report.labels.values()])
    offending = sorted(set(m.group(0).lower() for m in FORBIDDEN_CLAIMS.finditer(narrative)))
    checks.append(
        QualityCheck(
            key="no_unsupported_claims",
            status="FAIL" if offending else "PASS",
            message=(
                f"The report promises an outcome: {', '.join(offending)}"
                if offending
                else "The report states evidence and conditions, not predictions."
            ),
        )
    )

    # 8. the three headline numbers must be present and independent
    missing_numbers = [
        name
        for name, value in (
            ("research score", report.research_score),
            ("data confidence", report.data_confidence),
            ("risk score", report.risk_score),
        )
        if value is None
    ]
    checks.append(
        QualityCheck(
            key="three_numbers",
            status="WARN" if missing_numbers else "PASS",
            message=(
                f"Not reported: {', '.join(missing_numbers)}."
                if missing_numbers
                else "Research score, data confidence and risk score are all reported."
            ),
        )
    )

    return QualityReport(status=_worst([c.status for c in checks]), checks=checks)
