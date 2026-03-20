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
        database_path = (temp_root / f'import-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
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


def register_and_login_admin(client: TestClient) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': 'admin@example.com', 'password': 'Password123', 'role': 'admin'},
    )
    assert register_response.status_code == 201
    return register_response.json()['tokens']['access_token']


def test_import_api_flow() -> None:
    client, _ = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}

        employee_csv = '\n'.join([
            'employee_no,name,department,job_family,job_level,status,manager_employee_no',
            'EMP-2001,Alice Zhang,Engineering,Platform,P5,active,',
        ]).encode('utf-8')
        create_response = client.post(
            '/api/v1/imports/jobs?import_type=employees',
            files={'file': ('employees.csv', employee_csv, 'text/csv')},
            headers=headers,
        )
        assert create_response.status_code == 201
        job_id = create_response.json()['id']
        assert create_response.json()['success_rows'] == 1

        list_response = client.get('/api/v1/imports/jobs', headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 1

        detail_response = client.get(f'/api/v1/imports/jobs/{job_id}', headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()['import_type'] == 'employees'

        template_response = client.get('/api/v1/imports/templates/employees', headers=headers)
        assert template_response.status_code == 200
        assert 'attachment; filename=employees_template.csv' in template_response.headers['content-disposition']

        export_response = client.get(f'/api/v1/imports/jobs/{job_id}/export', headers=headers)
        assert export_response.status_code == 200
        assert 'attachment;' in export_response.headers['content-disposition']
        assert 'Employee imported.' in export_response.text

        xlsx_response = client.post(
            '/api/v1/imports/jobs?import_type=employees',
            files={'file': ('employees.xlsx', b'fake-xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            headers=headers,
        )
        assert xlsx_response.status_code == 201
        assert xlsx_response.json()['status'] == 'failed'
