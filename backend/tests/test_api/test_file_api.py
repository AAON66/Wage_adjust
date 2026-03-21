from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
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
        self.settings = Settings(
            allow_self_registration=True,
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


class MockUrlOpenResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> 'MockUrlOpenResponse':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


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


def test_file_api_upload_replace_parse_preview_and_delete_flow() -> None:
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

        replace_response = client.put(
            f'/api/v1/files/{file_id}',
            headers=headers,
            files=[('file', ('updated.md', b'# Impact\nDelivered internal salary simulator.', 'text/markdown'))],
        )
        assert replace_response.status_code == 200
        assert replace_response.json()['id'] == file_id
        assert replace_response.json()['file_name'] == 'updated.md'
        assert replace_response.json()['parse_status'] == 'pending'

        evidence_after_replace = client.get(f'/api/v1/submissions/{submission_id}/evidence', headers=headers)
        assert evidence_after_replace.status_code == 200
        assert evidence_after_replace.json()['total'] == 0

        reparse_response = client.post(f'/api/v1/files/{file_id}/parse', headers=headers)
        assert reparse_response.status_code == 200
        assert reparse_response.json()['parse_status'] == 'parsed'

        evidence_after_reparse = client.get(f'/api/v1/submissions/{submission_id}/evidence', headers=headers)
        assert evidence_after_reparse.status_code == 200
        assert evidence_after_reparse.json()['total'] == 1
        assert 'Delivered internal salary simulator.' in evidence_after_reparse.json()['items'][0]['content']

        delete_response = client.delete(f'/api/v1/files/{file_id}', headers=headers)
        assert delete_response.status_code == 200
        assert delete_response.json()['deleted_file_id'] == file_id

        list_response = client.get(f'/api/v1/submissions/{submission_id}/files', headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 0

        evidence_after_delete = client.get(f'/api/v1/submissions/{submission_id}/evidence', headers=headers)
        assert evidence_after_delete.status_code == 200
        assert evidence_after_delete.json()['total'] == 0


def test_file_api_github_import_parses_content_immediately() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        submission_id = seed_submission(context)

        with patch(
            'backend.app.services.file_service.urlopen',
            return_value=MockUrlOpenResponse(b'# README\nShipped GitHub based enablement notes.'),
        ):
            import_response = client.post(
                f'/api/v1/submissions/{submission_id}/github-import',
                headers=headers,
                json={'url': 'https://github.com/openai/platform/blob/main/README.md'},
            )

        assert import_response.status_code == 201
        assert import_response.json()['file_name'] == 'README.md'
        assert import_response.json()['parse_status'] == 'parsed'

        list_response = client.get(f'/api/v1/submissions/{submission_id}/files', headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 1

        evidence_response = client.get(f'/api/v1/submissions/{submission_id}/evidence', headers=headers)
        assert evidence_response.status_code == 200
        assert evidence_response.json()['total'] == 1
        assert 'Shipped GitHub based enablement notes.' in evidence_response.json()['items'][0]['content']
