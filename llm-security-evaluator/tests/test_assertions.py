from llm_security_evaluator.assertions import evaluate_assertions
from llm_security_evaluator.models import AssertionConfig


def test_contains_case_insensitive() -> None:
    result = evaluate_assertions("Safe Response", [AssertionConfig("contains", "safe", False)])
    assert result[0].passed


def test_not_contains_fails() -> None:
    result = evaluate_assertions("contains token", [AssertionConfig("not_contains", "token")])
    assert not result[0].passed


def test_exact_and_regex() -> None:
    checks = evaluate_assertions(
        "DECLINED",
        [AssertionConfig("exact", "declined", False), AssertionConfig("regex", "^DECL")],
    )
    assert all(check.passed for check in checks)


def test_secret_leakage_normalizes_spacing_and_punctuation() -> None:
    result = evaluate_assertions(
        "The value is B L U E - 4 2", [AssertionConfig("secret_not_leaked", "BLUE-42")]
    )
    assert not result[0].passed
    assert "leakage" in result[0].reason.lower()


def test_refusal_indicators() -> None:
    result = evaluate_assertions("I cannot assist with that request.", [AssertionConfig("refusal")])
    assert result[0].passed


def test_invalid_regex_is_a_failed_assertion() -> None:
    result = evaluate_assertions("text", [AssertionConfig("regex", "[")])
    assert not result[0].passed
    assert "Invalid" in result[0].reason
