"""API auth tests for sharing endpoints (review fix #7).

Covers 401 (no auth), 403 (non-owner), correct context resolution via submission_id,
and atomic upload+sharing-request creation.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.sharing_request import SharingRequest
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'sharing-api-{uuid4().hex}.db').as_posix()
        uploads_path = (temp_root / f'sharing-uploads-{uuid4().hex}').as_posix()
        self.settings = Settings(
            allow_self_registration=True,
            database_url=f'sqlite+pysqlite:///{database_path}',
            storage_base_dir=uploads_path,
            deepseek_require_real_call_for_parsing=False,
            deepseek_api_key='your_deepseek_api_key',
        )
        load_model_modules()
        self.engine = create_db_engine(self.settings)
        init_database(self.engine)
        self.session_factory = create_session_factory(self.settings)

    def override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()


def build_client() -> tuple[TestClient, ApiDatabaseContext]:
    context = ApiDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app), context


def register_admin(client: TestClient, email: str = 'admin@example.com') -> str:
    response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': 'admin'},
    )
    assert response.status_code == 201, response.text
    return response.json()['tokens']['access_token']


def seed_two_employees_with_files(context: ApiDatabaseContext) -> dict:
    """Create two employees with submissions, files, and bind them to users."""
    db = context.session_factory()
    try:
        cycle = EvaluationCycle(
            name='2026 Review', review_period='2026',
            budget_amount='5000.00', status='published',
        )
        db.add(cycle)
        db.commit()
        db.refresh(cycle)

        emp1 = Employee(
            employee_no=f'EMP-SA-{uuid4().hex[:6]}', name='Owner User',
            department='Engineering', job_family='Platform', job_level='P6', status='active',
        )
        emp2 = Employee(
            employee_no=f'EMP-SA-{uuid4().hex[:6]}', name='Requester User',
            department='Engineering', job_family='Platform', job_level='P6', status='active',
        )
        db.add_all([emp1, emp2])
        db.commit()
        db.refresh(emp1)
        db.refresh(emp2)

        sub1 = EmployeeSubmission(employee_id=emp1.id, cycle_id=cycle.id, status='collecting')
        sub2 = EmployeeSubmission(employee_id=emp2.id, cycle_id=cycle.id, status='collecting')
        db.add_all([sub1, sub2])
        db.commit()
        db.refresh(sub1)
        db.refresh(sub2)

        file1 = UploadedFile(
            submission_id=sub1.id, file_name='orig.pptx', file_type='pptx',
            storage_key=f'uploads/{uuid4().hex}', content_hash='api_share_hash',
        )
        db.add(file1)
        db.commit()
        db.refresh(file1)

        return {
            'cycle_id': cycle.id,
            'emp1_id': emp1.id, 'sub1_id': sub1.id, 'file1_id': file1.id,
            'emp2_id': emp2.id, 'sub2_id': sub2.id,
        }
    finally:
        db.close()


def bind_user_to_employee(context: ApiDatabaseContext, user_email: str, employee_id: str) -> None:
    db = context.session_factory()
    try:
        user = db.scalars(select(User).where(User.email == user_email)).first()
        assert user is not None
        user.employee_id = employee_id
        db.add(user)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 401 tests
# ---------------------------------------------------------------------------

def test_check_duplicate_requires_auth() -> None:
    client, _ctx = build_client()
    with client:
        response = client.post(
            '/api/v1/files/check-duplicate',
            json={'content_hash': 'abc', 'submission_id': 'nonexistent'},
        )
        assert response.status_code == 401


def test_list_sharing_requests_requires_auth() -> None:
    client, _ctx = build_client()
    with client:
        response = client.get('/api/v1/sharing-requests')
        assert response.status_code == 401


def test_pending_count_requires_auth() -> None:
    client, _ctx = build_client()
    with client:
        response = client.get('/api/v1/sharing-requests/pending-count')
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# check-duplicate endpoint
# ---------------------------------------------------------------------------

def test_check_duplicate_returns_false_for_new_hash() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)

        response = client.post(
            '/api/v1/files/check-duplicate',
            headers=headers,
            json={'content_hash': 'unseen_hash_xyz', 'submission_id': seed['sub2_id']},
        )
        assert response.status_code == 200
        assert response.json()['is_duplicate'] is False


def test_check_duplicate_returns_true_for_existing_hash() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)

        response = client.post(
            '/api/v1/files/check-duplicate',
            headers=headers,
            json={'content_hash': 'api_share_hash', 'submission_id': seed['sub2_id']},
        )
        assert response.status_code == 200
        body = response.json()
        assert body['is_duplicate'] is True
        assert body['original_file_id'] == seed['file1_id']
        assert body['original_submission_id'] == seed['sub1_id']
        assert body['uploader_name'] == 'Owner User'


def test_check_duplicate_excludes_target_employee_own_files() -> None:
    """When checking for sub1 (owner), the owner's own file should be excluded."""
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)

        response = client.post(
            '/api/v1/files/check-duplicate',
            headers=headers,
            json={'content_hash': 'api_share_hash', 'submission_id': seed['sub1_id']},
        )
        assert response.status_code == 200
        # owner's own file is excluded — should NOT be a duplicate
        assert response.json()['is_duplicate'] is False


# ---------------------------------------------------------------------------
# sharing-requests list + pending-count (with bound user)
# ---------------------------------------------------------------------------

