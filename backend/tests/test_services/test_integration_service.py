from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.approval import ApprovalRecord
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.integration_service import IntegrationService


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'integration-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def test_integration_service_returns_public_payload_sources() -> None:
    session_factory = build_context()
    db = session_factory()
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

        service = IntegrationService(db)
        latest = service.get_latest_employee_evaluation('EMP-3001')
        assert latest is not None
        assert latest.ai_evaluation is not None
        assert latest.ai_evaluation.ai_level == 'Level 5'

        cycle_result, salary_rows = service.get_cycle_salary_results(cycle.id)
        assert cycle_result is not None
        assert len(salary_rows) == 1

        summary = service.get_dashboard_summary()
        assert len(summary['overview']) == 4

        service.log_public_access(action='public.test', target_type='employee', target_id=employee.id, detail={'employee_no': 'EMP-3001'})
        assert db.query(__import__('backend.app.models.audit_log', fromlist=['AuditLog']).AuditLog).count() == 1
    finally:
        db.close()
