from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'files-api-{uuid4().hex}.db').as_posix()
        uploads_path = (temp_root / f'files-uploads-{uuid4().hex}').as_posix()
        self.settings = Settings(allow_self_registration=True, 
            database_url=f'sqlite+pysqlite:///{database_path}',
            storage_base_dir=uploads_path,
        )
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


def seed_submission(context: ApiDatabaseContext) -> str:
    db = context.session_factory()
    try:
        employee = Employee(
            employee_no='EMP-3001',
            name='File User',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='1000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='collecting')
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission.id
    finally:
        db.close()


def test_file_api_upload_parse_preview_and_evidence_flow() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        submission_id = seed_submission(context)

        upload_response = client.post(
            f'/api/v1/submissions/{submission_id}/files',
            headers=headers,
            files=[('files', ('notes.md', b'# Impact\nCreated reusable AI workflows.', 'text/markdown'))],
        )
        assert upload_response.status_code == 201
        file_id = upload_response.json()['items'][0]['id']
        assert upload_response.json()['items'][0]['parse_status'] == 'pending'

        list_response = client.get(f'/api/v1/submissions/{submission_id}/files', headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 1

        preview_response = client.get(f'/api/v1/files/{file_id}/preview', headers=headers)
        assert preview_response.status_code == 200
        assert preview_response.json()['preview_url'].startswith('file:///')

        parse_response = client.post(f'/api/v1/files/{file_id}/parse', headers=headers)
        assert parse_response.status_code == 200
        assert parse_response.json()['parse_status'] == 'parsed'
        assert parse_response.json()['evidence_count'] == 1

        evidence_response = client.get(f'/api/v1/submissions/{submission_id}/evidence', headers=headers)
        assert evidence_response.status_code == 200
        assert evidence_response.json()['total'] == 1
        assert 'Created reusable AI workflows.' in evidence_response.json()['items'][0]['content']

        parse_all_response = client.post(f'/api/v1/submissions/{submission_id}/parse-all', headers=headers)
        assert parse_all_response.status_code == 200
        assert parse_all_response.json()['total'] == 1
