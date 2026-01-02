from datetime import datetime, date

import pytest

from app.main import routes
from app.main.routes import get_date_range


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2024, 5, 15)


@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(routes, 'date', FixedDate)
    return FixedDate.today()


def test_valid_range_returns_first_and_last_day():
    start, end, year, month = get_date_range('2023', '12')
    assert (year, month) == (2023, 12)
    assert start == datetime(2023, 12, 1)
    assert end == datetime(2023, 12, 31, 23, 59, 59)


def test_leap_year_february_has_29_days():
    _, end, year, month = get_date_range('2024', '2')
    assert (year, month) == (2024, 2)
    assert end.day == 29
    assert end == datetime(2024, 2, 29, 23, 59, 59)


def test_leading_zero_month_is_parsed():
    start, end, year, month = get_date_range('2023', '07')
    assert (year, month) == (2023, 7)
    assert start == datetime(2023, 7, 1)
    assert end.day == 31


def test_invalid_year_defaults_to_today(fixed_today):
    start, end, year, month = get_date_range('abc', '3')
    assert (year, month) == (fixed_today.year, fixed_today.month)
    assert start == datetime(fixed_today.year, fixed_today.month, 1)
    assert end.day >= 28


def test_invalid_month_defaults_to_today(fixed_today):
    start, end, year, month = get_date_range('2023', 'oops')
    assert (year, month) == (fixed_today.year, fixed_today.month)
    assert start.month == fixed_today.month
    assert end.month == fixed_today.month


def test_none_inputs_default_to_today(fixed_today):
    start, end, year, month = get_date_range(None, None)
    assert (year, month) == (fixed_today.year, fixed_today.month)
    assert start.year == fixed_today.year
    assert end.year == fixed_today.year


def test_type_error_in_conversion_uses_today(monkeypatch):
    class Weird:
        def __int__(self):
            raise TypeError('no int')
    monkeypatch.setattr(routes, 'date', FixedDate)
    start, end, year, month = get_date_range(Weird(), '5')
    assert (year, month) == (FixedDate.today().year, FixedDate.today().month)
    assert start.year == FixedDate.today().year


def test_end_date_includes_end_of_day_time():
    _, end, _, _ = get_date_range('2023', '11')
    assert end.hour == 23 and end.minute == 59 and end.second == 59


def test_april_has_30_days():
    start, end, _, _ = get_date_range('2024', '4')
    assert start.day == 1
    assert end.day == 30


def test_returns_datetime_objects():
    start, end, _, _ = get_date_range('2022', '9')
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
