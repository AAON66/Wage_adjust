from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.audit_log import AuditLog
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.salary_service import SalaryService


def create_db_context():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'audit-service-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    session_factory = create_session_factory(settings)
    return settings, session_factory


def seed_audit_entities(session_factory) -> dict[str, str]:
    db = session_factory()
    try:
        admin = User(email='admin@example.com', hashed_password='x', role='admin')
        manager = User(email='manager@example.com', hashed_password='x', role='manager')
        employee = Employee(
            employee_no='EMP-9001',
            name='Audit Test User',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
        cycle = EvaluationCycle(
            name='2026 Audit Cycle',
            review_period='2026',
            budget_amount='8000.00',
            status='published',
        )
        db.add_all([admin, manager, employee, cycle])
        db.commit()
        for item in [admin, manager, employee, cycle]:
            db.refresh(item)

        submission = EmployeeSubmission(
            employee_id=employee.id,
            cycle_id=cycle.id,
            status='evaluated',
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=80,
            ai_level='Level 3',
            confidence_score=0.75,
            explanation='Audit baseline.',
            status='pending_hr',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(
            evaluation_id=evaluation.id,
            current_salary='50000.00',
            recommended_ratio=0.10,
            recommended_salary='55000.00',
            ai_multiplier=1.10,
            certification_bonus=0.0,
            final_adjustment_ratio=0.10,
            status='recommended',
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return {
            'admin_id': admin.id,
            'manager_id': manager.id,
            'evaluation_id': evaluation.id,
            'recommendation_id': recommendation.id,
        }
    finally:
        db.close()


def test_audit_log_schema() -> None:
    """AUDIT-01: AuditLog must have operator_role and request_id columns.

    FAILS until Phase 4 Plan 02 adds those columns to the model and migration.
    """
    # These assertions fail because the columns don't exist on the model yet
    assert hasattr(AuditLog, 'operator_role'), 'AuditLog missing column: operator_role'
    assert hasattr(AuditLog, 'request_id'), 'AuditLog missing column: request_id'


def test_manual_review_writes_audit() -> None:
    """AUDIT-03: EvaluationService.manual_review must accept operator= and request_id= kwargs
    and write an AuditLog row with those values.

    FAILS because the current signature does not accept operator/request_id params.
    """
    _, session_factory = create_db_context()
    ids = seed_audit_entities(session_factory)

    db = session_factory()
    try:
        admin = db.get(User, ids['admin_id'])
        assert admin is not None

        service = EvaluationService(db)
        # Call with new expected signature — TypeError until Plan 02 adds these params
        service.manual_review(
            ids['evaluation_id'],
            ai_level='Level 3',
            overall_score=82.0,
            explanation='Manual review by admin.',
            dimension_updates=[],
            operator=admin,
            request_id='req-test-001',
        )

        logs = list(db.scalars(
            select(AuditLog).where(AuditLog.target_type == 'evaluation')
        ))
        assert len(logs) >= 1
        assert any(log.action == 'manual_review' for log in logs)
        matching = [log for log in logs if log.action == 'manual_review']
        assert matching[0].operator_id == ids['admin_id']
        assert matching[0].operator_role == 'admin'
        assert matching[0].request_id == 'req-test-001'
    finally:
        db.close()


def test_hr_review_writes_audit() -> None:
    """AUDIT-03: EvaluationService.hr_review must accept operator= and request_id= kwargs
    and write an AuditLog row with those values.

    FAILS because the current signature does not accept operator/request_id params.
    """
    _, session_factory = create_db_context()
    ids = seed_audit_entities(session_factory)

    db = session_factory()
    try:
        admin = db.get(User, ids['admin_id'])
        assert admin is not None

        service = EvaluationService(db)
        # Seed manager_score so hr_review precondition passes
        evaluation = db.get(AIEvaluation, ids['evaluation_id'])
        assert evaluation is not None
        evaluation.manager_score = 80.0
        db.add(evaluation)
        db.commit()

        # Call with new expected signature — TypeError until Plan 02 adds these params
        service.hr_review(
            ids['evaluation_id'],
            decision='approved',
            comment='HR approved.',
            final_score=80.0,
            operator=admin,
            request_id='req-test-002',
        )

        logs = list(db.scalars(
            select(AuditLog).where(AuditLog.target_type == 'evaluation')
        ))
        assert len(logs) >= 1
        assert any(log.action == 'hr_review' for log in logs)
        matching = [log for log in logs if log.action == 'hr_review']
        assert matching[0].operator_id == ids['admin_id']
        assert matching[0].operator_role == 'admin'
        assert matching[0].request_id == 'req-test-002'
    finally:
        db.close()


def test_salary_update_audit_has_operator() -> None:
    """AUDIT-03: SalaryService.update_recommendation must record a non-None operator_id
    in the AuditLog row it writes.

    FAILS because the current implementation always writes operator_id=None.
    """
    _, session_factory = create_db_context()
    ids = seed_audit_entities(session_factory)

    db = session_factory()
    try:
        admin = db.get(User, ids['admin_id'])
        assert admin is not None

        service = SalaryService(db)
        # Call with new expected operator= kwarg — TypeError until Plan 02 adds this param
        service.update_recommendation(
            ids['recommendation_id'],
            final_adjustment_ratio=0.12,
            status='adjusted',
            operator=admin,
        )

        logs = list(db.scalars(
            select(AuditLog).where(
                AuditLog.target_type == 'salary_recommendation',
                AuditLog.action == 'salary_updated',
            )
        ))
        assert len(logs) >= 1
        assert logs[0].operator_id is not None
        assert logs[0].operator_id == ids['admin_id']
    finally:
        db.close()


def test_audit_atomicity() -> None:
    """AUDIT-01: If the AuditLog write fails after the business mutation,
    the entire transaction must roll back — evaluation status must remain unchanged.

    FAILS because evaluation mutations currently commit before the audit write,
    so a forced audit failure leaves the evaluation in a mutated state (no atomicity).
    """
    _, session_factory = create_db_context()
    ids = seed_audit_entities(session_factory)

    # Seed manager_score so hr_review precondition passes
    setup_db = session_factory()
    try:
        evaluation = setup_db.get(AIEvaluation, ids['evaluation_id'])
        assert evaluation is not None
        evaluation.manager_score = 80.0
        setup_db.add(evaluation)
        setup_db.commit()
    finally:
        setup_db.close()

    db = session_factory()
    try:
        service = EvaluationService(db)

        original_add = db.add
        call_count = [0]

        def patched_add(obj):
            if isinstance(obj, AuditLog):
                call_count[0] += 1
                raise RuntimeError('Simulated audit write failure')
            return original_add(obj)

        db.add = patched_add  # type: ignore[method-assign]

        try:
            service.hr_review(
                ids['evaluation_id'],
                decision='approved',
                comment='Atomicity test.',
                final_score=80.0,
            )
        except Exception:
            pass

        db.add = original_add
        db.rollback()
    finally:
        db.close()

    # After the forced audit failure, the evaluation status must NOT have changed
    # (full rollback required). Currently FAILS because hr_review commits the
    # evaluation mutation before writing the audit log — no atomicity guarantee.
    fresh_db = session_factory()
    try:
        refreshed = fresh_db.get(AIEvaluation, ids['evaluation_id'])
        assert refreshed is not None
        assert refreshed.status == 'pending_hr', (
            f'Expected status=pending_hr after audit failure rollback, got {refreshed.status!r}. '
            'Atomicity not guaranteed: evaluation committed before audit write.'
        )
    finally:
        fresh_db.close()
