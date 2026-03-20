from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'public-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}', public_api_key='test-public-key')
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


def seed_public_data(context: ApiDatabaseContext) -> tuple[str, str]:
    db = context.session_factory()
    try:
        cycle = EvaluationCycle(name='2026 Public', review_period='2026', budget_amount='12000.00', status='published')
        employee = Employee(employee_no='EMP-3001', name='Public User', department='Engineering', job_family='Platform', job_level='P6', status='active')
        approver = User(email='approver@example.com', hashed_password='x', role='admin')
        db.add_all([cycle, employee, approver])
        db.commit()
        db.refresh(cycle)
        db.refresh(employee)
        db.refresh(approver)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(submission_id=submission.id, overall_score=91, ai_level='Level 5', confidence_score=0.9, explanation='Excellent', status='confirmed')
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(evaluation_id=evaluation.id, current_salary='60000.00', recommended_ratio=0.15, recommended_salary='69000.00', ai_multiplier=1.18, certification_bonus=0.0, final_adjustment_ratio=0.15, status='approved')
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        db.add(ApprovalRecord(recommendation_id=recommendation.id, approver_id=approver.id, step_name='committee', decision='approved', comment='Approved'))
        db.commit()
        return cycle.id, employee.employee_no
    finally:
        db.close()


def test_public_api_key_and_read_endpoints() -> None:
    client, context = build_client()
    with client:
        cycle_id, employee_no = seed_public_data(context)
        headers = {'X-API-Key': context.settings.public_api_key}

        missing_key = client.get(f'/api/v1/public/employees/{employee_no}/latest-evaluation')
        assert missing_key.status_code == 401

        latest_response = client.get(f'/api/v1/public/employees/{employee_no}/latest-evaluation', headers=headers)
        assert latest_response.status_code == 200
        assert latest_response.json()['employee_no'] == employee_no
        assert latest_response.json()['salary_recommendation']['status'] == 'approved'

        salary_results_response = client.get(f'/api/v1/public/cycles/{cycle_id}/salary-results', headers=headers)
        assert salary_results_response.status_code == 200
        assert salary_results_response.json()['total'] == 1

        approval_status_response = client.get(f'/api/v1/public/cycles/{cycle_id}/approval-status', headers=headers)
        assert approval_status_response.status_code == 200
        assert approval_status_response.json()['items'][0]['approved_steps'] == 1

        dashboard_summary_response = client.get('/api/v1/public/dashboard/summary', headers=headers)
        assert dashboard_summary_response.status_code == 200
        assert len(dashboard_summary_response.json()['overview']) == 4

        db = context.session_factory()
        try:
            assert db.query(AuditLog).count() == 4
        finally:
            db.close()
