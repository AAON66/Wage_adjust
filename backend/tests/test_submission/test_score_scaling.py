"""Tests for SUB-04: Score scaling based on contribution percentage.

Per D-08: effective_score = raw_score * (contribution_pct / 100)
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
from backend.app.models.evidence import EvidenceItem
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.services.evaluation_service import EvaluationService


def _build_db():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'scoring-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        deepseek_api_key='test_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def _seed_with_contributors(session_factory, owner_pct: float, contributor_pct: float):
    """Seed DB with owner file and one contributor."""
    db = session_factory()
    cycle = EvaluationCycle(
        name='2026 Review', review_period='2026',
        budget_amount='5000.00', status='published',
    )
    emp_owner = Employee(
        employee_no=f'EMP-S1-{uuid4().hex[:4]}', name='Owner',
        department='Engineering', job_family='Platform', job_level='P6', status='active',
    )
    emp_contrib = Employee(
        employee_no=f'EMP-S2-{uuid4().hex[:4]}', name='Contributor',
        department='Engineering', job_family='Platform', job_level='P5', status='active',
    )
    db.add_all([cycle, emp_owner, emp_contrib])
    db.commit()
    for obj in [cycle, emp_owner, emp_contrib]:
        db.refresh(obj)

    sub_owner = EmployeeSubmission(employee_id=emp_owner.id, cycle_id=cycle.id, status='collecting')
    sub_contrib = EmployeeSubmission(employee_id=emp_contrib.id, cycle_id=cycle.id, status='collecting')
    db.add_all([sub_owner, sub_contrib])
    db.commit()
    db.refresh(sub_owner)
    db.refresh(sub_contrib)

    file1 = UploadedFile(
        submission_id=sub_owner.id,
        file_name='joint_project.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='score_hash_001',
        owner_contribution_pct=owner_pct,
    )
    db.add(file1)
    db.commit()
    db.refresh(file1)

    contrib = ProjectContributor(
        uploaded_file_id=file1.id,
        submission_id=sub_contrib.id,
        contribution_pct=contributor_pct,
        status='accepted',
    )
    db.add(contrib)
    db.commit()
    db.refresh(contrib)

    # Capture IDs before closing session to avoid detached instance errors
    ids = {
        'cycle_id': cycle.id,
        'emp_owner_id': emp_owner.id,
        'emp_contrib_id': emp_contrib.id,
        'sub_owner_id': sub_owner.id,
        'sub_contrib_id': sub_contrib.id,
        'file1_id': file1.id,
        'contrib_id': contrib.id,
    }
    db.close()

    return ids


def test_shared_project_score_scaling():
    """80 score * 60% contribution = 48 effective score (per D-08)."""
    raw_score = 80.0
    effective = EvaluationService.compute_effective_score(
        raw_score=raw_score,
        contribution_pct=60.0,
    )
    assert effective == pytest.approx(48.0, abs=0.01)


def test_owner_score_scaling():
    """Owner effective score = raw_score * (owner_pct / 100)."""
    raw_score = 80.0
    effective = EvaluationService.compute_effective_score(
        raw_score=raw_score,
        contribution_pct=40.0,
    )
    assert effective == pytest.approx(32.0, abs=0.01)


def test_no_contributors_full_score():
    """When there are no contributors, owner gets full 100% score."""
    raw_score = 90.0
    effective = EvaluationService.compute_effective_score(
        raw_score=raw_score,
        contribution_pct=100.0,
    )
    assert effective == pytest.approx(90.0, abs=0.01)


def test_evidence_scaling_with_contribution():
    """Evidence items are scaled by contribution percentage in _load_evidence_for_evaluation."""
    _settings, sf = _build_db()
    ids = _seed_with_contributors(sf, owner_pct=40.0, contributor_pct=60.0)

    db = sf()
    # Add evidence linked to the shared file for the owner's submission
    evidence = EvidenceItem(
        submission_id=ids['sub_owner_id'],
        source_type='ppt',
        title='Joint Project Slides',
        content='Evidence content about the joint project',
        confidence_score=0.9,
        metadata_json={'file_id': ids['file1_id']},
    )
    db.add(evidence)
    db.commit()

    # Create service for the owner's submission
    svc = EvaluationService(db, _settings)
    submission = db.get(EmployeeSubmission, ids['sub_owner_id'])
    all_evidence = svc._load_evidence_for_evaluation(submission)

    assert len(all_evidence) == 1
    # Owner has 40% contribution, so confidence_score should be scaled
    assert all_evidence[0].confidence_score == pytest.approx(0.9 * 0.4, abs=0.001)
    db.close()


def test_contributor_evidence_scaling():
    """Contributor evidence is loaded from original file and scaled by contribution_pct."""
    _settings, sf = _build_db()
    ids = _seed_with_contributors(sf, owner_pct=40.0, contributor_pct=60.0)

    db = sf()
    # Add evidence linked to the shared file for the owner's submission
    evidence = EvidenceItem(
        submission_id=ids['sub_owner_id'],
        source_type='ppt',
        title='Joint Project Slides',
        content='Evidence content about the joint project',
        confidence_score=0.8,
        metadata_json={'file_id': ids['file1_id']},
    )
    db.add(evidence)
    db.commit()

    # Create service for the contributor's submission
    svc = EvaluationService(db, _settings)
    submission = db.get(EmployeeSubmission, ids['sub_contrib_id'])
    all_evidence = svc._load_evidence_for_evaluation(submission)

    assert len(all_evidence) >= 1
    # Contributor has 60% contribution, evidence confidence_score should be scaled
    scaled_item = all_evidence[0]
    assert scaled_item.confidence_score == pytest.approx(0.8 * 0.6, abs=0.001)
    metadata = scaled_item.metadata_json
    assert metadata.get('is_shared') is True
    assert metadata.get('contribution_pct') == pytest.approx(60.0, abs=0.01)
    db.close()
