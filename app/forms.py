# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, DateField, DecimalField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models import User, Category
from flask_login import current_user
from datetime import date

# --- 认证表单 ---

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致。')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册。')

# --- 动态分类查询 (用于表单) ---

def get_user_expense_categories():
    if current_user.is_authenticated:
        return Category.query.filter_by(owner=current_user, type='expense').order_by(Category.name)
    return Category.query.none()

def get_user_income_categories():
    if current_user.is_authenticated:
        return Category.query.filter_by(owner=current_user, type='income').order_by(Category.name)
    return Category.query.none()

def get_all_user_categories():
    if current_user.is_authenticated:
        return Category.query.filter_by(owner=current_user).order_by(Category.name)
    return Category.query.none()


# --- 主应用表单 ---

class TransactionForm(FlaskForm):
    amount = DecimalField('金额', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    # 类型字段将帮助我们在路由中决定使用哪个分类查询
    type = SelectField('类型', choices=[('expense', '支出'), ('income', '收入')], validators=[DataRequired()])
    # 我们将在路由中动态设置此字段的 query_factory
    category = QuerySelectField('分类', get_label='name', allow_blank=False, validators=[DataRequired()])
    date = DateField('日期', validators=[DataRequired()], default=date.today)
    memo = TextAreaField('备注', validators=[Optional(), Length(max=200)])
    submit = SubmitField('保存')

class CategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired(), Length(min=1, max=100)])
    type = SelectField('类型', choices=[('expense', '支出'), ('income', '收入')], validators=[DataRequired()])
    submit = SubmitField('保存分类')

class BudgetForm(FlaskForm):
    amount = DecimalField('预算金额', validators=[DataRequired(), NumberRange(min=0)], places=2)
    # 动态查询所有“支出”分类，并允许“总预算”选项
    category = QuerySelectField(
        '预算分类',
        query_factory=get_user_expense_categories,
        get_label='name',
        allow_blank=True,
        blank_text='--- (月度总预算) ---'
    )
    submit = SubmitField('设置预算')

class SearchForm(FlaskForm):
    keyword = StringField('关键词 (备注)', validators=[Optional()])
    category = QuerySelectField('分类', query_factory=get_all_user_categories, get_label='name', allow_blank=True, blank_text='-- 所有分类 --')
    start_date = DateField('开始日期', validators=[Optional()])
    end_date = DateField('结束日期', validators=[Optional()])
    min_amount = DecimalField('最小金额', validators=[Optional()])
    max_amount = DecimalField('最大金额', validators=[Optional()])
    submit = SubmitField('搜索')

class DateRangeForm(FlaskForm):
    # 用于仪表盘和统计页面的日期筛选
    # 我们将使用 'month' 和 'year' 作为主要筛选方式
    # 'custom' 稍显复杂，我们先实现 按月/按年
    month = SelectField('月份', choices=[(str(i), f'{i}月') for i in range(1, 13)], default=str(date.today().month))
    year = SelectField('年份', choices=[(str(i), f'{i}年') for i in range(date.today().year - 5, date.today().year + 2)], default=str(date.today().year))
    submit = SubmitField('查看')


class ConfirmDeleteForm(FlaskForm):
    """简单的删除确认表单（用于在模板中包含 CSRF token）"""
    submit = SubmitField('删除')