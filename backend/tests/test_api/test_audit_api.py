from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'audit-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            allow_self_registration=True,
            database_url=f'sqlite+pysqlite:///{database_path}',
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


def register_user(client: TestClient, *, email: str, role: str) -> str:
    response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': role},
    )
    assert response.status_code == 201
    return response.json()['user']['id']


def login_token(client: TestClient, *, email: str) -> str:
    response = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': 'Password123'},
    )
    assert response.status_code == 200
    return response.json()['access_token']


def seed_audit_rows(context: ApiDatabaseContext, *, operator_id: str) -> None:
    db = context.session_factory()
    try:
        db.add(AuditLog(
            operator_id=operator_id,
            action='approval_decided',
            target_type='approval_record',
            target_id=str(uuid4()),
            detail={'decision': 'approved'},
        ))
        db.add(AuditLog(
            operator_id=operator_id,
            action='manual_review',
            target_type='evaluation',
            target_id=str(uuid4()),
            detail={'score': 80},
        ))
        db.add(AuditLog(
            operator_id=operator_id,
            action='salary_updated',
            target_type='salary_recommendation',
            target_id=str(uuid4()),
            detail={'new_ratio': 0.12},
        ))
        db.commit()
    finally:
        db.close()


def test_audit_requires_admin() -> None:
    """AUDIT-02: GET /api/v1/audit/ must return 401 for unauthenticated requests
    and 403 for non-admin roles.

    FAILS because the endpoint does not exist yet (returns 404, not 401/403).
    """
    client, context = build_client()

    # Unauthenticated — expect 401
    response = client.get('/api/v1/audit/')
    assert response.status_code == 401, (
        f'Expected 401 for unauthenticated request, got {response.status_code}. '
        'Endpoint /api/v1/audit/ does not exist yet.'
    )

    # Manager role — expect 403
    register_user(client, email='manager@example.com', role='manager')
    manager_token = login_token(client, email='manager@example.com')
    response = client.get(
        '/api/v1/audit/',
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 403, (
        f'Expected 403 for manager role, got {response.status_code}. '
        'Endpoint /api/v1/audit/ does not exist yet.'
    )


def test_audit_query_filters() -> None:
    """AUDIT-02: GET /api/v1/audit/?action=approval_decided must return only
    rows matching that action filter.

    FAILS because the endpoint does not exist yet (returns 404).
    """
    client, context = build_client()

    admin_id = register_user(client, email='admin@example.com', role='admin')
    admin_token = login_token(client, email='admin@example.com')

    seed_audit_rows(context, operator_id=admin_id)

    response = client.get(
        '/api/v1/audit/?action=approval_decided',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert response.status_code == 200, (
        f'Expected 200 with action filter, got {response.status_code}. '
        'Endpoint /api/v1/audit/ does not exist yet.'
    )
    data = response.json()
    items = data.get('items', data) if isinstance(data, dict) else data
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]['action'] == 'approval_decided'


def test_audit_date_range() -> None:
    """AUDIT-02: GET /api/v1/audit/?from_dt=...&to_dt=... must return only rows
    within the specified date range.

    FAILS because the endpoint does not exist yet (returns 404).
    """
    client, context = build_client()

    admin_id = register_user(client, email='admin2@example.com', role='admin')
    admin_token = login_token(client, email='admin2@example.com')

    seed_audit_rows(context, operator_id=admin_id)

    now = datetime.now(timezone.utc)
    from_dt = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    to_dt = (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    response = client.get(
        f'/api/v1/audit/?from_dt={from_dt}&to_dt={to_dt}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert response.status_code == 200, (
        f'Expected 200 with date range filter, got {response.status_code}. '
        'Endpoint /api/v1/audit/ does not exist yet.'
    )
    data = response.json()
    items = data.get('items', data) if isinstance(data, dict) else data
    assert isinstance(items, list)
    assert len(items) == 3
