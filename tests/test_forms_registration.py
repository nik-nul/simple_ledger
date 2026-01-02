from app.forms import RegistrationForm


def test_registration_form_valid_input(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='newuser',
            email='new@example.com',
            password='password123',
            password2='password123'
        )
        assert form.validate()


def test_registration_form_missing_username(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='',
            email='new@example.com',
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'username' in form.errors


def test_registration_form_username_too_short(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='a',
            email='new@example.com',
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'username' in form.errors


def test_registration_form_username_too_long(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='a' * 65,
            email='new@example.com',
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'username' in form.errors


def test_registration_form_duplicate_username(app, user):
    with app.test_request_context():
        form = RegistrationForm(
            username=user.username,
            email='different@example.com',
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'username' in form.errors


def test_registration_form_invalid_email(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='newuser',
            email='not-an-email',
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'email' in form.errors


def test_registration_form_duplicate_email(app, user):
    with app.test_request_context():
        form = RegistrationForm(
            username='differentuser',
            email=user.email,
            password='password123',
            password2='password123'
        )
        assert not form.validate()
        assert 'email' in form.errors


def test_registration_form_missing_password(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='newuser',
            email='new@example.com',
            password='',
            password2='password123'
        )
        assert not form.validate()
        assert 'password' in form.errors


def test_registration_form_password_too_short(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='newuser',
            email='new@example.com',
            password='short',
            password2='short'
        )
        assert not form.validate()
        assert 'password' in form.errors


def test_registration_form_password_mismatch(app):
    with app.test_request_context():
        form = RegistrationForm(
            username='newuser',
            email='new@example.com',
            password='password123',
            password2='different456'
        )
        assert not form.validate()
        assert 'password2' in form.errors
