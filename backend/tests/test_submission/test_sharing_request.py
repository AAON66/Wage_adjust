"""Tests for SharingService: file sharing workflow with D-09..D-19 semantics.

Covers: create_request, approve, reject, list with lazy expiry,
get_pending_count with lazy expiry, D-15/D-19 semantics, hash-only
dedup with deterministic oldest-first ordering.
"""
from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evidence import EvidenceItem
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.sharing_request import SharingRequest
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.utils.helpers import utc_now


def _build_db():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'sharing-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        storage_base_dir=(temp_root / f'sharing-uploads-{uuid4().hex}').as_posix(),
        deepseek_api_key='test_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def _seed(session_factory, *, employee_count: int = 2):
    """Seed DB with employees, cycle, submissions, and files. Returns IDs."""
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
            employee_no=f'EMP-SR-{uuid4().hex[:6]}',
            name=f'Share User {i}',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        sub = EmployeeSubmission(employee_id=emp.id, cycle_id=cycle_id, status='collecting')
        db.add(sub)
        db.commit()
        db.refresh(sub)

        # Create a file for each employee
        f = UploadedFile(
            submission_id=sub.id,
            file_name=f'project_{i}.pptx',
            file_type='pptx',
            storage_key=f'uploads/{uuid4().hex}',
            content_hash='shared_hash_001',
        )
        db.add(f)
        db.commit()
        db.refresh(f)

        results.append({
            'emp_id': emp.id,
            'sub_id': sub.id,
            'file_id': f.id,
        })

    db.close()
    return cycle_id, results


def test_create_request_pending():
    """SharingService.create_request() creates a SharingRequest with status='pending', proposed_pct=50.0."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    sr = svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    assert sr.status == 'pending'
    assert sr.proposed_pct == 50.0
    assert sr.id is not None
    db.close()


def test_create_request_d15_blocks_duplicate():
    """D-15: block if non-expired request exists for same content_hash + original uploader."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()

    # Create a new file with same hash for the re-request attempt
    new_file = UploadedFile(
        submission_id=requester['sub_id'],
        file_name='project_dup.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='shared_hash_001',
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    with pytest.raises(ValueError, match='已存在共享申请'):
        svc.create_request(
            requester_file_id=new_file.id,
            original_file_id=original['file_id'],
            requester_submission_id=requester['sub_id'],
            original_submission_id=original['sub_id'],
        )
    db.close()


def test_create_request_d19_allows_after_expired():
    """D-19: expired status is excluded — allows new request after expiry."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    sr = svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    # Manually expire the request
    sr.status = 'expired'
    sr.resolved_at = utc_now()
    db.commit()

    # New file with same hash
    new_file = UploadedFile(
        submission_id=requester['sub_id'],
        file_name='project_retry.pptx',
        file_type='pptx',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='shared_hash_001',
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # Should NOT raise because the prior request is expired
    sr2 = svc.create_request(
        requester_file_id=new_file.id,
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    assert sr2.status == 'pending'
    db.close()


def test_approve_request():
    """Approve sets status='approved', final_pct, resolved_at, creates ProjectContributor, updates owner_contribution_pct."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    sr = svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()

    result = svc.approve_request(sr.id, approver_employee_id=original['emp_id'], final_pct=70.0)
    db.commit()

    assert result.status == 'approved'
    assert result.final_pct == 70.0
    assert result.resolved_at is not None

    # Check ProjectContributor was created
    from sqlalchemy import select
    pc = db.scalars(
        select(ProjectContributor).where(
            ProjectContributor.uploaded_file_id == original['file_id'],
            ProjectContributor.submission_id == requester['sub_id'],
        )
    ).first()
    assert pc is not None
    assert pc.contribution_pct == 70.0

    # Check owner_contribution_pct was updated
    orig_file = db.get(UploadedFile, original['file_id'])
    assert orig_file.owner_contribution_pct == 30.0
    db.close()


def test_approve_contribution_pct_calculation():
    """Approve with final_pct=70 sets requester contribution to 70%, owner to 30%."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    sr = svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()

    svc.approve_request(sr.id, approver_employee_id=original['emp_id'], final_pct=70.0)
    db.commit()

    orig_file = db.get(UploadedFile, original['file_id'])
    assert orig_file.owner_contribution_pct == 30.0  # 100 - 70

    from sqlalchemy import select
    pc = db.scalars(
        select(ProjectContributor).where(
            ProjectContributor.uploaded_file_id == original['file_id'],
        )
    ).first()
    assert pc.contribution_pct == 70.0
    db.close()


def test_reject_request():
    """Reject sets status='rejected', resolved_at."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    sr = svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()

    result = svc.reject_request(sr.id, rejector_employee_id=original['emp_id'])
    assert result.status == 'rejected'
    assert result.resolved_at is not None
    db.close()


def test_reject_history_survives_requester_file_delete_and_still_lists():
    """D-03: deleting requester copy must not erase incoming/outgoing history."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()
    sharing_svc.reject_request(sr.id, rejector_employee_id=original['emp_id'])
    db.commit()

    FileService(db, _settings).delete_file(requester['file_id'])

    preserved = db.get(SharingRequest, sr.id)
    assert preserved is not None
    assert preserved.requester_file_id is None

    outgoing = sharing_svc.list_requests(employee_id=requester['emp_id'], direction='outgoing')
    incoming = sharing_svc.list_requests(employee_id=original['emp_id'], direction='incoming')
    assert [item.id for item in outgoing] == [sr.id]
    assert [item.id for item in incoming] == [sr.id]
    db.close()


def test_create_request_persists_duplicate_guard_snapshot_fields():
    """D-07: persisted snapshot fields must survive requester file cleanup."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService

    sr = SharingService(db, _settings).create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )

    assert sr.requester_content_hash == 'shared_hash_001'
    assert sr.requester_file_name_snapshot == 'project_0.pptx'
    db.close()


