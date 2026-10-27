"""Immutable recommendation contract and strict validation of untrusted output.

AI output is untrusted input. It is parsed into a ``RecommendationDraft`` (which holds no
money figures), then combined with deterministic savings from
``app.domain.analysis.features`` into a ``RecommendationContract``.

Errors carry a stable code and a field name, never the offending value, so raw AI content
cannot leak into logs (ADR-004).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from app.domain.analysis import features
from app.domain.common.money import Money
from app.domain.recommendations.exceptions import RecommendationDomainError

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})
DERIVED_PREFIX = "derived:"
MIN_ACTION_CONFIDENCE = Decimal("0.6")  # PLACEHOLDER: confirm with the team
MAX_ITEMS = 20  # PLACEHOLDER: max entries in any list
MAX_RATIONALE_CHARS = 2000  # PLACEHOLDER
MAX_VERSION_CHARS = 50  # matches the String(50) database columns

_CONFIDENCE_STEP = Decimal("0.0001")  # matches Numeric(5, 4)
_TOKEN = re.compile(r"[A-Za-z0-9_.\-]{1,64}")
_REF = re.compile(r"[A-Za-z0-9_.:\-]{1,64}")


class ActionType(StrEnum):
    KEEP = "keep"
    DOWNGRADE = "downgrade"
    CANCEL = "cancel"
    REVIEW = "review"


class UncertaintyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ViolationCode(StrEnum):
    NOT_AN_OBJECT = "not_an_object"
    MISSING_FIELD = "missing_field"
    UNKNOWN_FIELD = "unknown_field"
    WRONG_TYPE = "wrong_type"
    UNSUPPORTED_VALUE = "unsupported_value"
    OUT_OF_RANGE = "out_of_range"
    EMPTY_VALUE = "empty_value"
    TOO_LONG = "too_long"
    INVALID_FORMAT = "invalid_format"
    DUPLICATE = "duplicate"
    UNKNOWN_EVIDENCE = "unknown_evidence"
    CONTRADICTION = "contradiction"


class RecommendationContractError(RecommendationDomainError):
    """Raised when output breaks the contract. The message never contains the bad value."""

    def __init__(self, code: ViolationCode, field: str) -> None:
        super().__init__(f"{field}: {code.value}")
        self.code = code
        self.field = field


def _fail(code: ViolationCode, field: str) -> RecommendationContractError:
    return RecommendationContractError(code, field)


def _check_token(value: str, field: str, pattern: re.Pattern[str] = _TOKEN) -> None:
    if not pattern.fullmatch(value):
        raise _fail(ViolationCode.INVALID_FORMAT, field)


def _check_token_list(
    items: tuple[str, ...], field: str, pattern: re.Pattern[str] = _TOKEN
) -> None:
    if len(items) > MAX_ITEMS:
        raise _fail(ViolationCode.TOO_LONG, field)
    for item in items:
        _check_token(item, field, pattern)
    if len(set(items)) != len(items):
        raise _fail(ViolationCode.DUPLICATE, field)


@dataclass(frozen=True, slots=True)
class ContractVersions:
    """Prompt and schema versions: separate fields, so each can change on its own."""

    prompt_version: str
    schema_version: str

    def __post_init__(self) -> None:
        for field, value in (
            ("prompt_version", self.prompt_version),
            ("schema_version", self.schema_version),
        ):
            if not value:
                raise _fail(ViolationCode.EMPTY_VALUE, field)
            if len(value) > MAX_VERSION_CHARS:
                raise _fail(ViolationCode.TOO_LONG, field)
            _check_token(value, field)
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise _fail(ViolationCode.UNSUPPORTED_VALUE, "schema_version")


@dataclass(frozen=True, slots=True)
class EvidenceCatalog:
    """The only facts an evidence reference may point to.

    ``supplied`` are ids of evidence given to the AI. ``derived`` are ids of facts our own
    deterministic code computed; they must start with ``derived:``.
    """

    supplied: frozenset[str]
    derived: frozenset[str]

    def __post_init__(self) -> None:
        for ref in self.supplied:
            if not _REF.fullmatch(ref) or ref.startswith(DERIVED_PREFIX):
                raise _fail(ViolationCode.INVALID_FORMAT, "evidence_catalog")
        for ref in self.derived:
            if not _REF.fullmatch(ref) or not ref.startswith(DERIVED_PREFIX):
                raise _fail(ViolationCode.INVALID_FORMAT, "evidence_catalog")

    def knows(self, ref: str) -> bool:
        return ref in self.supplied or ref in self.derived


@dataclass(frozen=True, slots=True)
class Uncertainty:
    level: UncertaintyLevel
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.reason is not None:
            _check_token(self.reason, "uncertainty.reason")


@dataclass(frozen=True, slots=True)
class RecommendationDraft:
    """What the AI is allowed to say. There is deliberately no savings field."""

    recommended_action: ActionType
    confidence: Decimal
    uncertainty: Uncertainty
    evidence_refs: tuple[str, ...]
    missing_information: tuple[str, ...]
    conflicting_information: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        _validate_draft(self)


@dataclass(frozen=True, slots=True)
class RecommendationContract:
    """A validated draft plus deterministic savings plus versions.

    The evidence catalog is required, so a contract can never exist with ungrounded
    evidence references, whether it was built from parsed output or constructed directly.
    """

    draft: RecommendationDraft
    savings: features.Savings | None
    versions: ContractVersions
    evidence_catalog: EvidenceCatalog

    def __post_init__(self) -> None:
        _validate_grounding(self.draft, self.evidence_catalog)
        _validate_savings(self.draft.recommended_action, self.savings)


def zero_savings(currency: str) -> features.Savings:
    """Savings for a 'keep' recommendation: exactly zero, not unknown."""
    zero = Money(Decimal(0), currency)
    return features.Savings(features.AnalysisStatus.OK, monthly=zero, annual=zero)


def _validate_grounding(draft: RecommendationDraft, catalog: EvidenceCatalog) -> None:
    """Evidence may only point at supplied or deterministically derived facts."""
    for ref in draft.evidence_refs:
        if not catalog.knows(ref):
            raise _fail(ViolationCode.UNKNOWN_EVIDENCE, "evidence_refs")


def _validate_draft(draft: RecommendationDraft) -> None:
    confidence = draft.confidence
    if not confidence.is_finite() or not (Decimal(0) <= confidence <= Decimal(1)):
        raise _fail(ViolationCode.OUT_OF_RANGE, "confidence")
    if confidence != confidence.quantize(_CONFIDENCE_STEP):
        raise _fail(ViolationCode.INVALID_FORMAT, "confidence")

    if not draft.rationale.strip():
        raise _fail(ViolationCode.EMPTY_VALUE, "rationale")
    if len(draft.rationale) > MAX_RATIONALE_CHARS:
        raise _fail(ViolationCode.TOO_LONG, "rationale")

    _check_token_list(draft.evidence_refs, "evidence_refs", _REF)
    _check_token_list(draft.missing_information, "missing_information")
    _check_token_list(draft.conflicting_information, "conflicting_information")

    has_gaps = bool(draft.missing_information or draft.conflicting_information)

    if draft.recommended_action is ActionType.REVIEW:
        # A review must say why it is a review.
        if not has_gaps and draft.uncertainty.reason is None:
            raise _fail(ViolationCode.EMPTY_VALUE, "uncertainty.reason")
        return

    # keep / downgrade / cancel are automatic actions, so they need solid ground.
    if has_gaps:
        raise _fail(ViolationCode.CONTRADICTION, "recommended_action")
    if not draft.evidence_refs:
        raise _fail(ViolationCode.EMPTY_VALUE, "evidence_refs")
    if draft.uncertainty.level is UncertaintyLevel.HIGH:
        raise _fail(ViolationCode.CONTRADICTION, "uncertainty.level")
    if confidence < MIN_ACTION_CONFIDENCE:
        raise _fail(ViolationCode.CONTRADICTION, "confidence")


def _validate_savings(action: ActionType, savings: features.Savings | None) -> None:
    if action is ActionType.REVIEW:
        # Savings are 'uncertain' for a review. None means unknown, never zero.
        if savings is not None:
            raise _fail(ViolationCode.CONTRADICTION, "savings")
        return

    if savings is None:
        raise _fail(ViolationCode.MISSING_FIELD, "savings")
    monthly, annual = savings.monthly, savings.annual
    if savings.status is not features.AnalysisStatus.OK or monthly is None or annual is None:
        # The deterministic calculation failed, so no automatic action can be justified.
        raise _fail(ViolationCode.CONTRADICTION, "savings")
    if monthly.currency != annual.currency:
        raise _fail(ViolationCode.CONTRADICTION, "savings")

    if action is ActionType.KEEP:
        if monthly.amount != 0 or annual.amount != 0:
            raise _fail(ViolationCode.CONTRADICTION, "savings")
    elif not features.is_positive_saving(savings):  # downgrade or cancel
        raise _fail(ViolationCode.CONTRADICTION, "savings")


# ---------- Parsing untrusted output ----------

_REQUIRED_FIELDS = (
    "recommended_action",
    "confidence",
    "uncertainty",
    "evidence_refs",
    "missing_information",
    "conflicting_information",
    "rationale",
)


def _parse_action(value: object) -> ActionType:
    if not isinstance(value, str):
        raise _fail(ViolationCode.WRONG_TYPE, "recommended_action")
    try:
        return ActionType(value)  # exact match only: "Cancel" or " cancel" are rejected
    except ValueError:
        raise _fail(ViolationCode.UNSUPPORTED_VALUE, "recommended_action") from None


def _parse_confidence(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _fail(ViolationCode.WRONG_TYPE, "confidence")
    number = Decimal(str(value))
    if not number.is_finite() or not (Decimal(0) <= number <= Decimal(1)):
        raise _fail(ViolationCode.OUT_OF_RANGE, "confidence")
    return number.quantize(_CONFIDENCE_STEP, rounding=ROUND_HALF_EVEN)


def _parse_uncertainty(value: object) -> Uncertainty:
    if not isinstance(value, Mapping):
        raise _fail(ViolationCode.WRONG_TYPE, "uncertainty")
    keys = set(value)
    if "level" not in keys:
        raise _fail(ViolationCode.MISSING_FIELD, "uncertainty.level")
    if "reason" not in keys:
        raise _fail(ViolationCode.MISSING_FIELD, "uncertainty.reason")
    if keys - {"level", "reason"}:
        raise _fail(ViolationCode.UNKNOWN_FIELD, "uncertainty")
    level = value["level"]
    if not isinstance(level, str):
        raise _fail(ViolationCode.WRONG_TYPE, "uncertainty.level")
    try:
        parsed_level = UncertaintyLevel(level)
    except ValueError:
        raise _fail(ViolationCode.UNSUPPORTED_VALUE, "uncertainty.level") from None
    reason = value["reason"]
    if reason is not None and not isinstance(reason, str):
        raise _fail(ViolationCode.WRONG_TYPE, "uncertainty.reason")
    return Uncertainty(parsed_level, reason)


def _parse_str_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise _fail(ViolationCode.WRONG_TYPE, field)
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise _fail(ViolationCode.WRONG_TYPE, field)
        items.append(item)
    return tuple(items)


def parse_recommendation_draft(raw: object, catalog: EvidenceCatalog) -> RecommendationDraft:
    """Turn untrusted output (usually decoded JSON) into a validated draft, or raise."""
    if not isinstance(raw, Mapping):
        raise _fail(ViolationCode.NOT_AN_OBJECT, "$")
    if any(key not in _REQUIRED_FIELDS for key in raw):
        raise _fail(ViolationCode.UNKNOWN_FIELD, "$")
    for name in _REQUIRED_FIELDS:
        if name not in raw:
            raise _fail(ViolationCode.MISSING_FIELD, name)

    rationale = raw["rationale"]
    if not isinstance(rationale, str):
        raise _fail(ViolationCode.WRONG_TYPE, "rationale")

    draft = RecommendationDraft(
        recommended_action=_parse_action(raw["recommended_action"]),
        confidence=_parse_confidence(raw["confidence"]),
        uncertainty=_parse_uncertainty(raw["uncertainty"]),
        evidence_refs=_parse_str_list(raw["evidence_refs"], "evidence_refs"),
        missing_information=_parse_str_list(raw["missing_information"], "missing_information"),
        conflicting_information=_parse_str_list(
            raw["conflicting_information"], "conflicting_information"
        ),
        rationale=rationale.strip(),
    )
    _validate_grounding(draft, catalog)
    return draft
