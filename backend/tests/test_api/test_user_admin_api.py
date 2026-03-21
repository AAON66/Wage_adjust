from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'user-admin-{uuid4().hex}.db').as_posix()
        uploads_path = (temp_root / f'user-admin-uploads-{uuid4().hex}').as_posix()
        self.settings = Settings(allow_self_registration=True, database_url=f'sqlite+pysqlite:///{database_path}', storage_base_dir=uploads_path)
        load_model_modules()
        self.engine = create_db_engine(self.settings)
        init_database(self.engine)
        self.session_factory = create_session_factory(self.settings)

    def override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()



def build_client() -> tuple[TestClient, ApiDatabaseContext]:
    context = ApiDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app), context



def register_user(client: TestClient, *, email: str, role: str, password: str = 'Password123') -> str:
    response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password, 'role': role},
    )
    assert response.status_code == 201
    return response.json()['tokens']['access_token']



def create_employee(client: TestClient, headers: dict[str, str], *, employee_no: str, name: str) -> str:
    response = client.post(
        '/api/v1/employees',
        json={
            'employee_no': employee_no,
            'name': name,
            'department': '产品技术中心',
            'job_family': '平台研发',
            'job_level': 'P5',
            'manager_id': None,
            'status': 'active',
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()['id']



def test_admin_can_manage_lower_roles_but_not_admin_peers() -> None:
    client, _ = build_client()
    with client:
        admin_token = register_user(client, email='admin@example.com', role='admin')
        register_user(client, email='peer-admin@example.com', role='admin')
        headers = {'Authorization': f'Bearer {admin_token}'}

        create_response = client.post(
            '/api/v1/users',
            json={'email': 'hrbp@example.com', 'password': 'Password123', 'role': 'hrbp'},
            headers=headers,
        )
        assert create_response.status_code == 201
        hrbp_user_id = create_response.json()['id']
        assert create_response.json()['must_change_password'] is True

        list_response = client.get('/api/v1/users?page=1&page_size=20&keyword=example', headers=headers)
        assert list_response.status_code == 200
        listed_emails = {item['email'] for item in list_response.json()['items']}
        assert 'admin@example.com' in listed_emails
        assert 'peer-admin@example.com' not in listed_emails
        assert 'hrbp@example.com' in listed_emails

        cannot_create_admin = client.post(
            '/api/v1/users',
            json={'email': 'new-admin@example.com', 'password': 'Password123', 'role': 'admin'},
            headers=headers,
        )
        assert cannot_create_admin.status_code == 400
        assert cannot_create_admin.json()['message'] == 'You cannot create accounts with the same or higher role level.'

        peer_admin_me = client.post('/api/v1/auth/login', json={'email': 'peer-admin@example.com', 'password': 'Password123'})
        peer_admin_token = peer_admin_me.json()['access_token']
        peer_admin_profile = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {peer_admin_token}'})
        peer_admin_id = peer_admin_profile.json()['id']

        cannot_reset_peer_admin = client.patch(
            f'/api/v1/users/{peer_admin_id}/password',
            json={'new_password': 'ResetPassword123'},
            headers=headers,
        )
        assert cannot_reset_peer_admin.status_code == 400
        assert cannot_reset_peer_admin.json()['message'] == 'You cannot manage accounts with the same or higher role level.'

        delete_response = client.delete(f'/api/v1/users/{hrbp_user_id}', headers=headers)
        assert delete_response.status_code == 200



def test_manager_and_hrbp_can_only_manage_employees() -> None:
    client, _ = build_client()
    with client:
        admin_token = register_user(client, email='admin@example.com', role='admin')
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        hrbp_create = client.post('/api/v1/users', json={'email': 'hrbp@example.com', 'password': 'Password123', 'role': 'hrbp'}, headers=admin_headers)
        manager_create = client.post('/api/v1/users', json={'email': 'manager@example.com', 'password': 'Password123', 'role': 'manager'}, headers=admin_headers)
        employee_create = client.post('/api/v1/users', json={'email': 'employee@example.com', 'password': 'Password123', 'role': 'employee'}, headers=admin_headers)
        assert hrbp_create.status_code == 201
        assert manager_create.status_code == 201
        assert employee_create.status_code == 201

        hrbp_token = client.post('/api/v1/auth/login', json={'email': 'hrbp@example.com', 'password': 'Password123'}).json()['access_token']
        manager_token = client.post('/api/v1/auth/login', json={'email': 'manager@example.com', 'password': 'Password123'}).json()['access_token']
        hrbp_headers = {'Authorization': f'Bearer {hrbp_token}'}
        manager_headers = {'Authorization': f'Bearer {manager_token}'}

        hrbp_list = client.get('/api/v1/users?page=1&page_size=20', headers=hrbp_headers)
        assert hrbp_list.status_code == 200
        hrbp_visible = {item['email'] for item in hrbp_list.json()['items']}
        assert hrbp_visible == {'hrbp@example.com', 'employee@example.com'}

        manager_list = client.get('/api/v1/users?page=1&page_size=20', headers=manager_headers)
        assert manager_list.status_code == 200
        manager_visible = {item['email'] for item in manager_list.json()['items']}
        assert manager_visible == {'manager@example.com', 'employee@example.com'}

        hrbp_create_employee = client.post(
            '/api/v1/users',
            json={'email': 'employee2@example.com', 'password': 'Password123', 'role': 'employee'},
            headers=hrbp_headers,
        )
        assert hrbp_create_employee.status_code == 201

        hrbp_cannot_create_manager = client.post(
            '/api/v1/users',
            json={'email': 'manager2@example.com', 'password': 'Password123', 'role': 'manager'},
            headers=hrbp_headers,
        )
        assert hrbp_cannot_create_manager.status_code == 400
        assert hrbp_cannot_create_manager.json()['message'] == 'You cannot create accounts with the same or higher role level.'

        manager_id = manager_create.json()['id']
        hrbp_cannot_reset_manager = client.patch(
            f'/api/v1/users/{manager_id}/password',
            json={'new_password': 'ResetPassword123'},
            headers=hrbp_headers,
        )
        assert hrbp_cannot_reset_manager.status_code == 400
        assert hrbp_cannot_reset_manager.json()['message'] == 'You cannot manage accounts with the same or higher role level.'

        employee_id = employee_create.json()['id']
        manager_reset_employee = client.patch(
            f'/api/v1/users/{employee_id}/password',
            json={'new_password': 'ResetPassword123'},
            headers=manager_headers,
        )
        assert manager_reset_employee.status_code == 200

        manager_cannot_delete_hrbp = client.delete(f"/api/v1/users/{hrbp_create.json()['id']}", headers=manager_headers)
        assert manager_cannot_delete_hrbp.status_code == 400
        assert manager_cannot_delete_hrbp.json()['message'] == 'You cannot manage accounts with the same or higher role level.'



def test_binding_employee_profile_updates_auth_me() -> None:
    client, _ = build_client()
    with client:
        admin_token = register_user(client, email='admin@example.com', role='admin')
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        employee_account = client.post('/api/v1/users', json={'email': 'employee@example.com', 'password': 'Password123', 'role': 'employee'}, headers=admin_headers)
        assert employee_account.status_code == 201
        employee_user_id = employee_account.json()['id']

        employee_record_id = create_employee(client, admin_headers, employee_no='EMP-9001', name='陈曦')

        bind_response = client.patch(
            f'/api/v1/users/{employee_user_id}/binding',
            json={'employee_id': employee_record_id},
            headers=admin_headers,
        )
        assert bind_response.status_code == 200
        assert bind_response.json()['employee_id'] == employee_record_id
        assert bind_response.json()['employee_name'] == '陈曦'
        assert bind_response.json()['employee_no'] == 'EMP-9001'

        employee_login = client.post('/api/v1/auth/login', json={'email': 'employee@example.com', 'password': 'Password123'})
        employee_token = employee_login.json()['access_token']
        me_response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {employee_token}'})
        assert me_response.status_code == 200
        assert me_response.json()['employee_id'] == employee_record_id
        assert me_response.json()['employee_name'] == '陈曦'

        unbind_response = client.patch(
            f'/api/v1/users/{employee_user_id}/binding',
            json={'employee_id': None},
            headers=admin_headers,
        )
        assert unbind_response.status_code == 200
        assert unbind_response.json()['employee_id'] is None



def test_binding_respects_unique_employee_profile_constraint() -> None:
    client, _ = build_client()
    with client:
        admin_token = register_user(client, email='admin@example.com', role='admin')
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        first_user = client.post('/api/v1/users', json={'email': 'employee1@example.com', 'password': 'Password123', 'role': 'employee'}, headers=admin_headers)
        second_user = client.post('/api/v1/users', json={'email': 'employee2@example.com', 'password': 'Password123', 'role': 'employee'}, headers=admin_headers)
        employee_record_id = create_employee(client, admin_headers, employee_no='EMP-9002', name='李雨桐')

        first_bind = client.patch(
            f"/api/v1/users/{first_user.json()['id']}/binding",
            json={'employee_id': employee_record_id},
            headers=admin_headers,
        )
        assert first_bind.status_code == 200

        second_bind = client.patch(
            f"/api/v1/users/{second_user.json()['id']}/binding",
            json={'employee_id': employee_record_id},
            headers=admin_headers,
        )
        assert second_bind.status_code == 400
        assert second_bind.json()['message'] == 'This employee profile is already bound to another account.'



def test_employee_cannot_access_user_management() -> None:
    client, _ = build_client()
    with client:
        employee_token = register_user(client, email='employee@example.com', role='employee')
        headers = {'Authorization': f'Bearer {employee_token}'}

        response = client.get('/api/v1/users', headers=headers)
        assert response.status_code == 403



def test_self_safeguards_still_apply() -> None:
    client, _ = build_client()
    with client:
        first_admin_token = register_user(client, email='admin@example.com', role='admin')
        headers = {'Authorization': f'Bearer {first_admin_token}'}

        current_user_response = client.get('/api/v1/auth/me', headers=headers)
        current_user_id = current_user_response.json()['id']

        cannot_delete_self = client.delete(f'/api/v1/users/{current_user_id}', headers=headers)
        assert cannot_delete_self.status_code == 400
        assert cannot_delete_self.json()['message'] == 'You cannot delete the currently logged-in account.'

        cannot_reset_self = client.patch(
            f'/api/v1/users/{current_user_id}/password',
            json={'new_password': 'ResetPassword123'},
            headers=headers,
        )
        assert cannot_reset_self.status_code == 400
        assert cannot_reset_self.json()['message'] == 'Please use personal settings to change the current account password.'