def test_reject_duplicate_check_uses_persisted_hash_after_requester_file_delete():
    """D-07: rejected requests still block retries after requester copy cleanup."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()
    sharing_svc.reject_request(sr.id, rejector_employee_id=original['emp_id'])
    db.commit()

    FileService(db, _settings).delete_file(requester['file_id'])

    with pytest.raises(ValueError, match='已存在共享申请'):
        sharing_svc.check_can_create_request(
            submission_id=requester['sub_id'],
            original_submission_id=original['sub_id'],
            content_hash_hint='shared_hash_001',
        )
    db.close()


def test_expired_history_survives_requester_file_delete_and_allows_retry():
    """D-03/D-08: expired rows remain in history and do not block retries."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    sr.status = 'expired'
    sr.resolved_at = utc_now()
    db.commit()

    FileService(db, _settings).delete_file(requester['file_id'])

    preserved = db.get(SharingRequest, sr.id)
    assert preserved is not None
    assert preserved.status == 'expired'

    sharing_svc.check_can_create_request(
        submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
        content_hash_hint='shared_hash_001',
    )
    db.close()


def test_revoke_rejection_is_blocked_for_rejected_request():
    """D-07: rejected is terminal and cannot return to pending."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    db.commit()
    sharing_svc.reject_request(sr.id, rejector_employee_id=original['emp_id'])
    db.commit()

    with pytest.raises(ValueError, match='终态|rejected|撤销'):
        sharing_svc.revoke_rejection(sr.id, revoker_employee_id=original['emp_id'])
    db.close()


def test_reject_cleanup_removes_requester_copy_evidence_and_storage_but_keeps_original():
    """D-01/D-02: reject cleanup deletes only the requester copy and its derived data."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    requester_file = db.get(UploadedFile, requester['file_id'])
    original_file = db.get(UploadedFile, original['file_id'])
    assert requester_file is not None
    assert original_file is not None

    requester_file.storage_key = f'{requester["sub_id"]}/reject-copy.txt'
    original_file.storage_key = f'{original["sub_id"]}/original-copy.txt'
    requester_path = Path(_settings.storage_base_dir) / requester_file.storage_key
    original_path = Path(_settings.storage_base_dir) / original_file.storage_key
    requester_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.parent.mkdir(parents=True, exist_ok=True)
    requester_path.write_text('requester copy', encoding='utf-8')
    original_path.write_text('original copy', encoding='utf-8')

    evidence = EvidenceItem(
        submission_id=requester['sub_id'],
        source_type='file',
        title='Shared copy evidence',
        content='evidence',
        confidence_score=0.9,
        metadata_json={'file_id': requester['file_id']},
    )
    db.add(evidence)
    db.commit()

    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    request_id = sr.id
    db.commit()

    result = sharing_svc.reject_request(request_id, rejector_employee_id=original['emp_id'])

    assert result.status == 'rejected'
    assert result.requester_file_id is None
    assert db.get(UploadedFile, requester['file_id']) is None
    assert db.get(UploadedFile, original['file_id']) is not None
    assert not requester_path.exists()
    assert original_path.exists()
    remaining_evidence = db.query(EvidenceItem).filter(EvidenceItem.submission_id == requester['sub_id']).all()
    assert remaining_evidence == []
    preserved = db.get(SharingRequest, request_id)
    assert preserved is not None
    assert preserved.requester_file_id is None
    db.close()


