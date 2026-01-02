from datetime import datetime

from app import db
from app.models import Transaction, Budget, Category


def create_transaction(user, category, amount=10, type_='expense', dt=None, memo='m'):
    dt = dt or datetime(2024, 5, 1)
    user = db.session.merge(user)
    category = db.session.merge(category)
    tx = Transaction(amount=amount, type=type_, date=dt, memo=memo, author=user, category=category)
    db.session.add(tx)
    db.session.commit()
    return tx


def test_index_get_shows_page(auth_client):
    resp = auth_client.get('/')
    assert resp.status_code == 200
    assert b'<!doctype html' in resp.data


def test_index_post_expense_creates_transaction(auth_client, make_category, user):
    expense_cat = make_category('Groceries', 'expense')
    resp = auth_client.post('/', data={
        'exp-amount': '12.50',
        'exp-type': 'expense',
        'exp-category': expense_cat.id,
        'exp-date': '2024-05-02',
        'exp-memo': 'milk',
        'exp-submit': True
    }, follow_redirects=True)
    assert resp.status_code == 200
    tx = Transaction.query.filter_by(memo='milk').first()
    assert tx is not None
    assert tx.amount == 12.5


def test_chart_data_returns_day_totals(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    create_transaction(user, cat, amount=5, dt=datetime(2024, 5, 1))
    create_transaction(user, cat, amount=7, dt=datetime(2024, 5, 2))
    resp = auth_client.get('/api/chart-data?year=2024&month=5')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['pie_data']['data'] == [12.0]
    assert data['line_data']['expense'][0] == 5.0
    assert data['line_data']['expense'][1] == 7.0


def test_transactions_filter_by_keyword_and_stats(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    create_transaction(user, cat, amount=10, memo='coffee')
    create_transaction(user, cat, amount=5, memo='tea', dt=datetime(2024, 5, 2))
    resp = auth_client.get('/transactions?keyword=cof')
    assert resp.status_code == 200
    assert b'coffee' in resp.data and b'tea' not in resp.data


def test_transactions_date_and_amount_filters(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    create_transaction(user, cat, amount=20, dt=datetime(2024, 5, 5))
    create_transaction(user, cat, amount=5, dt=datetime(2024, 5, 10))
    resp = auth_client.get('/transactions?start_date=2024-05-06&max_amount=10')
    assert resp.status_code == 200
    assert b'5.0' in resp.data and b'20.0' not in resp.data


def test_budget_create_and_update(auth_client, make_category, user):
    expense_cat = make_category('Transport', 'expense')
    # create
    resp = auth_client.post('/budget?year=2024&month=5', data={
        'amount': '100',
        'category': expense_cat.id,
        'submit': True
    }, follow_redirects=True)
    assert resp.status_code == 200
    budget = Budget.query.filter_by(user_id=user.id, category_id=expense_cat.id, year=2024, month=5).first()
    assert budget and budget.amount == 100
    # update
    resp2 = auth_client.post('/budget?year=2024&month=5', data={
        'amount': '150',
        'category': expense_cat.id,
        'submit': True
    }, follow_redirects=True)
    assert resp2.status_code == 200
    db.session.refresh(budget)
    assert budget.amount == 150


def test_categories_add_edit_and_delete_without_links(auth_client, user):
    # add
    resp = auth_client.post('/categories', data={
        'name': 'Books',
        'type': 'expense',
        'submit': True
    }, follow_redirects=True)
    assert resp.status_code == 200
    category = Category.query.filter_by(name='Books').first()
    assert category
    # edit
    resp_edit = auth_client.post(f'/categories/edit/{category.id}', data={'name': 'Reading'}, follow_redirects=True)
    assert resp_edit.status_code == 200
    db.session.refresh(category)
    assert category.name == 'Reading'
    # delete
    resp_del = auth_client.post(f'/categories/delete/{category.id}', follow_redirects=True)
    assert resp_del.status_code == 200
    assert Category.query.get(category.id) is None


def test_delete_category_blocked_when_transactions_exist(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    create_transaction(user, cat, 10)
    resp = auth_client.post(f'/categories/delete/{cat.id}', follow_redirects=True)
    assert resp.status_code == 200
    # still exists
    assert Category.query.get(cat.id) is not None


def test_edit_transaction_get_and_post(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    tx = create_transaction(user, cat, 11.5, memo='old', dt=datetime(2024, 5, 3))
    # GET
    resp_get = auth_client.get(f'/transaction/edit/{tx.id}')
    assert resp_get.status_code == 200
    # POST update
    resp_post = auth_client.post(f'/transaction/edit/{tx.id}', data={
        'amount': '20',
        'type': 'expense',
        'category': cat.id,
        'date': '2024-05-04',
        'memo': 'new',
        'submit': True
    }, follow_redirects=True)
    assert resp_post.status_code == 200
    db.session.refresh(tx)
    assert tx.amount == 20
    assert tx.memo == 'new'


def test_delete_transaction(auth_client, make_category, user):
    cat = make_category('Food', 'expense')
    tx = create_transaction(user, cat, 9.9, memo='to-delete')
    resp = auth_client.post(f'/transaction/delete/{tx.id}', data={'submit': True}, follow_redirects=True)
    assert resp.status_code == 200
    assert Transaction.query.get(tx.id) is None
