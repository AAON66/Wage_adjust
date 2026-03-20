from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.approval_service import ApprovalService


def create_db_context() -> tuple[object, object]:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'approval-service-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    session_factory = create_session_factory(settings)
    return settings, session_factory


def seed_workflow_entities(session_factory) -> dict[str, str]:
    db = session_factory()
    try:
        admin = User(email='admin@example.com', hashed_password='x', role='admin')
        hrbp = User(email='hrbp@example.com', hashed_password='x', role='hrbp')
        manager = User(email='manager@example.com', hashed_password='x', role='manager')
        employee = Employee(
            employee_no='EMP-8201',
            name='Approval Flow User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Calibration', review_period='2026', budget_amount='9000.00', status='published')
        db.add_all([admin, hrbp, manager, employee, cycle])
        db.commit()
        for item in [admin, hrbp, manager, employee, cycle]:
            db.refresh(item)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=86,
            ai_level='Level 4',
            confidence_score=0.83,
            explanation='Calibration candidate.',
            status='needs_review',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(
            evaluation_id=evaluation.id,
            current_salary='60000.00',
            recommended_ratio=0.12,
            recommended_salary='67200.00',
            ai_multiplier=1.13,
            certification_bonus=0.0,
            final_adjustment_ratio=0.12,
            status='recommended',
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return {
            'admin_id': admin.id,
            'hrbp_id': hrbp.id,
            'manager_id': manager.id,
            'recommendation_id': recommendation.id,
            'evaluation_id': evaluation.id,
        }
    finally:
        db.close()


def test_submit_decide_and_list_workflow() -> None:
    _, session_factory = create_db_context()
    ids = seed_workflow_entities(session_factory)

    db = session_factory()
    try:
        service = ApprovalService(db)
        recommendation = service.submit_for_approval(
            recommendation_id=ids['recommendation_id'],
            steps=[
                {'step_name': 'hr_review', 'approver_id': ids['hrbp_id'], 'comment': 'HRBP review'},
                {'step_name': 'committee', 'approver_id': ids['manager_id'], 'comment': 'Committee review'},
            ],
        )
        assert recommendation.status == 'pending_approval'
        assert len(recommendation.approval_records) == 2

        hrbp = db.get(User, ids['hrbp_id'])
        manager = db.get(User, ids['manager_id'])
        assert hrbp is not None
        assert manager is not None

        my_items = service.list_approvals(current_user=hrbp)
        assert len(my_items) == 1
        assert my_items[0].step_name == 'hr_review'

        approved = service.decide_approval(
            my_items[0].id,
            current_user=hrbp,
            decision='approved',
            comment='Looks good.',
        )
        assert approved is not None
        assert approved.recommendation.status == 'pending_approval'

        manager_item = service.list_approvals(current_user=manager)[0]
        rejected = service.decide_approval(
            manager_item.id,
            current_user=manager,
            decision='rejected',
            comment='Budget needs recalibration.',
        )
        assert rejected is not None
        assert rejected.recommendation.status == 'rejected'

        history = service.list_history(ids['recommendation_id'])
        assert len(history) == 2
        queue = service.list_calibration_queue()
        assert len(queue) == 1
        assert queue[0].id == ids['evaluation_id']
    finally:
        db.close()

