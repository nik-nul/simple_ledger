from datetime import datetime
from app import db
from app.models import Category, Transaction, Budget


class TestBudgetTracking:
    
    def test_budget_vs_spending_workflow(self, user, make_category):
        # 1. 创建分类
        food_cat = make_category('Food', 'expense')
        
        # 2. 设置预算
        budget = Budget(amount=500, year=2025, month=5, owner=user, category=food_cat)
        db.session.add(budget)
        db.session.commit()
        
        # 3. 添加多笔交易
        transactions = [
            Transaction(amount=100, type='expense', date=datetime(2025, 5, 1), 
                       author=user, category=food_cat, memo='Groceries'),
            Transaction(amount=50, type='expense', date=datetime(2025, 5, 10),
                       author=user, category=food_cat, memo='Restaurant'),
            Transaction(amount=75, type='expense', date=datetime(2025, 5, 20),
                       author=user, category=food_cat, memo='Takeout'),
        ]
        db.session.add_all(transactions)
        db.session.commit()
        
        # 4. 验证支出计算
        spent = food_cat.get_spent_in_month(2025, 5)
        assert spent == 225.0
        
        # 5. 验证预算剩余
        remaining = budget.amount - spent
        assert remaining == 275.0
        assert spent < budget.amount  # 未超支
    
    def test_multi_category_budget_scenario(self, user, make_category):
        # 创建多个分类
        food = make_category('Food', 'expense')
        transport = make_category('Transport', 'expense')
        income_cat = make_category('Salary', 'income')
        
        # 设置各分类预算
        budgets = [
            Budget(amount=500, year=2025, month=5, owner=user, category=food),
            Budget(amount=200, year=2025, month=5, owner=user, category=transport),
        ]
        db.session.add_all(budgets)
        
        # 添加收入和支出
        transactions = [
            Transaction(amount=3000, type='income', date=datetime(2025, 5, 1),
                       author=user, category=income_cat, memo='Monthly salary'),
            Transaction(amount=300, type='expense', date=datetime(2025, 5, 5),
                       author=user, category=food),
            Transaction(amount=150, type='expense', date=datetime(2025, 5, 7),
                       author=user, category=transport),
        ]
        db.session.add_all(transactions)
        db.session.commit()
        
        # 验证各分类支出
        assert food.get_spent_in_month(2025, 5) == 300.0
        assert transport.get_spent_in_month(2025, 5) == 150.0
        
        # 验证总支出
        total_expense = 450.0
        total_budget = 700.0
        assert total_expense < total_budget
    
    def test_budget_overspending_detection(self, user, make_category):
        cat = make_category('Entertainment', 'expense')
        budget = Budget(amount=100, year=2025, month=5, owner=user, category=cat)
        db.session.add(budget)
        
        # 添加导致超支的交易
        tx = Transaction(amount=150, type='expense', date=datetime(2025, 5, 15),
                        author=user, category=cat, memo='Concert tickets')
        db.session.add(tx)
        db.session.commit()
        
        spent = cat.get_spent_in_month(2025, 5)
        assert spent > budget.amount  # 超支
        overspend = spent - budget.amount
        assert overspend == 50.0


class TestCrossMonthOperations:
    def test_monthly_budget_isolation(self, user, make_category):
        cat = make_category('Food', 'expense')
        
        # 设置不同月份预算
        b1 = Budget(amount=400, year=2025, month=4, owner=user, category=cat)
        b2 = Budget(amount=500, year=2025, month=5, owner=user, category=cat)
        db.session.add_all([b1, b2])
        
        # 添加不同月份交易
        t1 = Transaction(amount=300, type='expense', date=datetime(2025, 4, 15),
                        author=user, category=cat)
        t2 = Transaction(amount=200, type='expense', date=datetime(2025, 5, 15),
                        author=user, category=cat)
        db.session.add_all([t1, t2])
        db.session.commit()
        
        # 验证月份隔离
        assert cat.get_spent_in_month(2025, 4) == 300.0
        assert cat.get_spent_in_month(2025, 5) == 200.0
        
    def test_year_end_transition(self, user, make_category):
        cat = make_category('Savings', 'expense')
        
        b1 = Budget(amount=10000, year=2023, month=1, owner=user, category=cat)
        b2 = Budget(amount=12000, year=2025, month=1, owner=user, category=cat)
        db.session.add_all([b1, b2])
        
        t1 = Transaction(amount=5000, type='expense', date=datetime(2023, 1, 1),
                        author=user, category=cat)
        t2 = Transaction(amount=6000, type='expense', date=datetime(2025, 1, 1),
                        author=user, category=cat)
        db.session.add_all([t1, t2])
        db.session.commit()
        
        assert cat.get_spent_in_month(2023, 1) == 5000.0
        assert cat.get_spent_in_month(2025, 1) == 6000.0


class TestUserDataIsolation:
    def test_multiple_users_isolation(self):
        from app.models import User
        
        # 创建两个用户
        user1 = User(username='alice', email='alice@example.com')
        user1.set_password('pass1')
        user2 = User(username='bob', email='bob@example.com')
        user2.set_password('pass2')
        db.session.add_all([user1, user2])
        
        # 为每个用户创建分类
        cat1 = Category(name='Food', type='expense', owner=user1)
        cat2 = Category(name='Food', type='expense', owner=user2)
        db.session.add_all([cat1, cat2])
        
        # 为每个用户添加交易
        t1 = Transaction(amount=100, type='expense', date=datetime.now(),
                        author=user1, category=cat1)
        t2 = Transaction(amount=200, type='expense', date=datetime.now(),
                        author=user2, category=cat2)
        db.session.add_all([t1, t2])
        db.session.commit()
        
        # 验证数据隔离
        assert user1.transactions.count() == 1
        assert user2.transactions.count() == 1
        assert user1.categories.count() == 1
        assert user2.categories.count() == 1