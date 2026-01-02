from hypothesis import given, settings, strategies as st
from app.forms import (
    RegistrationForm, LoginForm, CategoryForm, 
    SearchForm, DateRangeForm
)
import pytest
from decimal import InvalidOperation
from datetime import date, timedelta

settings.register_profile("default", max_examples=3000)
settings.load_profile("default")

@given(
    username=st.text(min_size=2, max_size=64),
    email=st.emails(),
    password=st.text(min_size=6, max_size=128)
)
def test_registration_form_fuzzing(app, username, email, password):
    """模糊测试注册表单"""
    with app.app_context():
        form_data = {
            'username': username,
            'email': email,
            'password': password,
            'password2': password
        }
        try:
            form = RegistrationForm(data=form_data)
            assert hasattr(form, 'username')
            assert hasattr(form, 'email')
        except Exception as e:
            pytest.fail(f"表单处理异常: {e}")


@given(
    email=st.one_of(
        st.emails(),
        st.text(min_size=1, max_size=100),
        st.just(''),
        st.just('invalid@'),
        st.just('@invalid.com'),
        st.just('no-at-sign.com')
    ),
    password=st.text(min_size=0, max_size=200),
    remember_me=st.booleans()
)
def test_login_form_fuzzing(app, email, password, remember_me):
    """模糊测试登录表单，测试各种有效和无效的邮箱格式"""
    with app.app_context():
        form_data = {
            'email': email,
            'password': password,
            'remember_me': remember_me
        }
        try:
            form = LoginForm(data=form_data)
            # 表单应该能够创建，但可能验证失败
            assert hasattr(form, 'email')
            assert hasattr(form, 'password')
            assert hasattr(form, 'remember_me')
        except Exception as e:
            pytest.fail(f"登录表单处理异常: {e}")


# ==================== 分类表单模糊测试 ====================

@given(
    name=st.text(min_size=0, max_size=150),
    type_choice=st.sampled_from(['expense', 'income', 'invalid', ''])
)
def test_category_form_fuzzing(app, name, type_choice):
    """模糊测试分类表单，测试各种分类名称和类型"""
    with app.app_context():
        form_data = {
            'name': name,
            'type': type_choice
        }
        try:
            form = CategoryForm(data=form_data)
            assert hasattr(form, 'name')
            assert hasattr(form, 'type')
            # 验证表单，可能成功或失败
            form.validate()
        except Exception as e:
            pytest.fail(f"分类表单处理异常: {e}")


# ==================== 搜索表单模糊测试 ====================

@given(
    keyword=st.one_of(st.none(), st.text(min_size=0, max_size=200)),
    min_amount=st.one_of(
        st.none(),
        st.decimals(min_value=0, max_value=999999, places=2),
        st.decimals(min_value=-1000, max_value=-0.01, places=2)  # 负数
    ),
    max_amount=st.one_of(
        st.none(),
        st.decimals(min_value=0, max_value=999999, places=2),
        st.decimals(min_value=-1000, max_value=-0.01, places=2)  # 负数
    ),
    days_before=st.integers(min_value=0, max_value=365),
    days_after=st.integers(min_value=0, max_value=365)
)
def test_search_form_fuzzing(app, keyword, min_amount, max_amount, days_before, days_after):
    """模糊测试搜索表单，测试各种搜索条件组合"""
    with app.app_context():
        # 生成随机日期
        today = date.today()
        start_date = today - timedelta(days=days_before)
        end_date = today + timedelta(days=days_after)
        
        form_data = {
            'keyword': keyword,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'start_date': start_date,
            'end_date': end_date
        }
        try:
            form = SearchForm(data=form_data)
            assert hasattr(form, 'keyword')
            assert hasattr(form, 'min_amount')
            assert hasattr(form, 'max_amount')
            # 表单应能处理各种输入，包括 None 和负数
            form.validate()
        except (ValueError, InvalidOperation, TypeError):
            # 某些无效的 Decimal 值可能抛出异常，这是预期的
            pass
        except Exception as e:
            pytest.fail(f"搜索表单处理异常: {e}")

# ==================== 日期范围表单模糊测试 ====================

@given(
    month=st.integers(min_value=1, max_value=12),
    year=st.integers(min_value=2020, max_value=2030)
)
def test_date_range_form_fuzzing(app, month, year):
    """模糊测试日期范围表单"""
    with app.app_context():
        form_data = {
            'month': str(month),
            'year': str(year)
        }
        try:
            form = DateRangeForm(data=form_data)
            assert hasattr(form, 'month')
            assert hasattr(form, 'year')
            # 表单应该能够处理所有有效的月份和年份
            form.validate()
        except Exception as e:
            pytest.fail(f"日期范围表单处理异常: {e}")

