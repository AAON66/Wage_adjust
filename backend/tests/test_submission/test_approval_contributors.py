"""Tests for SUB-05: Approval record shows project contributors.

Validates that ApprovalService.load_project_contributors returns correct
contributor summaries for shared project files, including owner and contributors.
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
        explanation='Test evaluation for approval contributor display.',
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

    # Capture IDs before closing
    ids = {
        'admin_id': admin.id,
        'emp_owner_id': emp_owner.id,
        'emp_owner_name': emp_owner.name,
        'emp_contrib_id': emp_contrib.id,
        'emp_contrib_name': emp_contrib.name,
        'cycle_id': cycle.id,
        'sub_owner_id': sub_owner.id,
        'sub_contrib_id': sub_contrib.id,
        'file1_id': file1.id,
        'file1_name': file1.file_name,
        'contrib_id': contrib.id,
        'evaluation_id': evaluation.id,
        'recommendation_id': recommendation.id,
    }
    db.close()

    return ids


def test_approval_shows_contributors():
    """ApprovalService.load_project_contributors returns contributor list for shared files."""
    _settings, sf = _build_db()
    ids = _seed_approval_with_contributors(sf)

    db = sf()
    svc = ApprovalService(db)

    contributors = svc.load_project_contributors(ids['sub_owner_id'])
    db.close()

    assert len(contributors) > 0
    # Should have both owner and contributor entries
    assert len(contributors) == 2

    # Check file name matches
    for c in contributors:
        assert c.file_name == ids['file1_name']


def test_approval_shows_owner_in_contributors():
    """The file owner should appear in the contributors list with is_owner=True."""
    _settings, sf = _build_db()
    ids = _seed_approval_with_contributors(sf)

    db = sf()
    svc = ApprovalService(db)

    contributors = svc.load_project_contributors(ids['sub_owner_id'])
    db.close()

    owner_entries = [c for c in contributors if c.is_owner]
    assert len(owner_entries) == 1
    assert owner_entries[0].employee_id == ids['emp_owner_id']
    assert owner_entries[0].employee_name == ids['emp_owner_name']
    assert owner_entries[0].contribution_pct == pytest.approx(60.0, abs=0.01)

    contrib_entries = [c for c in contributors if not c.is_owner]
    assert len(contrib_entries) == 1
    assert contrib_entries[0].employee_id == ids['emp_contrib_id']
    assert contrib_entries[0].employee_name == ids['emp_contrib_name']
    assert contrib_entries[0].contribution_pct == pytest.approx(40.0, abs=0.01)
