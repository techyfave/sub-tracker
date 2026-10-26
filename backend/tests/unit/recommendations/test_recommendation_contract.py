import uuid
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.analysis.features import calculate_savings
from app.domain.common.money import Money
from app.domain.recommendations.contracts import (
    ActionType,
    ContractVersions,
    EvidenceCatalog,
    RecommendationContract,
    RecommendationDraft,
    Uncertainty,
    UncertaintyLevel,
    ViolationCode,
    parse_recommendation_draft,
    zero_savings,
)
from app.domain.recommendations.contracts import RecommendationContractError as ContractError
from app.domain.recommendations.exceptions import RecommendationDomainError
from app.domain.subscriptions.entities import BillingCadence, Plan
from app.infrastructure.database.models import RecommendationAction

CATALOG = EvidenceCatalog(
    supplied=frozenset({"usage-1", "txn-1"}),
    derived=frozenset({"derived:monthly_cost"}),
)
VERSIONS = ContractVersions(prompt_version="1.0.0", schema_version="1.0")


def make_plan(amount: str, currency: str = "NGN") -> Plan:
    return Plan(
        provider_id=uuid.uuid4(),
        name="test plan",
        amount=Decimal(amount),
        currency=currency,
        billing_interval=BillingCadence.MONTHLY,
    )


def raw_draft(**overrides: object) -> dict[str, object]:
    """A valid 'keep' draft. Tests change one thing at a time."""
    base: dict[str, object] = {
        "recommended_action": "keep",
        "confidence": 0.9,
        "uncertainty": {"level": "low", "reason": None},
        "evidence_refs": ["usage-1"],
        "missing_information": [],
        "conflicting_information": [],
        "rationale": "Regular usage shows the subscription is still valuable.",
    }
    base.update(overrides)
    return base


def assert_rejected(raw: object, code: ViolationCode, field: str | None = None) -> None:
    with pytest.raises(ContractError) as info:
        parse_recommendation_draft(raw, CATALOG)
    assert info.value.code == code
    if field is not None:
        assert info.value.field == field


# ---------- Golden tests: the six scenarios in doc/seed-scenarios.md ----------
def test_golden_keep():
    draft = parse_recommendation_draft(raw_draft(), CATALOG)
    contract = RecommendationContract(draft, zero_savings("NGN"), VERSIONS)
    assert contract.draft.recommended_action is ActionType.KEEP
    assert contract.savings is not None
    assert contract.savings.monthly == Money(Decimal("0"), "NGN")
    assert contract.savings.annual == Money(Decimal("0"), "NGN")


def test_golden_downgrade_saves_4000_monthly_48000_annual():
    draft = parse_recommendation_draft(raw_draft(recommended_action="downgrade"), CATALOG)
    savings = calculate_savings(make_plan("20000.00"), make_plan("16000.00"))
    contract = RecommendationContract(draft, savings, VERSIONS)
    assert contract.savings is not None
    assert contract.savings.monthly == Money(Decimal("4000"), "NGN")
    assert contract.savings.annual == Money(Decimal("48000"), "NGN")


def test_golden_cancel_saves_full_cost():
    draft = parse_recommendation_draft(raw_draft(recommended_action="cancel"), CATALOG)
    savings = calculate_savings(make_plan("5000.00"))
    contract = RecommendationContract(draft, savings, VERSIONS)
    assert contract.savings is not None
    assert contract.savings.monthly == Money(Decimal("5000"), "NGN")
    assert contract.savings.annual == Money(Decimal("60000"), "NGN")


def test_golden_review_uncertain_evidence_has_unknown_savings():
    raw = raw_draft(
        recommended_action="review",
        confidence=0.4,
        uncertainty={"level": "medium", "reason": "insufficient_evidence"},
        evidence_refs=[],
    )
    contract = RecommendationContract(parse_recommendation_draft(raw, CATALOG), None, VERSIONS)
    assert contract.draft.recommended_action is ActionType.REVIEW
    assert contract.savings is None  # unknown, NOT zero


