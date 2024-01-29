import pytest

from metrics_python.prometheus._server import _parse_bool


@pytest.mark.parametrize(
    "value,expected_result",
    [
        ("y", True),
        ("n", False),
        ("Y", True),
        ("N", False),
        ("yes", True),
        ("no", False),
        ("true", True),
        ("false", False),
    ],
)
def test_parse_bool(value: str, expected_result: bool) -> None:
    assert _parse_bool(value) == expected_result


def test_parse_bool_raise_exception() -> None:
    with pytest.raises(ValueError):
        _parse_bool("random-string")
