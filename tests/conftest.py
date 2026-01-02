import os
import sys

# Ensure project root is on sys.path for test imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from config import Config
from app import create_app, db
from app.models import User, Category


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


def _fresh_app():
    return create_app(TestConfig)


@pytest.fixture(scope="session")
def app():
    app = _fresh_app()
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


@pytest.fixture(autouse=True)
def clean_database(app):
    db.session.remove()
    db.drop_all()
    db.create_all()
    yield
    db.session.remove()


@pytest.fixture
def user():
    u = User(username='tester', email='tester@example.com')
    u.set_password('secret123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def make_category(user):
    def _make(name='Food', type='expense'):
        owner = db.session.merge(user)
        c = Category(name=name, type=type, owner=owner)
        db.session.add(c)
        db.session.commit()
        return c
    return _make


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, user, make_category):
    # Ensure at least one expense and one income category exist for forms
    make_category('Food', 'expense')
    make_category('Salary', 'income')
    resp = client.post('/auth/login', data={
        'email': user.email,
        'password': 'secret123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Reset session identity map to avoid cross-request conflicts
    db.session.remove()
    return client