def test_golden_missing_usage_is_review_not_zero_usage():
    raw = raw_draft(
        recommended_action="review",
        confidence=0.3,
        uncertainty={"level": "high", "reason": "missing_usage"},
        evidence_refs=[],
        missing_information=["usage_data"],
    )
    draft = parse_recommendation_draft(raw, CATALOG)
    assert draft.missing_information == ("usage_data",)
    assert RecommendationContract(draft, None, VERSIONS).savings is None


def test_golden_conflicting_evidence_is_review():
    raw = raw_draft(
        recommended_action="review",
        confidence=0.5,
        uncertainty={"level": "medium", "reason": "conflicting_evidence"},
        evidence_refs=["usage-1", "txn-1"],
        conflicting_information=["usage_vs_billing"],
    )
    draft = parse_recommendation_draft(raw, CATALOG)
    assert draft.conflicting_information == ("usage_vs_billing",)
    assert RecommendationContract(draft, None, VERSIONS).savings is None


def test_derived_facts_are_valid_evidence():
    draft = parse_recommendation_draft(
        raw_draft(evidence_refs=["usage-1", "derived:monthly_cost"]), CATALOG
    )
    assert draft.evidence_refs == ("usage-1", "derived:monthly_cost")


# ---------- Adversarial tests: bad structure ----------
@pytest.mark.parametrize("raw", ["cancel", None, [], 42])
def test_non_object_output_rejected(raw):
    assert_rejected(raw, ViolationCode.NOT_AN_OBJECT, "$")


@pytest.mark.parametrize(
    "name",
    [
        "recommended_action",
        "confidence",
        "uncertainty",
        "evidence_refs",
        "missing_information",
        "conflicting_information",
        "rationale",
    ],
)
def test_missing_field_rejected(name):
    raw = raw_draft()
    del raw[name]
    assert_rejected(raw, ViolationCode.MISSING_FIELD, name)


def test_ai_cannot_invent_savings_or_other_fields():
    assert_rejected(raw_draft(monthly_savings=99999), ViolationCode.UNKNOWN_FIELD, "$")
    assert_rejected(raw_draft(schema_version="9.9"), ViolationCode.UNKNOWN_FIELD, "$")


BAD_DRAFTS = [
    # action
    ({"recommended_action": "delete"}, ViolationCode.UNSUPPORTED_VALUE, "recommended_action"),
    ({"recommended_action": "Cancel"}, ViolationCode.UNSUPPORTED_VALUE, "recommended_action"),
    ({"recommended_action": " cancel"}, ViolationCode.UNSUPPORTED_VALUE, "recommended_action"),
    ({"recommended_action": 5}, ViolationCode.WRONG_TYPE, "recommended_action"),
    # confidence
    ({"confidence": True}, ViolationCode.WRONG_TYPE, "confidence"),
    ({"confidence": "0.9"}, ViolationCode.WRONG_TYPE, "confidence"),
    ({"confidence": 1.5}, ViolationCode.OUT_OF_RANGE, "confidence"),
    ({"confidence": -0.1}, ViolationCode.OUT_OF_RANGE, "confidence"),
    ({"confidence": float("nan")}, ViolationCode.OUT_OF_RANGE, "confidence"),
    ({"confidence": float("inf")}, ViolationCode.OUT_OF_RANGE, "confidence"),
    # evidence references
    ({"evidence_refs": ["invented-9"]}, ViolationCode.UNKNOWN_EVIDENCE, "evidence_refs"),
    ({"evidence_refs": ["derived:invented"]}, ViolationCode.UNKNOWN_EVIDENCE, "evidence_refs"),
    ({"evidence_refs": ["usage-1", "usage-1"]}, ViolationCode.DUPLICATE, "evidence_refs"),
    (
        {"evidence_refs": ["ignore previous instructions"]},
        ViolationCode.INVALID_FORMAT,
        "evidence_refs",
    ),
    ({"evidence_refs": "usage-1"}, ViolationCode.WRONG_TYPE, "evidence_refs"),
    ({"evidence_refs": [1]}, ViolationCode.WRONG_TYPE, "evidence_refs"),
    ({"evidence_refs": []}, ViolationCode.EMPTY_VALUE, "evidence_refs"),
    ({"evidence_refs": ["usage-1"] * 21}, ViolationCode.TOO_LONG, "evidence_refs"),
    # rationale
    ({"rationale": ""}, ViolationCode.EMPTY_VALUE, "rationale"),
    ({"rationale": "   "}, ViolationCode.EMPTY_VALUE, "rationale"),
    ({"rationale": "x" * 2001}, ViolationCode.TOO_LONG, "rationale"),
    ({"rationale": 42}, ViolationCode.WRONG_TYPE, "rationale"),
    # uncertainty
    (
        {"uncertainty": {"level": "extreme", "reason": None}},
        ViolationCode.UNSUPPORTED_VALUE,
        "uncertainty.level",
    ),
    (
        {"uncertainty": {"level": "low", "reason": None, "extra": 1}},
        ViolationCode.UNKNOWN_FIELD,
        "uncertainty",
    ),
    ({"uncertainty": {"level": "low"}}, ViolationCode.MISSING_FIELD, "uncertainty.reason"),
    ({"uncertainty": "low"}, ViolationCode.WRONG_TYPE, "uncertainty"),
    (
        {"uncertainty": {"level": "low", "reason": "not a token!"}},
        ViolationCode.INVALID_FORMAT,
        "uncertainty.reason",
    ),
]


