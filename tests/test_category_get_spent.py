from datetime import datetime

from app import db
from app.models import Transaction


def add_transaction(user, category, amount, year, month, day, type_='expense'):
    tx = Transaction(
        amount=amount,
        type=type_,
        date=datetime(year, month, day),
        author=user,
        category=category,
    )
    db.session.add(tx)
    db.session.commit()
    return tx


def test_no_transactions_returns_zero(make_category):
    category = make_category()
    assert category.get_spent_in_month(2024, 5) == 0.0


def test_single_expense_is_counted(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 25.5, 2024, 5, 10)
    assert category.get_spent_in_month(2024, 5) == 25.5


def test_multiple_expenses_sum(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 10, 2024, 5, 1)
    add_transaction(user, category, 15, 2024, 5, 2)
    add_transaction(user, category, 5, 2024, 5, 3)
    assert category.get_spent_in_month(2024, 5) == 30


def test_income_transactions_not_counted(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 100, 2024, 5, 4, type_='income')
    assert category.get_spent_in_month(2024, 5) == 0


def test_other_category_expenses_not_counted(make_category):
    category = make_category('Food')
    other_category = make_category('Books')
    user = category.owner
    add_transaction(user, other_category, 40, 2024, 5, 5)
    assert category.get_spent_in_month(2024, 5) == 0


def test_other_month_not_counted(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 12, 2024, 4, 30)
    assert category.get_spent_in_month(2024, 5) == 0


def test_other_year_not_counted(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 12, 2023, 5, 15)
    assert category.get_spent_in_month(2024, 5) == 0


def test_includes_first_day(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 9.99, 2024, 5, 1)
    assert category.get_spent_in_month(2024, 5) == 9.99


def test_includes_last_day(make_category):
    category = make_category()
    user = category.owner
    add_transaction(user, category, 20, 2024, 5, 31)
    assert category.get_spent_in_month(2024, 5) == 20


def test_mixed_types_and_categories(make_category):
    food = make_category('Food')
    travel = make_category('Travel')
    user = food.owner
    add_transaction(user, food, 10, 2024, 5, 1)
    add_transaction(user, food, 5, 2024, 5, 2, type_='income')
    add_transaction(user, travel, 100, 2024, 5, 3)
    add_transaction(user, food, 7.25, 2024, 5, 4)
    assert food.get_spent_in_month(2024, 5) == 17.25
