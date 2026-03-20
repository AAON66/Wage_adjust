from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.services.evaluation_service import EvaluationService


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'evaluation-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def test_evaluation_service_generates_and_reviews_evaluation() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-4001',
            name='Eval User',
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
            EvidenceItem(submission_id=submission.id, source_type='self_report', title='Impact', content='Delivered strong AI workflow improvements.', confidence_score=0.82, metadata_json={}),
            EvidenceItem(submission_id=submission.id, source_type='file_parse', title='Docs', content='Evidence from uploaded files confirms repeated delivery gains.', confidence_score=0.77, metadata_json={}),
        ])
        db.commit()

        service = EvaluationService(db)
        evaluation = service.generate_evaluation(submission.id)
        assert evaluation.ai_level in {'Level 3', 'Level 4', 'Level 5'}
        assert len(evaluation.dimension_scores) == 5
        assert evaluation.status in {'generated', 'needs_review'}

        reviewed = service.manual_review(
            evaluation.id,
            ai_level='Level 4',
            overall_score=88,
            explanation='Manual review confirmed stronger impact.',
            dimension_updates=[{'dimension_code': 'IMPACT', 'raw_score': 92, 'rationale': 'Validated by reviewer.'}],
        )
        assert reviewed is not None
        assert reviewed.status == 'reviewed'
        assert reviewed.ai_level == 'Level 4'

        confirmed = service.confirm_evaluation(evaluation.id)
        assert confirmed is not None
        assert confirmed.status == 'confirmed'
    finally:
        db.close()