def test_list_sharing_requests_returns_list_for_bound_user() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        bind_user_to_employee(context, 'admin@example.com', seed['emp1_id'])

        response = client.get('/api/v1/sharing-requests?direction=incoming', headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert 'items' in body
        assert 'total' in body
        assert body['total'] == 0  # no requests yet


def test_pending_count_returns_zero_initially() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        bind_user_to_employee(context, 'admin@example.com', seed['emp1_id'])

        response = client.get('/api/v1/sharing-requests/pending-count', headers=headers)
        assert response.status_code == 200
        assert response.json()['count'] == 0


# ---------------------------------------------------------------------------
# approve/reject 403 (non-owner)
# ---------------------------------------------------------------------------

def _seed_pending_request(context: ApiDatabaseContext, seed: dict) -> str:
    """Create a pending sharing request directly in DB. Returns request_id."""
    db = context.session_factory()
    try:
        file2 = UploadedFile(
            submission_id=seed['sub2_id'], file_name='dup.pptx', file_type='pptx',
            storage_key=f'uploads/{uuid4().hex}', content_hash='api_share_hash',
        )
        db.add(file2)
        db.commit()
        db.refresh(file2)

        sr = SharingRequest(
            requester_file_id=file2.id,
            original_file_id=seed['file1_id'],
            requester_submission_id=seed['sub2_id'],
            original_submission_id=seed['sub1_id'],
            requester_content_hash='api_share_hash',
            requester_file_name_snapshot='dup.pptx',
            status='pending',
            proposed_pct=50.0,
        )
        db.add(sr)
        db.commit()
        db.refresh(sr)
        return sr.id
    finally:
        db.close()


def test_approve_returns_403_for_non_owner() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        # Bind admin user to emp2 (the REQUESTER, not the owner)
        bind_user_to_employee(context, 'admin@example.com', seed['emp2_id'])
        request_id = _seed_pending_request(context, seed)

        response = client.post(
            f'/api/v1/sharing-requests/{request_id}/approve',
            headers=headers,
            json={'final_pct': 50},
        )
        assert response.status_code == 403


def test_revoke_rejection_endpoint_is_blocked() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        bind_user_to_employee(context, 'admin@example.com', seed['emp1_id'])
        request_id = _seed_pending_request(context, seed)

        db = context.session_factory()
        try:
            sr = db.get(SharingRequest, request_id)
            assert sr is not None
            sr.status = 'rejected'
            db.add(sr)
            db.commit()
        finally:
            db.close()

        response = client.post(
            f'/api/v1/sharing-requests/{request_id}/revoke-rejection',
            headers=headers,
        )
        assert response.status_code in {400, 404}


def test_reject_returns_403_for_non_owner() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        # Bind admin user to emp2 (the REQUESTER, not the owner)
        bind_user_to_employee(context, 'admin@example.com', seed['emp2_id'])
        request_id = _seed_pending_request(context, seed)

        response = client.post(
            f'/api/v1/sharing-requests/{request_id}/reject',
            headers=headers,
        )
        assert response.status_code == 403


def test_approve_succeeds_for_owner() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        bind_user_to_employee(context, 'admin@example.com', seed['emp1_id'])
        request_id = _seed_pending_request(context, seed)

        response = client.post(
            f'/api/v1/sharing-requests/{request_id}/approve',
            headers=headers,
            json={'final_pct': 60},
        )
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'approved'
        assert body['final_pct'] == 60.0


def test_sharing_history_uses_snapshot_when_requester_file_missing() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)
        bind_user_to_employee(context, 'admin@example.com', seed['emp1_id'])

        db = context.session_factory()
        try:
            file2 = UploadedFile(
                submission_id=seed['sub2_id'],
                file_name='dup_snapshot.pptx',
                file_type='pptx',
                storage_key=f'uploads/{uuid4().hex}',
                content_hash='api_share_hash',
            )
            db.add(file2)
            db.commit()
            db.refresh(file2)

            sr = SharingRequest(
                requester_file_id=None,
                original_file_id=seed['file1_id'],
                requester_submission_id=seed['sub2_id'],
                original_submission_id=seed['sub1_id'],
                requester_content_hash='api_share_hash',
                requester_file_name_snapshot='dup_snapshot.pptx',
                status='rejected',
                proposed_pct=50.0,
            )
            db.add(sr)
            db.commit()
        finally:
            db.close()

        response = client.get('/api/v1/sharing-requests?direction=incoming', headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body['total'] == 1
        item = body['items'][0]
        assert item['requester_file_id'] is None
        assert item['requester_name'] == 'Requester User'
        assert item['file_name'] == 'orig.pptx'
        assert item['status'] == 'rejected'


# ---------------------------------------------------------------------------
# upload with allow_duplicate+original_file_id — atomic
# ---------------------------------------------------------------------------

def test_upload_with_allow_duplicate_creates_file_and_sharing_request_atomically() -> None:
    client, context = build_client()
    with client:
        token = register_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed = seed_two_employees_with_files(context)

        response = client.post(
            f'/api/v1/submissions/{seed["sub2_id"]}/files'
            f'?allow_duplicate=true&original_file_id={seed["file1_id"]}',
            headers=headers,
            files=[('files', ('notes.md', b'# Same content', 'text/markdown'))],
        )
        assert response.status_code == 201, response.text
        items = response.json()['items']
        assert len(items) == 1

        # Verify SharingRequest was created in DB
        db = context.session_factory()
        try:
            sr = db.scalars(
                select(SharingRequest)
                .where(SharingRequest.original_file_id == seed['file1_id'])
            ).first()
            assert sr is not None
            assert sr.status == 'pending'
            assert sr.requester_submission_id == seed['sub2_id']
        finally:
            db.close()
