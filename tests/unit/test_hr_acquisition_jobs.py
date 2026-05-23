import pytest

from src.utils.telegram import normalize_telegram_username


@pytest.mark.parametrize(
    "raw_telegram, expected",
    (
        (" @ExampleUser ", "exampleuser"),
        (123456789, "123456789"),
        (None, ""),
    ),
)
def test_normalize_telegram_username_handles_sheet_values(raw_telegram, expected):
    assert normalize_telegram_username(raw_telegram) == expected
