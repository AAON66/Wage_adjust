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
        database_path = (temp_root / f'api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(allow_self_registration=True, database_url=f'sqlite+pysqlite:///{database_path}')
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


def build_client() -> TestClient:
    context = ApiDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app)


def register_and_login_admin(client: TestClient) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': 'admin@example.com', 'password': 'Password123', 'role': 'admin'},
    )
    assert register_response.status_code == 201
    return register_response.json()['tokens']['access_token']


def test_employee_and_cycle_api_flow() -> None:
    with build_client() as client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}

        create_employee_response = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-1001',
                'name': 'Alice Zhang',
                'department': 'Engineering',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=headers,
        )
        assert create_employee_response.status_code == 201
        employee_id = create_employee_response.json()['id']

        list_employees_response = client.get('/api/v1/employees?department=Engineering', headers=headers)
        assert list_employees_response.status_code == 200
        assert list_employees_response.json()['total'] == 1

        detail_response = client.get(f'/api/v1/employees/{employee_id}', headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()['employee_no'] == 'EMP-1001'

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2026 Annual Review',
                'review_period': '2026',
                'budget_amount': '250000.00',
                'status': 'draft',
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 201
        cycle_id = create_cycle_response.json()['id']

        list_cycles_response = client.get('/api/v1/cycles', headers=headers)
        assert list_cycles_response.status_code == 200
        assert list_cycles_response.json()['total'] == 1

        update_cycle_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={'name': '2026 Annual Review Updated', 'status': 'collecting'},
            headers=headers,
        )
        assert update_cycle_response.status_code == 200
        assert update_cycle_response.json()['name'] == '2026 Annual Review Updated'
        assert update_cycle_response.json()['status'] == 'collecting'

        publish_cycle_response = client.post(f'/api/v1/cycles/{cycle_id}/publish', headers=headers)
        assert publish_cycle_response.status_code == 200
        assert publish_cycle_response.json()['status'] == 'published'

        archive_cycle_response = client.post(f'/api/v1/cycles/{cycle_id}/archive', headers=headers)
        assert archive_cycle_response.status_code == 200
        assert archive_cycle_response.json()['status'] == 'archived'

        archived_update_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={'name': 'Should Fail'},
            headers=headers,
        )
        assert archived_update_response.status_code == 400
        assert archived_update_response.json()['message'] == 'Archived cycles cannot be edited.'


def test_employee_list_requires_authentication() -> None:
    with build_client() as client:
        response = client.get('/api/v1/employees')
        assert response.status_code == 401
