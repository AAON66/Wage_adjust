"""Tests for SUB-01: Document deduplication based on content_hash.

Per D-01 (refactored): deduplication is GLOBAL, hash-only (no filename matching).
Per D-02: dedup is cross-employee (global).
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
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile


def _build_db():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'dedup-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        deepseek_api_key='test_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def _seed(session_factory, *, employee_count: int = 1):
    """Seed DB with employee(s), cycle, and submission(s). Returns string IDs."""
    db = session_factory()
    cycle = EvaluationCycle(
        name='2026 Review', review_period='2026',
        budget_amount='5000.00', status='published',
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    cycle_id = cycle.id

    results = []
    for i in range(employee_count):
        emp = Employee(
            employee_no=f'EMP-DD-{uuid4().hex[:6]}',
            name=f'Dedup User {i}',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        emp_id = emp.id

        sub = EmployeeSubmission(employee_id=emp_id, cycle_id=cycle_id, status='collecting')
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sub_id = sub.id
        results.append((emp_id, sub_id))

    db.close()
    return cycle_id, results


def test_duplicate_upload_rejected():
    """Same content_hash should be rejected (D-01 hash-only dedup)."""
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    file1 = UploadedFile(
        submission_id=sub_id,
        file_name='project_report.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='abc123def456',
    )
    db.add(file1)
    db.commit()
    db.refresh(file1)

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)) as exc_info:
        svc.check_duplicate(content_hash='abc123def456')
    assert 'duplicate' in str(exc_info.value).lower() or 'existing' in str(exc_info.value).lower()
    db.close()


def test_duplicate_different_employee_rejected():
    """Different employee uploading same content_hash should also be rejected (D-02 global dedup)."""
    _settings, sf = _build_db()
    cycle_id, [(emp1_id, sub1_id), (emp2_id, sub2_id)] = _seed(sf, employee_count=2)

    db = sf()
    file1 = UploadedFile(
        submission_id=sub1_id,
        file_name='shared_project.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='global_hash_001',
    )
    db.add(file1)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)) as exc_info:
        svc.check_duplicate(content_hash='global_hash_001')
    assert 'duplicate' in str(exc_info.value).lower()
    db.close()


def test_same_hash_different_filename_is_duplicate():
    """D-01: same hash but different filename IS a duplicate (hash-only matching)."""
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    file1 = UploadedFile(
        submission_id=sub_id,
        file_name='original_name.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='hash_for_d01_test',
    )
    db.add(file1)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    # Same hash, different filename should still be a duplicate
    result = svc._check_duplicate('hash_for_d01_test')
    assert result is not None
    assert result.id == file1.id
    db.close()


def test_different_hash_same_filename_not_duplicate():
    """Different hash with same filename should NOT be a duplicate."""
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    file1 = UploadedFile(
        submission_id=sub_id,
        file_name='report.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='hash_a',
    )
    db.add(file1)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    result = svc._check_duplicate('hash_b')
    assert result is None
    db.close()


def test_replace_file_dedup_check():
    """Replacing a file should check dedup but exclude the current file being replaced."""
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    original = UploadedFile(
        submission_id=sub_id,
        file_name='doc.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='hash_original',
    )
    db.add(original)
    db.commit()
    db.refresh(original)
    original_id = original.id

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    # Replacing with same hash should NOT raise (exclude_file_id)
    svc.check_duplicate(
        content_hash='hash_original',
        exclude_file_id=original_id,
    )
    db.close()


def test_github_import_dedup_check():
    """GitHub import should also go through dedup check (hash-only)."""
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    existing = UploadedFile(
        submission_id=sub_id,
        file_name='main.py',
        file_type='code',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='github_hash_001',
    )
    db.add(existing)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    with pytest.raises((ValueError, Exception)):
        svc.check_duplicate(content_hash='github_hash_001')
    db.close()


def test_check_duplicate_returns_oldest():
    """_check_duplicate returns oldest file by created_at when multiple matches exist (review #5)."""
    import time
    _settings, sf = _build_db()
    cycle_id, [(emp_id, sub_id)] = _seed(sf)

    db = sf()
    # Create two files with same hash
    file1 = UploadedFile(
        submission_id=sub_id,
        file_name='first.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='multi_hash',
    )
    db.add(file1)
    db.commit()
    db.refresh(file1)
    file1_id = file1.id

    # Slight delay to ensure different created_at (SQLite datetime precision)
    time.sleep(0.05)
    file2 = UploadedFile(
        submission_id=sub_id,
        file_name='second.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='multi_hash',
    )
    db.add(file2)
    db.commit()
    db.refresh(file2)

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    result = svc._check_duplicate('multi_hash')
    assert result is not None
    assert result.id == file1_id, 'Should return the oldest file'
    db.close()