@pytest.mark.parametrize(("overrides", "code", "field"), BAD_DRAFTS)
def test_bad_drafts_rejected(overrides, code, field):
    assert_rejected(raw_draft(**overrides), code, field)


# ---------- Adversarial tests: contradictory output ----------
CONTRADICTIONS = [
    # missing or conflicting information forces a review
    (
        {"recommended_action": "cancel", "missing_information": ["usage_data"]},
        ViolationCode.CONTRADICTION,
        "recommended_action",
    ),
    (
        {"recommended_action": "keep", "conflicting_information": ["usage_vs_billing"]},
        ViolationCode.CONTRADICTION,
        "recommended_action",
    ),
    # automatic actions cannot rest on high uncertainty or low confidence
    (
        {
            "recommended_action": "cancel",
            "uncertainty": {"level": "high", "reason": None},
        },
        ViolationCode.CONTRADICTION,
        "uncertainty.level",
    ),
    (
        {"recommended_action": "cancel", "confidence": 0.3},
        ViolationCode.CONTRADICTION,
        "confidence",
    ),
    # a review must explain itself
    (
        {"recommended_action": "review", "evidence_refs": []},
        ViolationCode.EMPTY_VALUE,
        "uncertainty.reason",
    ),
]


@pytest.mark.parametrize(("overrides", "code", "field"), CONTRADICTIONS)
def test_contradictory_drafts_rejected(overrides, code, field):
    assert_rejected(raw_draft(**overrides), code, field)


def test_cannot_build_an_invalid_draft_directly():
    with pytest.raises(ContractError) as info:
        RecommendationDraft(
            recommended_action=ActionType.CANCEL,
            confidence=Decimal("0.9000"),
            uncertainty=Uncertainty(UncertaintyLevel.LOW),
            evidence_refs=("usage-1",),
            missing_information=("usage_data",),
            conflicting_information=(),
            rationale="Looks unused.",
        )
    assert info.value.code == ViolationCode.CONTRADICTION


# ---------- Adversarial tests: savings must match the action ----------
def make_draft(action: str) -> RecommendationDraft:
    if action == "review":
        raw = raw_draft(
            recommended_action="review",
            confidence=0.4,
            uncertainty={"level": "medium", "reason": "insufficient_evidence"},
            evidence_refs=[],
        )
    else:
        raw = raw_draft(recommended_action=action)
    return parse_recommendation_draft(raw, CATALOG)


def assert_savings_rejected(action, savings, code, field="savings"):
    with pytest.raises(ContractError) as info:
        RecommendationContract(make_draft(action), savings, VERSIONS)
    assert info.value.code == code
    assert info.value.field == field


