from datetime import datetime

from app import db
from app.models import Category, Transaction, Budget


class TestUser:
    def test_user_creation(self, user):
        assert user.username == 'tester'
        assert user.email == 'tester@example.com'
        assert user.id is not None

    def test_user_set_password(self, user):
        # Password should be hashed
        assert user.password_hash != 'secret123'
        assert user.password_hash is not None

    def test_user_check_password_correct(self, user):
        assert user.check_password('secret123')

    def test_user_check_password_incorrect(self, user):
        assert not user.check_password('wrongpassword')

    def test_user_check_password_empty(self, user):
        assert not user.check_password('')

    def test_user_repr(self, user):
        assert repr(user) == '<User tester>'

    def test_user_is_authenticated(self, user):
        assert user.is_authenticated

    def test_user_is_active(self, user):
        assert user.is_active

    def test_user_is_anonymous(self, user):
        assert not user.is_anonymous

    def test_user_get_id(self, user):
        assert user.get_id() == str(user.id)

    def test_user_transactions_relationship(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=10, type='expense', date=datetime.now(), author=user, category=cat)
        db.session.add(tx)
        db.session.commit()
        assert user.transactions.count() == 1

    def test_user_categories_relationship(self, user, make_category):
        cat = make_category('Food', 'expense')
        assert user.categories.count() == 1

    def test_user_budgets_relationship(self, user, make_category):
        cat = make_category('Food', 'expense')
        budget = Budget(amount=100, year=2024, month=5, owner=user, category=cat)
        db.session.add(budget)
        db.session.commit()
        assert user.budgets.count() == 1


