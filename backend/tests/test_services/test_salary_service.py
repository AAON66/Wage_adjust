from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.certification import Certification
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.salary_service import SalaryService


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'salary-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def test_salary_service_recommend_simulate_and_lock() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-6001',
            name='Salary User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='6000.00', status='draft')
        user = User(email='hr@example.com', hashed_password='hash', role='admin')
        db.add_all([employee, cycle, user])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)
        db.refresh(user)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=86,
            ai_level='Level 4',
            confidence_score=0.82,
            explanation='Confirmed evaluation.',
            status='confirmed',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        certification = Certification(
            employee_id=employee.id,
            certification_type='ai_skill',
            certification_stage='advanced',
            bonus_rate=0.02,
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        db.add(certification)
        db.commit()

        service = SalaryService(db)
        recommendation = service.recommend_salary(evaluation.id)
        assert recommendation.status == 'recommended'
        assert recommendation.final_adjustment_ratio > 0

        updated = service.update_recommendation(recommendation.id, final_adjustment_ratio=0.18, status='adjusted')
        assert updated is not None
        assert updated.status == 'adjusted'

        items, budget, total, over_budget = service.simulate_cycle(cycle_id=cycle.id, department=None, job_family=None, budget_amount=None)
        assert len(items) == 1
        assert budget >= total
        assert over_budget is False

        locked = service.lock_recommendation(recommendation.id, user)
        assert locked is not None
        assert locked.status == 'locked'
        assert len(locked.approval_records) == 1
    finally:
        db.close()