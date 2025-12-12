# app/main/routes.py
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import Transaction, Category, Budget
from app.forms import TransactionForm, CategoryForm, BudgetForm, SearchForm, DateRangeForm, get_user_expense_categories, get_user_income_categories, ConfirmDeleteForm
from datetime import datetime, date
from sqlalchemy import func, extract
import calendar

# --- 帮助函数：解析日期 ---
def get_date_range(year_str, month_str):
    """根据传入的年份和月份字符串，获取该月的第一天和最后一天"""
    try:
        year = int(year_str)
        month = int(month_str)
    except (ValueError, TypeError):
        today = date.today()
        year, month = today.year, today.month

    # 获取月份的最后一天
    _, last_day = calendar.monthrange(year, month)
   
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, last_day, 23, 59, 59)
   
    return start_date, end_date, year, month

# --- 1. 仪表盘 (首页) & 记账 ---
@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """主页面，显示本月收支和结余，包括数字，折线和饼图，提供月份切换，链接到其余页面；提供记账表单，支持收入和支出两种类型的记账。具有预算提醒功能，采用不同颜色标注预算情况。"""
    # --- 日期筛选逻辑 ---
    date_form = DateRangeForm(request.args)
    year_str = request.args.get('year', str(date.today().year))
    month_str = request.args.get('month', str(date.today().month))
   
    # 设置表单默认值
    if request.method == 'GET':
        date_form.year.data = year_str
        date_form.month.data = month_str

    start_date, end_date, year, month = get_date_range(year_str, month_str)

    # --- 记账表单逻辑 ---
    # 我们使用两个表单实例，并用 prefix 区分
    expense_form = TransactionForm(prefix='exp')
    income_form = TransactionForm(prefix='inc')
   
    # 动态设置表单的分类
    expense_form.category.query_factory = get_user_expense_categories
    income_form.category.query_factory = get_user_income_categories
    income_form.type.data = 'income' # 预设收入表单的类型

    # 处理支出表单提交
    if expense_form.validate_on_submit() and expense_form.submit.data:
        t = Transaction(
            amount=expense_form.amount.data,
            type='expense',
            date=expense_form.date.data,
            memo=expense_form.memo.data,
            author=current_user,
            category=expense_form.category.data
        )
        db.session.add(t)
        db.session.commit()
        flash('支出记录已添加！', 'success')
        return redirect(url_for('main.index', year=year, month=month))

    # 处理收入表单提交
    if income_form.validate_on_submit() and income_form.submit.data:
        t = Transaction(
            amount=income_form.amount.data,
            type='income',
            date=income_form.date.data,
            memo=income_form.memo.data,
            author=current_user,
            category=income_form.category.data
        )
        db.session.add(t)
        db.session.commit()
        flash('收入记录已添加！', 'success')
        return redirect(url_for('main.index', year=year, month=month))

    # --- 仪表盘统计数据查询 (GET) ---
   
    # 1. 总收支与结余
    total_income_q = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date.between(start_date, end_date)
    ).scalar() or 0.0

    total_expense_q = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date.between(start_date, end_date)
    ).scalar() or 0.0

    balance = total_income_q - total_expense_q
   
    stats = {
        'income': total_income_q,
        'expense': total_expense_q,
        'balance': balance
    }

    # 2. 预算提醒
    budget_warnings = []
   
    # 查询总预算
    total_budget_q = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.year == year,
        Budget.month == month,
        Budget.category_id == None
    ).first()

    if total_budget_q:
        spent_percent = (total_expense_q / total_budget_q.amount) * 100 if total_budget_q.amount > 0 else 0
        budget_warnings.append({
            'name': '月度总预算',
            'amount': total_budget_q.amount,
            'spent': total_expense_q,
            'percent': round(spent_percent, 2),
        })

    # 查询分类预算
    category_budgets_q = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.year == year,
        Budget.month == month,
        Budget.category_id != None
    ).join(Category).all()

    for cb in category_budgets_q:
        spent_in_category = cb.category.get_spent_in_month(year, month)
        spent_percent = (spent_in_category / cb.amount) * 100 if cb.amount > 0 else 0
        budget_warnings.append({
            'name': cb.category.name,
            'amount': cb.amount,
            'spent': spent_in_category,
            'percent': round(spent_percent, 2),
        })

    # 3. 最近 5 笔交易
    recent_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.id.desc()).limit(5).all()

    # 删除表单（用于在模板中包含 CSRF token）
    delete_form = ConfirmDeleteForm()

    return render_template('index.html',
                           title='仪表盘',
                           expense_form=expense_form,
                           income_form=income_form,
                           date_form=date_form,
                           stats=stats,
                           budget_warnings=budget_warnings,
                           recent_transactions=recent_transactions,
                           current_year=year,
                           current_month=month,
                           delete_form=delete_form)