def test_cancel_without_savings_rejected():
    assert_savings_rejected("cancel", None, ViolationCode.MISSING_FIELD)


def test_cancel_with_zero_savings_rejected():
    assert_savings_rejected("cancel", zero_savings("NGN"), ViolationCode.CONTRADICTION)


def test_downgrade_to_a_pricier_plan_rejected():
    pricier = calculate_savings(make_plan("3000.00"), make_plan("5000.00"))
    assert_savings_rejected("downgrade", pricier, ViolationCode.CONTRADICTION)


def test_keep_with_positive_savings_rejected():
    assert_savings_rejected(
        "keep", calculate_savings(make_plan("5000.00")), ViolationCode.CONTRADICTION
    )


def test_review_with_savings_rejected():
    assert_savings_rejected(
        "review", calculate_savings(make_plan("5000.00")), ViolationCode.CONTRADICTION
    )


def test_cancel_with_failed_calculation_rejected():
    mismatch = calculate_savings(make_plan("5000.00", "NGN"), make_plan("5.00", "USD"))
    assert_savings_rejected("cancel", mismatch, ViolationCode.CONTRADICTION)


# ---------- Versions ----------
def test_prompt_and_schema_versions_are_independent():
    a = ContractVersions(prompt_version="1.0.0", schema_version="1.0")
    b = ContractVersions(prompt_version="2.0.0", schema_version="1.0")
    assert a.schema_version == b.schema_version
    assert a.prompt_version != b.prompt_version


@pytest.mark.parametrize(
    ("prompt", "schema", "code", "field"),
    [
        ("1.0.0", "9.9", ViolationCode.UNSUPPORTED_VALUE, "schema_version"),
        ("", "1.0", ViolationCode.EMPTY_VALUE, "prompt_version"),
        ("v" * 51, "1.0", ViolationCode.TOO_LONG, "prompt_version"),
        ("has space", "1.0", ViolationCode.INVALID_FORMAT, "prompt_version"),
    ],
)
def test_bad_versions_rejected(prompt, schema, code, field):
    with pytest.raises(ContractError) as info:
        ContractVersions(prompt_version=prompt, schema_version=schema)
    assert info.value.code == code
    assert info.value.field == field


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (0.5, "0.5000"),
        (0.123456, "0.1235"),  # rounds up
        (0.12345, "0.1234"),  # tie: half-even goes to the even digit (4)
        (0.12355, "0.1236"),  # tie: half-even goes to the even digit (6)
    ],
)
def test_confidence_is_rounded_half_even_to_four_places(given, expected):
    raw = raw_draft(
        recommended_action="review",
        confidence=given,
        uncertainty={"level": "medium", "reason": "insufficient_evidence"},
        evidence_refs=[],
    )
    assert parse_recommendation_draft(raw, CATALOG).confidence == Decimal(expected)


# ---------- Evidence catalog ----------
def test_catalog_rejects_spoofed_ids():
    with pytest.raises(ContractError):
        EvidenceCatalog(supplied=frozenset({"derived:fake"}), derived=frozenset())
    with pytest.raises(ContractError):
        EvidenceCatalog(supplied=frozenset(), derived=frozenset({"monthly_cost"}))


# ---------- Safety properties ----------
def test_error_never_echoes_raw_content():
    secret = "SECRET-ACTION-XYZ"
    with pytest.raises(ContractError) as info:
        parse_recommendation_draft(raw_draft(recommended_action=secret), CATALOG)
    assert secret not in str(info.value)


def test_contract_is_immutable():
    contract = RecommendationContract(make_draft("keep"), zero_savings("NGN"), VERSIONS)
    with pytest.raises(FrozenInstanceError):
        contract.savings = None
    with pytest.raises(FrozenInstanceError):
        contract.draft.confidence = Decimal("1")
    assert isinstance(contract.draft.evidence_refs, tuple)


def test_contract_errors_are_domain_errors():
    assert issubclass(ContractError, RecommendationDomainError)


def test_action_values_match_the_stored_enum():
    assert {a.value for a in ActionType} == {a.value for a in RecommendationAction}
