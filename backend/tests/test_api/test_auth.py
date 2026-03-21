from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules


class AuthDatabaseContext:
    def __init__(self, *, allow_self_registration: bool) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'auth-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            allow_self_registration=allow_self_registration,
            database_url=f'sqlite+pysqlite:///{database_path}',
        )
        self.engine = create_db_engine(self.settings)
        self.session_factory = create_session_factory(self.settings)
        load_model_modules()
        init_database(self.engine)

    def override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()


def build_test_client(*, allow_self_registration: bool = True) -> TestClient:
    context = AuthDatabaseContext(allow_self_registration=allow_self_registration)
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app)


def test_register_login_refresh_and_me_flow() -> None:
    with build_test_client() as client:
        register_response = client.post(
            '/api/v1/auth/register',
            json={
                'email': 'owner@example.com',
                'password': 'Password123',
                'role': 'admin',
            },
        )
        assert register_response.status_code == 201
        register_body = register_response.json()
        assert register_body['user']['email'] == 'owner@example.com'
        assert register_body['user']['must_change_password'] is False
        access_token = register_body['tokens']['access_token']
        refresh_token = register_body['tokens']['refresh_token']

        me_response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        assert me_response.status_code == 200
        assert me_response.json()['role'] == 'admin'
        assert me_response.json()['must_change_password'] is False

        login_response = client.post(
            '/api/v1/auth/login',
            json={'email': 'owner@example.com', 'password': 'Password123'},
        )
        assert login_response.status_code == 200
        assert login_response.json()['token_type'] == 'bearer'

        refresh_response = client.post(
            '/api/v1/auth/refresh',
            json={'refresh_token': refresh_token},
        )
        assert refresh_response.status_code == 200
        assert refresh_response.json()['access_token']


def test_duplicate_registration_returns_conflict() -> None:
    with build_test_client() as client:
        payload = {
            'email': 'duplicate@example.com',
            'password': 'Password123',
            'role': 'employee',
        }
        assert client.post('/api/v1/auth/register', json=payload).status_code == 201

        duplicate_response = client.post('/api/v1/auth/register', json=payload)
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()['error'] == 'http_error'


def test_invalid_login_and_invalid_token_are_rejected() -> None:
    with build_test_client() as client:
        client.post(
            '/api/v1/auth/register',
            json={
                'email': 'person@example.com',
                'password': 'Password123',
                'role': 'employee',
            },
        )

        login_response = client.post(
            '/api/v1/auth/login',
            json={'email': 'person@example.com', 'password': 'WrongPassword'},
        )
        assert login_response.status_code == 401

        me_response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': 'Bearer invalid-token'},
        )
        assert me_response.status_code == 401
        assert me_response.json()['error'] == 'http_error'


def test_register_is_forbidden_when_self_registration_disabled() -> None:
    with build_test_client(allow_self_registration=False) as client:
        response = client.post(
            '/api/v1/auth/register',
            json={
                'email': 'blocked@example.com',
                'password': 'Password123',
                'role': 'employee',
            },
        )
        assert response.status_code == 403
        assert response.json()['error'] == 'http_error'
        assert response.json()['message'] == 'Self registration is disabled.'


def test_user_can_change_password() -> None:
    with build_test_client() as client:
        register_response = client.post(
            '/api/v1/auth/register',
            json={
                'email': 'change-password@example.com',
                'password': 'Password123',
                'role': 'employee',
            },
        )
        access_token = register_response.json()['tokens']['access_token']

        change_response = client.post(
            '/api/v1/auth/change-password',
            json={'current_password': 'Password123', 'new_password': 'Password1234'},
            headers={'Authorization': f'Bearer {access_token}'},
        )
        assert change_response.status_code == 200
        assert change_response.json()['message'] == 'Password updated successfully.'

        old_login = client.post('/api/v1/auth/login', json={'email': 'change-password@example.com', 'password': 'Password123'})
        assert old_login.status_code == 401

        new_login = client.post('/api/v1/auth/login', json={'email': 'change-password@example.com', 'password': 'Password1234'})
        assert new_login.status_code == 200

        me_response = client.get('/api/v1/auth/me', headers={'Authorization': f"Bearer {new_login.json()['access_token']}"})
        assert me_response.status_code == 200
        assert me_response.json()['must_change_password'] is False


def test_change_password_validates_current_password() -> None:
    with build_test_client() as client:
        register_response = client.post(
            '/api/v1/auth/register',
            json={
                'email': 'wrong-current@example.com',
                'password': 'Password123',
                'role': 'employee',
            },
        )
        access_token = register_response.json()['tokens']['access_token']

        change_response = client.post(
            '/api/v1/auth/change-password',
            json={'current_password': 'WrongPassword', 'new_password': 'Password1234'},
            headers={'Authorization': f'Bearer {access_token}'},
        )
        assert change_response.status_code == 400
        assert change_response.json()['message'] == 'Current password is incorrect.'


def test_admin_created_user_must_change_password_before_normal_access() -> None:
    with build_test_client() as client:
        admin_register = client.post(
            '/api/v1/auth/register',
            json={
                'email': 'admin@example.com',
                'password': 'Password123',
                'role': 'admin',
            },
        )
        admin_token = admin_register.json()['tokens']['access_token']
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        create_response = client.post(
            '/api/v1/users',
            json={'email': 'new-user@example.com', 'password': 'TempPassword123!', 'role': 'employee'},
            headers=admin_headers,
        )
        assert create_response.status_code == 201
        assert create_response.json()['must_change_password'] is True

        employee_login = client.post('/api/v1/auth/login', json={'email': 'new-user@example.com', 'password': 'TempPassword123!'})
        assert employee_login.status_code == 200
        employee_token = employee_login.json()['access_token']

        me_before_change = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {employee_token}'})
        assert me_before_change.status_code == 200
        assert me_before_change.json()['must_change_password'] is True

        change_response = client.post(
            '/api/v1/auth/change-password',
            json={'current_password': 'TempPassword123!', 'new_password': 'BetterPassword123!'},
            headers={'Authorization': f'Bearer {employee_token}'},
        )
        assert change_response.status_code == 200

        relogin = client.post('/api/v1/auth/login', json={'email': 'new-user@example.com', 'password': 'BetterPassword123!'})
        assert relogin.status_code == 200
        relogin_token = relogin.json()['access_token']

        me_after_change = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {relogin_token}'})
        assert me_after_change.status_code == 200
        assert me_after_change.json()['must_change_password'] is False
