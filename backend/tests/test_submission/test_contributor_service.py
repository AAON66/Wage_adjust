"""Tests for SUB-02 (contributor CRUD), SUB-03 (shared file visibility),
and D-06 (dispute mechanism).
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile


def _build_db():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'contrib-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        deepseek_api_key='test_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def _seed_two_employees(session_factory):
    """Seed DB with 2 employees, 1 cycle, 2 submissions, 1 uploaded file on emp1's submission.
    Returns string IDs to avoid detached instance errors.
    """
    db = session_factory()
    cycle = EvaluationCycle(
        name='2026 Review', review_period='2026',
        budget_amount='5000.00', status='published',
    )
    emp1 = Employee(
        employee_no=f'EMP-C1-{uuid4().hex[:4]}', name='Owner',
        department='Engineering', job_family='Platform', job_level='P6', status='active',
    )
    emp2 = Employee(
        employee_no=f'EMP-C2-{uuid4().hex[:4]}', name='Contributor',
        department='Engineering', job_family='Platform', job_level='P5', status='active',
    )
    db.add_all([cycle, emp1, emp2])
    db.commit()
    for obj in [cycle, emp1, emp2]:
        db.refresh(obj)

    cycle_id = cycle.id
    emp1_id = emp1.id
    emp2_id = emp2.id

    sub1 = EmployeeSubmission(employee_id=emp1_id, cycle_id=cycle_id, status='collecting')
    sub2 = EmployeeSubmission(employee_id=emp2_id, cycle_id=cycle_id, status='collecting')
    db.add_all([sub1, sub2])
    db.commit()
    db.refresh(sub1)
    db.refresh(sub2)

    sub1_id = sub1.id
    sub2_id = sub2.id

    file1 = UploadedFile(
        submission_id=sub1_id,
        file_name='team_project.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='team_hash_001',
    )
    db.add(file1)
    db.commit()
    db.refresh(file1)
    file1_id = file1.id
    db.close()
    return cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id


# ---------------------------------------------------------------------------
# SUB-02: Contributor CRUD and validation
# ---------------------------------------------------------------------------

def test_contributors_saved():
    """Uploading with contributor list should create project_contributor rows."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    svc = FileService(db)
    svc.add_contributors(
        uploaded_file_id=file1_id,
        contributors=[{'employee_id': emp2_id, 'contribution_pct': 40.0}],
    )

    contribs = db.query(ProjectContributor).filter_by(uploaded_file_id=file1_id).all()
    assert len(contribs) == 1
    assert contribs[0].submission_id == sub2_id
    assert contribs[0].contribution_pct == 40.0

    # owner_contribution_pct should be auto-computed
    file_obj = db.query(UploadedFile).get(file1_id)
    assert file_obj.owner_contribution_pct == 60.0
    db.close()


def test_contributor_pct_sum_exceeds_100_rejected():
    """If sum of contributor pcts >= 100, should be rejected."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)):
        svc.add_contributors(
            uploaded_file_id=file1_id,
            contributors=[{'employee_id': emp2_id, 'contribution_pct': 100.0}],
        )
    db.close()


def test_contributor_pct_zero_rejected():
    """0% contribution should be rejected."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)):
        svc.add_contributors(
            uploaded_file_id=file1_id,
            contributors=[{'employee_id': emp2_id, 'contribution_pct': 0.0}],
        )
    db.close()


def test_owner_pct_computed():
    """owner_contribution_pct = 100 - sum(contributor_pcts), auto-computed."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    svc = FileService(db)
    svc.add_contributors(
        uploaded_file_id=file1_id,
        contributors=[{'employee_id': emp2_id, 'contribution_pct': 30.0}],
    )

    file_obj = db.query(UploadedFile).get(file1_id)
    assert file_obj.owner_contribution_pct == 70.0
    db.close()


def test_contribution_locked_after_evaluation():
    """After evaluation is submitted, contribution percentages cannot be modified."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    # Set submission status to evaluated
    db = sf()
    sub1_obj = db.query(EmployeeSubmission).get(sub1_id)
    sub1_obj.status = 'evaluated'
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)) as exc_info:
        svc.add_contributors(
            uploaded_file_id=file1_id,
            contributors=[{'employee_id': emp2_id, 'contribution_pct': 50.0}],
        )
    assert 'locked' in str(exc_info.value).lower() or 'evaluated' in str(exc_info.value).lower()
    db.close()


