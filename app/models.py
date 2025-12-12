# app/models.py
from app import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

# Flask-Login 需要的回调函数，用于从 session 重新加载用户对象
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
   
    transactions = db.relationship('Transaction', backref='author', lazy='dynamic', cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='owner', lazy='dynamic', cascade="all, delete-orphan")
    budgets = db.relationship('Budget', backref='owner', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False, default='expense')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    budgets = db.relationship('Budget', backref='category', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Category {self.name}>'

    # 帮助函数：获取本分类在某月的总花费
    def get_spent_in_month(self, year, month):
        total = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == self.id,
            Transaction.type == 'expense',
            func.extract('year', Transaction.date) == year,
            func.extract('month', Transaction.date) == month
        ).scalar()
        return total or 0.0

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False, default='expense')
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    memo = db.Column(db.String(200))
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        return f'<Transaction {self.id} - {self.amount}>'

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
   
    # 如果 category_id 为空, 表示这是月度总预算
    # 如果有值, 表示是特定分类的预算
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    def __repr__(self):
        return f'<Budget {self.year}-{self.month} - {self.amount}>'