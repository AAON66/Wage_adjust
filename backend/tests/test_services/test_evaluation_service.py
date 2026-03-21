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



def test_evaluation_service_auto_confirms_when_manager_gap_is_small() -> None:
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
        reviewed = service.manual_review(
            evaluation.id,
            ai_level=None,
            overall_score=evaluation.ai_overall_score + 5,
            explanation='主管评分与 AI 接近，允许自动取平均。',
            dimension_updates=[{'dimension_code': 'IMPACT', 'raw_score': 92, 'rationale': 'Validated by reviewer.'}],
        )
        assert reviewed is not None
        assert reviewed.status == 'confirmed'
        assert reviewed.manager_score == round(evaluation.ai_overall_score + 5, 2)
        assert reviewed.score_gap == 5.0
    finally:
        db.close()



def test_evaluation_service_routes_large_gap_to_hr_review() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-4002',
            name='Eval User Two',
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
            EvidenceItem(submission_id=submission.id, source_type='self_report', title='Impact', content='Built strong self-report evidence.', confidence_score=0.82, metadata_json={}),
            EvidenceItem(submission_id=submission.id, source_type='file_parse', title='Docs', content='Uploaded files show stable delivery gains.', confidence_score=0.77, metadata_json={}),
        ])
        db.commit()

        service = EvaluationService(db)
        evaluation = service.generate_evaluation(submission.id)
        reviewed = service.manual_review(
            evaluation.id,
            ai_level=None,
            overall_score=evaluation.ai_overall_score + 18,
            explanation='主管评分明显高于 AI，需要 HR 审核。',
            dimension_updates=[],
        )
        assert reviewed is not None
        assert reviewed.status == 'pending_hr'
        assert reviewed.hr_decision == 'pending'
        assert reviewed.score_gap == 18.0

        returned = service.hr_review(
            evaluation.id,
            decision='returned',
            comment='请补充更多客观证据。',
            final_score=None,
        )
        assert returned is not None
        assert returned.status == 'returned'

        approved = service.hr_review(
            evaluation.id,
            decision='approved',
            comment='HR 同意，采用修正后的最终评分。',
            final_score=evaluation.ai_overall_score + 9,
        )
        assert approved is not None
        assert approved.status == 'confirmed'
        assert approved.hr_decision == 'approved'
        assert approved.overall_score == round(evaluation.ai_overall_score + 9, 2)
    finally:
        db.close()