def test_reject_cleanup_rolls_back_when_file_delete_fails(monkeypatch: pytest.MonkeyPatch):
    """T-21-04: reject cleanup must stay atomic if file deletion fails."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    from backend.app.services.sharing_service import SharingService

    sharing_svc = SharingService(db, _settings)
    sr = sharing_svc.create_request(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
    )
    request_id = sr.id
    requester_file_id = requester['file_id']
    db.commit()

    def _boom(self, file_id: str) -> str:
        raise RuntimeError('boom')

    monkeypatch.setattr(FileService, 'delete_file_without_commit', _boom)

    with pytest.raises(RuntimeError, match='boom'):
        sharing_svc.reject_request(request_id, rejector_employee_id=original['emp_id'])
    db.rollback()
    db.close()

    verify_db = sf()
    try:
        refreshed = verify_db.get(SharingRequest, request_id)
        assert refreshed is not None
        assert refreshed.status == 'pending'
        assert refreshed.requester_file_id == requester_file_id
        assert verify_db.get(UploadedFile, requester_file_id) is not None
    finally:
        verify_db.close()


def test_list_requests_marks_stale_as_expired():
    """list_requests() marks stale pending requests as expired before returning (D-17)."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    # Create a request and manually set its created_at to 73 hours ago
    sr = SharingRequest(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
        requester_content_hash='shared_hash_001',
        requester_file_name_snapshot='project_0.pptx',
        status='pending',
        created_at=utc_now() - timedelta(hours=73),
    )
    db.add(sr)
    db.commit()
    db.refresh(sr)
    sr_id = sr.id

    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    items = svc.list_requests(employee_id=original['emp_id'], direction='incoming')

    # The stale request should now be expired
    refreshed = db.get(SharingRequest, sr_id)
    assert refreshed.status == 'expired'
    db.close()


def test_get_pending_count_runs_lazy_expiry():
    """get_pending_count() also runs lazy expiry before counting (review #6)."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    # Create a stale request (73h ago)
    sr_stale = SharingRequest(
        requester_file_id=requester['file_id'],
        original_file_id=original['file_id'],
        requester_submission_id=requester['sub_id'],
        original_submission_id=original['sub_id'],
        requester_content_hash='shared_hash_001',
        requester_file_name_snapshot='project_0.pptx',
        status='pending',
        created_at=utc_now() - timedelta(hours=73),
    )
    db.add(sr_stale)
    db.commit()

    from backend.app.services.sharing_service import SharingService
    svc = SharingService(db, _settings)
    count = svc.get_pending_count(employee_id=original['emp_id'])
    # Should be 0 because the stale request should have been expired
    assert count == 0
    db.close()


def test_check_duplicate_hash_only_returns_oldest():
    """_check_duplicate returns oldest file by created_at when multiple matches exist (review #5)."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    # Create two files with same hash, different timestamps
    file_old = UploadedFile(
        submission_id=requester['sub_id'],
        file_name='old_file.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='determ_hash',
    )
    db.add(file_old)
    db.commit()
    db.refresh(file_old)
    old_id = file_old.id

    time.sleep(0.05)
    file_new = UploadedFile(
        submission_id=requester['sub_id'],
        file_name='new_file.pdf',
        file_type='pdf',
        storage_key=f'uploads/{uuid4().hex}',
        content_hash='determ_hash',
    )
    db.add(file_new)
    db.commit()

    from backend.app.services.file_service import FileService
    svc = FileService(db)
    result = svc._check_duplicate('determ_hash')
    assert result is not None
    assert result.id == old_id
    db.close()


def test_check_duplicate_different_hash_returns_none():
    """_check_duplicate with different hash returns None."""
    _settings, sf = _build_db()
    _cycle_id, [requester, original] = _seed(sf)

    db = sf()
    from backend.app.services.file_service import FileService
    svc = FileService(db)
    result = svc._check_duplicate('nonexistent_hash')
    assert result is None
    db.close()
