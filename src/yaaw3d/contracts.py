from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AnswerKind = Literal["A", "B", "C", "CUSTOM"]
StateName = Literal[
    "INTAKE",
    "AMBIGUITY_REVIEW",
    "BRIEF_LOCKED",
    "PLANNING",
    "BUILDING",
    "CRITIQUE",
    "VALIDATION",
    "CORRECTION",
    "EXPORT",
    "COMPLETE",
    "BLOCKED",
]
QADomain = Literal["visual", "technical", "motion", "material", "cinematography"]


@dataclass(frozen=True)
class Choice:
    key: str
    label: str


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    choices: tuple[Choice, Choice, Choice]
    recommendation: str
    required: bool = True
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "choices": [asdict(c) for c in self.choices],
            "recommendation": self.recommendation,
            "required": self.required,
            "rationale": self.rationale,
            "custom": "Provide an exact answer if A/B/C does not fit.",
        }


@dataclass
class Answer:
    question_id: str
    choice: AnswerKind
    custom: str | None = None

    def resolved_value(self, question: Question) -> str:
        if self.choice == "CUSTOM":
            if not self.custom or not self.custom.strip():
                raise ValueError(f"{self.question_id}: CUSTOM requires non-empty custom text")
            return self.custom.strip()
        by_key = {c.key: c.label for c in question.choices}
        if self.choice not in by_key:
            raise ValueError(f"{self.question_id}: invalid choice {self.choice!r}")
        return by_key[self.choice]


@dataclass
class ProductionBrief:
    job_id: str
    version: int
    source_request: str
    status: Literal["draft", "locked"] = "draft"
    requirements: dict[str, str] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    acceptance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JobState:
    job_id: str
    state: StateName = "INTAKE"
    brief_version: int = 0
    plan_version: int = 0
    iteration: int = 0
    critic_pass: bool = False
    validator_pass: bool = False
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QAReport:
    domain: QADomain
    passed: bool
    findings: list[str]
    artifact_id: str = "current"
    evidence: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("QAReport.artifact_id must be non-empty")
        if not self.passed and not self.findings:
            raise ValueError("failed QA reports require at least one finding")


@dataclass
class CorrectionTicket:
    iteration: int
    owner: str
    findings: list[str]
    required_changes: list[str]
    acceptance_checks: list[str]
    artifact_id: str = "current"
    evidence: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    milestone_id: str
    artifact_id: str
    passed: bool
    outputs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ExportReport:
    artifact_id: str
    passed: bool
    files: list[str]
    evidence: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("ExportReport.artifact_id must be non-empty")
        if self.passed and not self.files:
            raise ValueError("passed exports require at least one file")
        if not self.passed and not self.findings:
            raise ValueError("failed exports require findings")