# --- 2. API 端点 (用于图表) ---

@bp.route('/api/chart-data')
@login_required
def chart_data():
    year_str = request.args.get('year', str(date.today().year))
    month_str = request.args.get('month', str(date.today().month))
   
    start_date, end_date, _, _ = get_date_range(year_str, month_str)

    # 1. 支出分类饼图 (当月)
    pie_data_q = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date.between(start_date, end_date)
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()
   
    pie_data = {
        'labels': [row.name for row in pie_data_q],
        'data': [float(row.total) for row in pie_data_q]
    }

    # 2. 收支趋势折线图 (最近6个月)
    # (为了简化，我们暂时也只显示当月的每日趋势)
    # 一个更复杂的查询会 group by (最近6个的) 'year-month'
   
    # 我们改为查询 "当月每日收支"
    line_data_expense = db.session.query(
        extract('day', Transaction.date).label('day'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date.between(start_date, end_date)
    ).group_by('day').all()
   
    line_data_income = db.session.query(
        extract('day', Transaction.date).label('day'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date.between(start_date, end_date)
    ).group_by('day').all()

    # 准备 Chart.js 数据
    days_in_month = end_date.day
    line_labels = list(range(1, days_in_month + 1))
    expense_by_day = [0.0] * days_in_month
    income_by_day = [0.0] * days_in_month

    for row in line_data_expense:
        expense_by_day[int(row.day) - 1] = float(row.total)
    for row in line_data_income:
        income_by_day[int(row.day) - 1] = float(row.total)

    line_data = {
        'labels': line_labels,
        'expense': expense_by_day,
        'income': income_by_day
    }

    return jsonify({'pie_data': pie_data, 'line_data': line_data})


# --- 3. 交易查找与筛选 ---

@bp.route('/transactions')
@login_required
def transactions():
    """可以根据关键词、分类、时间范围、金额区间等多种条件组合查找交易，支持分页显示，并统计总收入、总支出和总结余。"""
    page = request.args.get('page', 1, type=int)
    # 使用 request.args 填充表单，使其在 GET 请求后保持状态
    form = SearchForm(request.args)
   
    query = Transaction.query.filter_by(author=current_user)
   
    # 动态构建查询
    if form.keyword.data:
        query = query.filter(Transaction.memo.ilike(f"%{form.keyword.data}%"))
       
    if form.category.data:
        query = query.filter(Transaction.category_id == form.category.data.id)
   
    if form.start_date.data:
        query = query.filter(Transaction.date >= form.start_date.data)
   
    if form.end_date.data:
        # 包含当天
        query = query.filter(Transaction.date <= datetime.combine(form.end_date.data, datetime.max.time()))
       
    if form.min_amount.data:
        query = query.filter(Transaction.amount >= form.min_amount.data)
       
    if form.max_amount.data:
        query = query.filter(Transaction.amount <= form.max_amount.data)

    # 排序和分页
    results = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=20)

    # 统计总收入、总支出、总结余
    total_income = query.filter(Transaction.type == 'income').with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    total_expense = query.filter(Transaction.type == 'expense').with_entities(func.sum(Transaction.amount)).scalar() or 0.0
    stats = {
        'income': total_income,
        'expense': total_expense,
        'balance': total_income - total_expense
    }

    # 用于删除操作的简单 CSRF 表单
    delete_form = ConfirmDeleteForm()

    return render_template('transactions.html', title='交易查找', form=form, transactions=results, delete_form=delete_form, stats=stats)


# --- 6. 交易编辑与删除 ---
@bp.route('/transaction/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """可以编辑交易所有的信息，包括金额、类型、分类、日期和备注。"""
    t = Transaction.query.get_or_404(id)
    if t.author != current_user:
        flash('没有权限编辑此交易。', 'danger')
        return redirect(url_for('main.transactions'))

    form = TransactionForm(obj=t)
    # 根据当前交易类型设置分类查询
    if t.type == 'expense':
        form.category.query_factory = get_user_expense_categories
    else:
        form.category.query_factory = get_user_income_categories

    # 确保表单显示已有值（GET 请求）
    if request.method == 'GET':
        try:
            form.amount.data = t.amount
            form.type.data = t.type
            # Transaction.date may be datetime; TransactionForm.date is a date field
            form.date.data = t.date.date() if hasattr(t.date, 'date') else t.date
            form.memo.data = t.memo
            form.category.data = t.category
        except Exception:
            pass

    if form.validate_on_submit():
        t.amount = float(form.amount.data)
        t.type = form.type.data
        t.date = form.date.data
        t.memo = form.memo.data
        t.category = form.category.data
        db.session.commit()
        flash('交易已更新。', 'success')
        # 优先返回原页面
        return redirect(url_for('main.index'))

    return render_template('transaction_edit.html', title='编辑交易', form=form, transaction=t)


@bp.route('/transaction/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    form = ConfirmDeleteForm()
    # 需要表单验证以包含 CSRF token
    if form.validate_on_submit():
        t = Transaction.query.get_or_404(id)
        if t.author != current_user:
            flash('没有权限删除此交易。', 'danger')
            return redirect(request.referrer or url_for('main.index'))

        db.session.delete(t)
        db.session.commit()
        flash('交易已删除。', 'success')
    else:
        flash('未能确认删除操作。', 'warning')

    return redirect(request.referrer or url_for('main.index'))

# --- 4. 分类管理 (CRUD) ---
@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    """分类管理页面，支持添加新分类，显示已有分类，编辑和删除分类。"""
    form = CategoryForm()
   
    if form.validate_on_submit():
        # 检查分类是否已存在 (同名同类型)
        exists = Category.query.filter_by(
            owner=current_user,
            name=form.name.data,
            type=form.type.data
        ).first()
       
        if not exists:
            category = Category(
                name=form.name.data,
                type=form.type.data,
                owner=current_user
            )
            db.session.add(category)
            db.session.commit()
            flash('分类已添加。', 'success')
        else:
            flash('同名同类型的分类已存在。', 'warning')
        return redirect(url_for('main.categories'))
   
    # GET: 显示所有分类
    expense_categories = Category.query.filter_by(owner=current_user, type='expense').order_by(Category.name).all()
    income_categories = Category.query.filter_by(owner=current_user, type='income').order_by(Category.name).all()
   
    return render_template('categories.html',
                           title='分类管理',
                           form=form,
                           expense_categories=expense_categories,
                           income_categories=income_categories)

@bp.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    if category.owner != current_user:
        return redirect(url_for('main.categories')) # 或者 403 Forbidden
   
    new_name = request.form.get('name')
    if new_name and len(new_name) > 0:
        # 检查重名
        exists = Category.query.filter(
            Category.id != id,
            Category.owner == current_user,
            Category.name == new_name,
            Category.type == category.type
        ).first()
       
        if not exists:
            category.name = new_name
            db.session.commit()
            flash('分类已更新。', 'success')
        else:
            flash('同名分类已存在。', 'warning')
           
    return redirect(url_for('main.categories'))

@bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if category.owner != current_user:
        return redirect(url_for('main.categories'))
   
    # 检查是否有交易关联
    if category.transactions.count() > 0:
        flash('无法删除：该分类下已有交易记录。', 'danger')
        return redirect(url_for('main.categories'))
   
    # 检查是否有预算关联
    if category.budgets.count() > 0:
        flash('无法删除：该分类已设置预算。', 'danger')
        return redirect(url_for('main.categories'))

    db.session.delete(category)
    db.session.commit()
    flash('分类已删除。', 'success')
    return redirect(url_for('main.categories'))


# --- 5. 预算管理 ---
@bp.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    """预算管理页面，支持为各分类和总支出设置预算"""
    # 预算总是基于 年/月 设置
    date_form = DateRangeForm(request.args)
    year_str = request.args.get('year', str(date.today().year))
    month_str = request.args.get('month', str(date.today().month))
   
    if request.method == 'GET':
        date_form.year.data = year_str
        date_form.month.data = month_str
       
    year, month = int(year_str), int(month_str)
   
    form = BudgetForm()
   
    if form.validate_on_submit():
        category_id = form.category.data.id if form.category.data else None
       
        # 查找是否已存在该预算 (UPSERT 逻辑)
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            year=year,
            month=month,
            category_id=category_id
        ).first()
       
        if existing_budget:
            # 更新
            existing_budget.amount = form.amount.data
            flash('预算已更新。', 'info')
        else:
            # 创建
            new_budget = Budget(
                amount=form.amount.data,
                year=year,
                month=month,
                user_id=current_user.id,
                category_id=category_id
            )
            db.session.add(new_budget)
            flash('预算已设置。', 'success')
           
        db.session.commit()
        return redirect(url_for('main.budget', year=year, month=month))
       
    # GET: 显示当前选定月份的所有已设预算
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        year=year,
        month=month
    ).all()
   
    # 为了方便显示，将其处理成字典
    budget_map = {b.category_id: b for b in budgets}
   
    # 获取所有支出分类，用于显示
    expense_categories = Category.query.filter_by(owner=current_user, type='expense').all()
   
    return render_template('budget.html',
                           title='预算管理',
                           form=form,
                           date_form=date_form,
                           budgets=budget_map,
                           expense_categories=expense_categories,
                           current_year=year,
                           current_month=month)