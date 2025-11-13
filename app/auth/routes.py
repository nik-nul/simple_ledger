# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.models import User, Category
from app.forms import LoginForm, RegistrationForm

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('无效的邮箱或密码。', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # 检查 'next' 参数
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        return redirect(next_page)
        
    return render_template('login.html', title='登录', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        
        # !! 关键：为新用户创建预设分类 !!
        default_categories = [
            Category(name='餐饮', type='expense', owner=user),
            Category(name='交通', type='expense', owner=user),
            Category(name='购物', type='expense', owner=user),
            Category(name='娱乐', type='expense', owner=user),
            Category(name='住房', type='expense', owner=user),
            Category(name='其他支出', type='expense', owner=user),
            Category(name='工资', type='income', owner=user),
            Category(name='理财', type='income', owner=user),
            Category(name='其他收入', type='income', owner=user),
        ]
        
        db.session.add_all(default_categories)
        db.session.commit()
        
        flash('恭喜，您已成功注册！请登录。', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', title='注册', form=form)