# ---------------------------------------------------------------------------
# D-06: Dispute mechanism
# ---------------------------------------------------------------------------

def test_dispute_changes_status():
    """POST dispute endpoint should change contributor status from accepted to disputed."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    contrib = ProjectContributor(
        uploaded_file_id=file1_id,
        submission_id=sub2_id,
        contribution_pct=40.0,
        status='accepted',
    )
    db.add(contrib)
    db.commit()
    db.refresh(contrib)
    contrib_id = contrib.id

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    svc.dispute_contribution(contributor_id=contrib_id, disputant_id=emp2_id)

    updated = db.query(ProjectContributor).get(contrib_id)
    assert updated.status == 'disputed'
    db.close()


def test_dispute_resolve_all_confirm():
    """All members confirming should resolve the dispute (status -> resolved)."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    contrib = ProjectContributor(
        uploaded_file_id=file1_id,
        submission_id=sub2_id,
        contribution_pct=40.0,
        status='disputed',
    )
    db.add(contrib)
    db.commit()
    db.refresh(contrib)
    contrib_id = contrib.id

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    # Both owner and contributor confirm
    svc.confirm_contribution(contributor_id=contrib_id, confirmer_id=emp1_id)
    svc.confirm_contribution(contributor_id=contrib_id, confirmer_id=emp2_id)

    resolved = db.query(ProjectContributor).get(contrib_id)
    assert resolved.status == 'resolved'
    db.close()


def test_dispute_resolve_manager_override():
    """Manager override should directly resolve a disputed contribution."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    contrib = ProjectContributor(
        uploaded_file_id=file1_id,
        submission_id=sub2_id,
        contribution_pct=40.0,
        status='disputed',
    )
    db.add(contrib)
    db.commit()
    db.refresh(contrib)
    contrib_id = contrib.id

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    svc.resolve_dispute_manager(contributor_id=contrib_id, manager_id='manager-001')

    resolved = db.query(ProjectContributor).get(contrib_id)
    assert resolved.status == 'resolved'
    db.close()


# ---------------------------------------------------------------------------
# SUB-03: Shared file visibility
# ---------------------------------------------------------------------------

def test_contributor_sees_shared_file():
    """Contributor should see the shared project file in their list_files result."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    contrib = ProjectContributor(
        uploaded_file_id=file1_id,
        submission_id=sub2_id,
        contribution_pct=40.0,
        status='accepted',
    )
    db.add(contrib)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    files = svc.list_files(submission_id=sub2_id, include_shared=True)
    shared_ids = [f.id for f in files]
    assert file1_id in shared_ids
    db.close()


def test_contributor_can_upload_supplementary():
    """Contributor should be able to upload supplementary material to their own submission."""
    _settings, sf = _build_db()
    cycle_id, emp1_id, emp2_id, sub1_id, sub2_id, file1_id = _seed_two_employees(sf)

    db = sf()
    contrib = ProjectContributor(
        uploaded_file_id=file1_id,
        submission_id=sub2_id,
        contribution_pct=40.0,
        status='accepted',
    )
    db.add(contrib)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    supplementary = svc.upload_file(
        submission_id=sub2_id,
        file_name='my_contribution_notes.pdf',
        file_type='pdf',
        content=b'supplementary content',
        content_hash='supplementary_hash_001',
    )
    assert supplementary.submission_id == sub2_id
    assert supplementary.file_name == 'my_contribution_notes.pdf'
    db.close()
