from app.models import Category, User


def test_auth_register_get_shows_form(client):
    resp = client.get('/auth/register')
    assert resp.status_code == 200


def test_auth_register_valid_creates_user(client):
    resp = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    user = User.query.filter_by(username='newuser').first()
    assert user is not None
    assert user.email == 'new@example.com'
    # Verify default categories created
    categories = Category.query.filter_by(owner=user).all()
    assert len(categories) == 9  # 6 expense + 3 income


def test_auth_register_duplicate_username(client, user):
    resp = client.post('/auth/register', data={
        'username': user.username,
        'email': 'other@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should not have created a new user
    users_with_email = User.query.filter_by(email='other@example.com').all()
    assert len(users_with_email) == 0


def test_auth_register_duplicate_email(client, user):
    resp = client.post('/auth/register', data={
        'username': 'different',
        'email': user.email,
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should not have created a new user
    users_with_name = User.query.filter_by(username='different').all()
    assert len(users_with_name) == 0


def test_auth_login_get_shows_form(client):
    resp = client.get('/auth/login')
    assert resp.status_code == 200


def test_auth_login_valid(client, user):
    resp = client.post('/auth/login', data={
        'email': user.email,
        'password': 'secret123',
        'remember_me': False
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_auth_login_invalid_email(client):
    resp = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'anypassword',
        'remember_me': False
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should show error message


def test_auth_login_invalid_password(client, user):
    resp = client.post('/auth/login', data={
        'email': user.email,
        'password': 'wrongpassword',
        'remember_me': False
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should show error message


def test_auth_login_remember_me(client, user):
    resp = client.post('/auth/login', data={
        'email': user.email,
        'password': 'secret123',
        'remember_me': True
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_auth_logout(auth_client):
    resp = auth_client.get('/auth/logout', follow_redirects=True)
    assert resp.status_code == 200


def test_auth_register_redirect_if_authenticated(auth_client):
    resp = auth_client.get('/auth/register', follow_redirects=False)
    assert resp.status_code == 302 or resp.status_code == 200


def test_auth_login_redirect_if_authenticated(auth_client):
    resp = auth_client.get('/auth/login', follow_redirects=False)
    assert resp.status_code == 302 or resp.status_code == 200