class TestCategory:
    def test_category_creation(self, make_category):
        cat = make_category('Groceries', 'expense')
        assert cat.name == 'Groceries'
        assert cat.type == 'expense'

    def test_category_repr(self, make_category):
        cat = make_category('Books', 'expense')
        assert repr(cat) == '<Category Books>'

    def test_category_default_type(self, user):
        cat = Category(name='Default', owner=user)
        db.session.add(cat)
        db.session.commit()
        assert cat.type == 'expense'

    def test_category_income_type(self, make_category):
        cat = make_category('Salary', 'income')
        assert cat.type == 'income'

    def test_category_get_spent_no_transactions(self, make_category):
        cat = make_category('Food', 'expense')
        spent = cat.get_spent_in_month(2024, 5)
        assert spent == 0.0

    def test_category_get_spent_single_transaction(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(
            amount=15.5,
            type='expense',
            date=datetime(2024, 5, 10),
            author=user,
            category=cat
        )
        db.session.add(tx)
        db.session.commit()
        spent = cat.get_spent_in_month(2024, 5)
        assert spent == 15.5

    def test_category_get_spent_multiple_transactions(self, user, make_category):
        cat = make_category('Food', 'expense')
        for i in range(3):
            tx = Transaction(
                amount=10.0,
                type='expense',
                date=datetime(2024, 5, i + 1),
                author=user,
                category=cat
            )
            db.session.add(tx)
        db.session.commit()
        spent = cat.get_spent_in_month(2024, 5)
        assert spent == 30.0

    def test_category_get_spent_ignores_income(self, user, make_category):
        cat = make_category('Food', 'income')
        tx = Transaction(
            amount=100,
            type='income',
            date=datetime(2024, 5, 1),
            author=user,
            category=cat
        )
        db.session.add(tx)
        db.session.commit()
        spent = cat.get_spent_in_month(2024, 5)
        assert spent == 0.0

    def test_category_get_spent_different_months(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx1 = Transaction(
            amount=10,
            type='expense',
            date=datetime(2024, 4, 15),
            author=user,
            category=cat
        )
        tx2 = Transaction(
            amount=20,
            type='expense',
            date=datetime(2024, 5, 15),
            author=user,
            category=cat
        )
        db.session.add_all([tx1, tx2])
        db.session.commit()
        assert cat.get_spent_in_month(2024, 4) == 10.0
        assert cat.get_spent_in_month(2024, 5) == 20.0

    def test_category_get_spent_different_years(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx1 = Transaction(
            amount=15,
            type='expense',
            date=datetime(2023, 5, 15),
            author=user,
            category=cat
        )
        tx2 = Transaction(
            amount=25,
            type='expense',
            date=datetime(2024, 5, 15),
            author=user,
            category=cat
        )
        db.session.add_all([tx1, tx2])
        db.session.commit()
        assert cat.get_spent_in_month(2023, 5) == 15.0
        assert cat.get_spent_in_month(2024, 5) == 25.0


class TestTransaction:
    def test_transaction_creation(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(
            amount=25.50,
            type='expense',
            date=datetime(2024, 5, 10),
            memo='lunch',
            author=user,
            category=cat
        )
        db.session.add(tx)
        db.session.commit()
        assert tx.amount == 25.50
        assert tx.type == 'expense'
        assert tx.memo == 'lunch'

    def test_transaction_repr(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=50, type='expense', date=datetime.now(), author=user, category=cat)
        db.session.add(tx)
        db.session.commit()
        assert repr(tx) == f'<Transaction {tx.id} - 50.0>'

    def test_transaction_default_type(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=10, type='expense', author=user, category=cat)
        db.session.add(tx)
        db.session.commit()
        assert tx.type == 'expense'

    def test_transaction_income_type(self, user, make_category):
        cat = make_category('Salary', 'income')
        tx = Transaction(amount=5000, type='income', date=datetime.now(), author=user, category=cat)
        assert tx.type == 'income'

    def test_transaction_no_memo(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=10, type='expense', date=datetime.now(), author=user, category=cat)
        assert tx.memo is None

    def test_transaction_date_defaults_to_now(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=10, type='expense', author=user, category=cat, date=datetime.now())
        db.session.add(tx)
        db.session.commit()
        # Check that date was set
        assert tx.date is not None
        assert isinstance(tx.date, datetime)

    def test_transaction_zero_amount(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=0, type='expense', date=datetime.now(), author=user, category=cat)
        assert tx.amount == 0

    def test_transaction_large_amount(self, user, make_category):
        cat = make_category('Food', 'expense')
        tx = Transaction(amount=999999.99, type='expense', date=datetime.now(), author=user, category=cat)
        assert tx.amount == 999999.99


class TestBudget:
    def test_budget_creation_with_category(self, user, make_category):
        cat = make_category('Food', 'expense')
        budget = Budget(amount=500, year=2024, month=5, owner=user, category=cat)
        db.session.add(budget)
        db.session.commit()
        assert budget.amount == 500
        assert budget.year == 2024
        assert budget.month == 5
        assert budget.category_id == cat.id

    def test_budget_creation_total_only(self, user):
        budget = Budget(amount=3000, year=2024, month=5, owner=user, category_id=None)
        db.session.add(budget)
        db.session.commit()
        assert budget.amount == 3000
        assert budget.category_id is None

    def test_budget_repr(self, user, make_category):
        cat = make_category('Food', 'expense')
        budget = Budget(amount=100, year=2024, month=5, owner=user, category=cat)
        db.session.add(budget)
        db.session.commit()
        assert repr(budget) == '<Budget 2024-5 - 100.0>'

    def test_budget_repr_total(self, user):
        budget = Budget(amount=2000, year=2024, month=6, owner=user)
        db.session.add(budget)
        db.session.commit()
        assert repr(budget) == '<Budget 2024-6 - 2000.0>'

    def test_budget_zero_amount(self, user):
        budget = Budget(amount=0, year=2024, month=5, owner=user)
        db.session.add(budget)
        db.session.commit()
        assert budget.amount == 0

    def test_budget_large_amount(self, user):
        budget = Budget(amount=999999.99, year=2024, month=5, owner=user)
        db.session.add(budget)
        db.session.commit()
        assert budget.amount == 999999.99

    def test_budget_different_months(self, user, make_category):
        cat = make_category('Food', 'expense')
        b1 = Budget(amount=100, year=2024, month=4, owner=user, category=cat)
        b2 = Budget(amount=150, year=2024, month=5, owner=user, category=cat)
        db.session.add_all([b1, b2])
        db.session.commit()
        # Query to verify
        budgets = Budget.query.filter_by(user_id=user.id, category_id=cat.id).all()
        assert len(budgets) == 2

    def test_budget_different_years(self, user):
        b1 = Budget(amount=1000, year=2023, month=5, owner=user)
        b2 = Budget(amount=2000, year=2024, month=5, owner=user)
        db.session.add_all([b1, b2])
        db.session.commit()
        budgets = Budget.query.filter_by(user_id=user.id).all()
        assert len(budgets) == 2
