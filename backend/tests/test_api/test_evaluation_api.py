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



def register_user(client: TestClient, *, email: str, role: str) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': role},
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



def test_evaluation_api_small_gap_auto_confirms() -> None:
    client, context = build_client()
    with client:
        admin_token = register_user(client, email='admin@example.com', role='admin')
        headers = {'Authorization': f'Bearer {admin_token}'}
        submission_id = seed_submission_with_evidence(context)

        generate_response = client.post('/api/v1/evaluations/generate', json={'submission_id': submission_id}, headers=headers)
        assert generate_response.status_code == 201
        evaluation_id = generate_response.json()['id']
        ai_score = generate_response.json()['ai_overall_score']

        review_response = client.patch(
            f'/api/v1/evaluations/{evaluation_id}/manual-review',
            json={
                'overall_score': round(ai_score + 4, 2),
                'explanation': '主管评分与 AI 接近，可直接取平均。',
                'dimension_scores': [
                    {'dimension_code': 'IMPACT', 'raw_score': 90, 'rationale': '主管确认业务影响力较高。'}
                ],
            },
            headers=headers,
        )
        assert review_response.status_code == 200
        assert review_response.json()['status'] == 'confirmed'
        assert review_response.json()['manager_score'] == round(ai_score + 4, 2)
        assert review_response.json()['score_gap'] <= 10



def test_evaluation_api_large_gap_goes_to_hr_and_can_be_returned_or_approved() -> None:
    client, context = build_client()
    with client:
        manager_token = register_user(client, email='manager@example.com', role='manager')
        hrbp_token = register_user(client, email='hrbp@example.com', role='hrbp')
        manager_headers = {'Authorization': f'Bearer {manager_token}'}
        hr_headers = {'Authorization': f'Bearer {hrbp_token}'}
        submission_id = seed_submission_with_evidence(context)

        generate_response = client.post('/api/v1/evaluations/generate', json={'submission_id': submission_id}, headers=manager_headers)
        assert generate_response.status_code == 201
        evaluation_id = generate_response.json()['id']
        ai_score = generate_response.json()['ai_overall_score']

        review_response = client.patch(
            f'/api/v1/evaluations/{evaluation_id}/manual-review',
            json={
                'overall_score': round(ai_score + 18, 2),
                'explanation': '主管认为本次表现明显高于 AI 结果。',
                'dimension_scores': [
                    {'dimension_code': 'IMPACT', 'raw_score': 96, 'rationale': '主管补充了更多业务背景。'}
                ],
            },
            headers=manager_headers,
        )
        assert review_response.status_code == 200
        assert review_response.json()['status'] == 'pending_hr'
        assert review_response.json()['needs_manual_review'] is True

        return_response = client.patch(
            f'/api/v1/evaluations/{evaluation_id}/hr-review',
            json={'decision': 'returned', 'comment': '请主管补充更多客观证据后重新评分。'},
            headers=hr_headers,
        )
        assert return_response.status_code == 200
        assert return_response.json()['status'] == 'returned'
        assert return_response.json()['hr_decision'] == 'returned'

        approve_response = client.patch(
            f'/api/v1/evaluations/{evaluation_id}/hr-review',
            json={'decision': 'approved', 'comment': 'HR 审核通过，采用折中后的最终评分。', 'final_score': round(ai_score + 9, 2)},
            headers=hr_headers,
        )
        assert approve_response.status_code == 200
        assert approve_response.json()['status'] == 'confirmed'
        assert approve_response.json()['hr_decision'] == 'approved'
        assert approve_response.json()['overall_score'] == round(ai_score + 9, 2)
