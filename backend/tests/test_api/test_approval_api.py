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
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'approval-api-{uuid4().hex}.db').as_posix()
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
    response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': role},
    )
    assert response.status_code == 201
    return response.json()['user']['id']


def login_token(client: TestClient, *, email: str) -> str:
    response = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': 'Password123'},
    )
    assert response.status_code == 200
    return response.json()['access_token']


def seed_recommendation(context: ApiDatabaseContext) -> tuple[str, str]:
    db = context.session_factory()
    try:
        employee = Employee(
            employee_no='EMP-8301',
            name='Approval API User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Approval', review_period='2026', budget_amount='12000.00', status='published')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=90,
            ai_level='Level 4',
            confidence_score=0.87,
            explanation='Ready for approval.',
            status='reviewed',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(
            evaluation_id=evaluation.id,
            current_salary='60000.00',
            recommended_ratio=0.14,
            recommended_salary='68400.00',
            ai_multiplier=1.13,
            certification_bonus=0.0,
            final_adjustment_ratio=0.14,
            status='recommended',
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation.id, evaluation.id
    finally:
        db.close()


def test_approval_api_flow() -> None:
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        hrbp_id = register_user(client, email='hrbp@example.com', role='hrbp')
        manager_id = register_user(client, email='manager@example.com', role='manager')
        register_user(client, email='employee@example.com', role='employee')
        admin_token = login_token(client, email='admin@example.com')
        hrbp_token = login_token(client, email='hrbp@example.com')
        manager_token = login_token(client, email='manager@example.com')
        outsider_token = login_token(client, email='employee@example.com')
        recommendation_id, evaluation_id = seed_recommendation(context)

        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'hr_review', 'approver_id': hrbp_id, 'comment': 'HRBP review'},
                    {'step_name': 'committee', 'approver_id': manager_id, 'comment': 'Committee review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201
        assert submit_response.json()['total'] == 2

        calibration_response = client.get(
            '/api/v1/approvals/calibration-queue',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert calibration_response.status_code == 200
        assert calibration_response.json()['items'][0]['evaluation_id'] == evaluation_id

        hrbp_queue = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {hrbp_token}'})
        assert hrbp_queue.status_code == 200
        assert hrbp_queue.json()['total'] == 1
        hrbp_approval_id = hrbp_queue.json()['items'][0]['id']

        forbidden_response = client.patch(
            f'/api/v1/approvals/{hrbp_approval_id}',
            json={'decision': 'approved', 'comment': 'Not my task.'},
            headers={'Authorization': f'Bearer {outsider_token}'},
        )
        assert forbidden_response.status_code == 403

        approve_response = client.patch(
            f'/api/v1/approvals/{hrbp_approval_id}',
            json={'decision': 'approved', 'comment': 'Looks good.'},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()['recommendation_status'] == 'pending_approval'

        manager_queue = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {manager_token}'})
        assert manager_queue.status_code == 200
        manager_approval_id = manager_queue.json()['items'][0]['id']

        reject_response = client.patch(
            f'/api/v1/approvals/{manager_approval_id}',
            json={'decision': 'rejected', 'comment': 'Need tighter budget.'},
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()['recommendation_status'] == 'rejected'

        history_response = client.get(
            f'/api/v1/approvals/recommendations/{recommendation_id}/history',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert history_response.status_code == 200
        assert history_response.json()['total'] == 2

        admin_queue = client.get(
            '/api/v1/approvals?include_all=true',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert admin_queue.status_code == 200
        assert admin_queue.json()['total'] == 2



