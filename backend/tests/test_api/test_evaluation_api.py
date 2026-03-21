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
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'evaluation-api-{uuid4().hex}.db').as_posix()
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


def seed_submission_with_evidence(context: ApiDatabaseContext) -> str:
    db = context.session_factory()
    try:
        employee = Employee(
            employee_no='EMP-5001',
            name='Eval API User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='3000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='reviewing')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        db.add_all([
            EvidenceItem(submission_id=submission.id, source_type='self_report', title='Impact', content='Built reusable AI automation flows.', confidence_score=0.84, metadata_json={}),
            EvidenceItem(submission_id=submission.id, source_type='file_parse', title='Artifacts', content='Uploaded materials confirm consistent delivery impact.', confidence_score=0.79, metadata_json={}),
        ])
        db.commit()
        return submission.id
    finally:
        db.close()


def test_evaluation_api_flow() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        submission_id = seed_submission_with_evidence(context)

        generate_response = client.post('/api/v1/evaluations/generate', json={'submission_id': submission_id}, headers=headers)
        assert generate_response.status_code == 201
        evaluation_id = generate_response.json()['id']
        assert len(generate_response.json()['dimension_scores']) == 5

        get_response = client.get(f'/api/v1/evaluations/{evaluation_id}', headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()['submission_id'] == submission_id

        review_response = client.patch(
            f'/api/v1/evaluations/{evaluation_id}/manual-review',
            json={
                'ai_level': 'Level 4',
                'explanation': 'Manual review upgraded impact.',
                'dimension_scores': [
                    {'dimension_code': 'IMPACT', 'raw_score': 93, 'rationale': 'Validated with stronger business context.'}
                ],
            },
            headers=headers,
        )
        assert review_response.status_code == 200
        assert review_response.json()['status'] == 'reviewed'
        assert review_response.json()['ai_level'] == 'Level 4'

        confirm_response = client.post(f'/api/v1/evaluations/{evaluation_id}/confirm', headers=headers)
        assert confirm_response.status_code == 200
        assert confirm_response.json()['status'] == 'confirmed'

        regenerate_response = client.post('/api/v1/evaluations/regenerate', json={'submission_id': submission_id}, headers=headers)
        assert regenerate_response.status_code == 200
        assert regenerate_response.json()['submission_id'] == submission_id
