"""RED test stubs for SUB-05: Approval record shows project contributors.

All tests are marked xfail because the approval-contributor integration is not yet implemented.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.models.user import User
from backend.app.services.approval_service import ApprovalService


def _build_db():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'approval-contrib-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        deepseek_api_key='test_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def _seed_approval_with_contributors(session_factory):
    """Seed DB with full approval chain + contributor on one uploaded file."""
    db = session_factory()

    admin = User(email='admin@example.com', hashed_password='x', role='admin')
    emp_owner = Employee(
        employee_no=f'EMP-A1-{uuid4().hex[:4]}', name='Owner Employee',
        department='Engineering', job_family='Platform', job_level='P6', status='active',
    )
    emp_contrib = Employee(
        employee_no=f'EMP-A2-{uuid4().hex[:4]}', name='Contributor Employee',
        department='Engineering', job_family='Platform', job_level='P5', status='active',
    )
    cycle = EvaluationCycle(
        name='2026 Review', review_period='2026',
        budget_amount='9000.00', status='published',
    )
    db.add_all([admin, emp_owner, emp_contrib, cycle])
    db.commit()
    for obj in [admin, emp_owner, emp_contrib, cycle]:
        db.refresh(obj)

    sub_owner = EmployeeSubmission(employee_id=emp_owner.id, cycle_id=cycle.id, status='evaluated')
    sub_contrib = EmployeeSubmission(employee_id=emp_contrib.id, cycle_id=cycle.id, status='collecting')
    db.add_all([sub_owner, sub_contrib])
    db.commit()
    db.refresh(sub_owner)
    db.refresh(sub_contrib)

    file1 = UploadedFile(
        submission_id=sub_owner.id,
        file_name='team_deliverable.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='approval_hash_001',
        owner_contribution_pct=60.0,
    )
    db.add(file1)
    db.commit()
    db.refresh(file1)

    contrib = ProjectContributor(
        uploaded_file_id=file1.id,
        submission_id=sub_contrib.id,
        contribution_pct=40.0,
        status='accepted',
    )
    db.add(contrib)
    db.commit()
    db.refresh(contrib)

    evaluation = AIEvaluation(
        submission_id=sub_owner.id,
        ai_level='Level 3',
        overall_score=75.0,
        status='confirmed',
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    recommendation = SalaryRecommendation(
        evaluation_id=evaluation.id,
        current_salary=10000.00,
        recommended_salary=11500.00,
        final_adjustment_ratio=0.15,
        status='pending',
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    db.close()

    return {
        'admin': admin,
        'emp_owner': emp_owner,
        'emp_contrib': emp_contrib,
        'cycle': cycle,
        'sub_owner': sub_owner,
        'sub_contrib': sub_contrib,
        'file1': file1,
        'contrib': contrib,
        'evaluation': evaluation,
        'recommendation': recommendation,
    }


@pytest.mark.xfail(reason='RED: SUB-05 approval contributors display not implemented')
def test_approval_shows_contributors():
    """ApprovalRecordRead should include project_contributors list."""
    _settings, sf = _build_db()
    data = _seed_approval_with_contributors(sf)

    svc = ApprovalService(session_factory=sf)

    # Submit for approval
    db = sf()
    svc.submit_for_approval(
        recommendation_id=data['recommendation'].id,
        steps=[{'step_name': 'hr_review', 'approver_id': data['admin'].id}],
        db=db,
    )
    db.close()

    # List approvals and check for contributors
    db = sf()
    approvals = svc.list_approvals(
        user_id=data['admin'].id,
        user_role='admin',
        db=db,
    )
    db.close()

    assert len(approvals) > 0
    record = approvals[0]
    # The record should have project_contributors field populated
    assert hasattr(record, 'project_contributors') or 'project_contributors' in record
    contributors = record.project_contributors if hasattr(record, 'project_contributors') else record['project_contributors']
    assert len(contributors) > 0


@pytest.mark.xfail(reason='RED: SUB-05 owner in contributors list not implemented')
def test_approval_shows_owner_in_contributors():
    """The file owner should also appear in the contributors list with is_owner=True."""
    _settings, sf = _build_db()
    data = _seed_approval_with_contributors(sf)

    svc = ApprovalService(session_factory=sf)

    db = sf()
    svc.submit_for_approval(
        recommendation_id=data['recommendation'].id,
        steps=[{'step_name': 'hr_review', 'approver_id': data['admin'].id}],
        db=db,
    )
    db.close()

    db = sf()
    approvals = svc.list_approvals(
        user_id=data['admin'].id,
        user_role='admin',
        db=db,
    )
    db.close()

    assert len(approvals) > 0
    record = approvals[0]
    contributors = record.project_contributors if hasattr(record, 'project_contributors') else record['project_contributors']
    owner_entries = [c for c in contributors if getattr(c, 'is_owner', False) or (isinstance(c, dict) and c.get('is_owner'))]
    assert len(owner_entries) >= 1
