"""Phase 34 Plan 03 Task 3：API 层端到端测试（≥ 11 cases）。

覆盖：
- GET /performance/records          admin 200 / hrbp 200 / employee 403 / manager 403
- POST /performance/records         admin 201 happy + 422 invalid grade
- GET /performance/tier-summary     admin 404（无快照）+ 200（有快照）
- POST /performance/recompute-tiers admin 200 happy + 409 busy + 500 failed
- GET /performance/available-years  admin 200（B-3）
- GET /performance/me/tier          404（保留位未实现）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.core.security import create_access_token
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot
from backend.app.models.user import User


@dataclass
class _UserCreds:
    id: str
    role: str


class _TestContext:
    """每个测试独立 SQLite + FastAPI app，自带 admin/hrbp/employee/manager token。"""

    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = (temp_root / f'perf-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            database_url=f'sqlite+pysqlite:///{db_path}',
            allow_self_registration=True,
        )
        self.engine = create_engine(
            self.settings.database_url,
            connect_args={'check_same_thread': False},
        )
        load_model_modules()
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False,
        )
        self.app = create_app(self.settings)
        self.app.dependency_overrides[get_db] = self._override_get_db
        self._db_path = db_path

    def _override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def db(self) -> Session:
        return self.session_factory()

    def make_user(self, *, role: str) -> _UserCreds:
        from backend.app.core.security import get_password_hash
        db = self.db()
        try:
            user = User(
                email=f'{role}-{uuid4().hex[:6]}@example.com',
                hashed_password=get_password_hash('Password123'),
                role=role,
                token_version=0,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return _UserCreds(id=user.id, role=user.role)
        finally:
            db.close()

    def auth_header(self, creds: _UserCreds) -> dict[str, str]:
        token = create_access_token(
            subject=creds.id, role=creds.role, settings=self.settings,
            token_version=0,
        )
        return {'Authorization': f'Bearer {token}'}

    def cleanup(self) -> None:
        self.engine.dispose()
        try:
            Path(self._db_path).unlink(missing_ok=True)
        except OSError:
            pass


@pytest.fixture()
def ctx():
    c = _TestContext()
    try:
        yield c
    finally:
        c.cleanup()


def _seed_employee(ctx: _TestContext, employee_no: str = 'E0001', department: str = 'Eng') -> str:
    db = ctx.db()
    try:
        emp = Employee(
            employee_no=employee_no, name='测试员工',
            department=department, job_family='engineering', job_level='P5',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return emp.id
    finally:
        db.close()


def _seed_snapshot(ctx: _TestContext, year: int = 2026) -> None:
    db = ctx.db()
    try:
        snap = PerformanceTierSnapshot(
            year=year,
            tiers_json={'e1': 1, 'e2': 2, 'e3': 3, 'e4': None},
            sample_size=3,
            insufficient_sample=False,
            distribution_warning=False,
            actual_distribution_json={'1': 0.33, '2': 0.34, '3': 0.33},
            skipped_invalid_grades=1,
        )
        db.add(snap)
        db.commit()
    finally:
        db.close()


def _seed_snapshot_for_current_year(
    ctx: _TestContext,
    *,
    tiers_json: dict[str, int | None],
    insufficient_sample: bool = False,
    sample_size: int = 100,
) -> PerformanceTierSnapshot:
    """插入当前年的档次快照，供 /performance/me/tier API 测试使用。"""
    current_year = datetime.now().year
    db = ctx.db()
    try:
        snap = PerformanceTierSnapshot(
            year=current_year,
            tiers_json=tiers_json,
            sample_size=sample_size,
            insufficient_sample=insufficient_sample,
            distribution_warning=False,
            actual_distribution_json={},
            skipped_invalid_grades=0,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap
    finally:
        db.close()


def _seed_employee_and_bind(
    ctx: _TestContext, user_creds: _UserCreds, employee_no: str,
) -> str:
    """创建 Employee 并绑定到指定用户。"""
    db = ctx.db()
    try:
        emp = Employee(
            employee_no=employee_no,
            name=f'Test {employee_no}',
            department='Eng',
            job_family='Backend',
            job_level='P6',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        user = db.get(User, user_creds.id)
        assert user is not None
        user.employee_id = emp.id
        db.add(user)
        db.commit()
        return emp.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /performance/records
# ---------------------------------------------------------------------------

def test_list_records_admin_returns_200(ctx):
    admin = ctx.make_user(role='admin')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/records',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in ('items', 'total', 'page', 'page_size', 'total_pages'):
        assert key in body


def test_list_records_hrbp_returns_200(ctx):
    hrbp = ctx.make_user(role='hrbp')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/records',
        headers=ctx.auth_header(hrbp),
    )
    assert resp.status_code == 200


def test_list_records_employee_returns_403(ctx):
    emp = ctx.make_user(role='employee')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/records',
        headers=ctx.auth_header(emp),
    )
    assert resp.status_code == 403


def test_list_records_manager_returns_403(ctx):
    mgr = ctx.make_user(role='manager')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/records',
        headers=ctx.auth_header(mgr),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /performance/records
# ---------------------------------------------------------------------------

def test_create_record_admin_returns_201(ctx):
    admin = ctx.make_user(role='admin')
    emp_id = _seed_employee(ctx, 'E0100', 'Engineering')
    client = TestClient(ctx.app)
    resp = client.post(
        '/api/v1/performance/records',
        headers=ctx.auth_header(admin),
        json={
            'employee_id': emp_id,
            'year': 2026,
            'grade': 'A',
            'source': 'manual',
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body['grade'] == 'A'
    assert body['department_snapshot'] == 'Engineering'


def test_create_record_invalid_grade_returns_422(ctx):
    admin = ctx.make_user(role='admin')
    emp_id = _seed_employee(ctx, 'E0101', 'Eng')
    client = TestClient(ctx.app)
    # Pydantic 422（grade 长度合法但 service 内 ValueError 转 422）
    resp = client.post(
        '/api/v1/performance/records',
        headers=ctx.auth_header(admin),
        json={
            'employee_id': emp_id,
            'year': 2026,
            'grade': 'F',
            'source': 'manual',
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /performance/tier-summary
# ---------------------------------------------------------------------------

def test_get_tier_summary_no_snapshot_returns_404(ctx):
    admin = ctx.make_user(role='admin')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/tier-summary?year=2030',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 404
    body = resp.json()
    # http_exception_handler 在 exc.detail 是 dict 时直接 return content（无 detail wrapper）
    assert body['error'] == 'no_snapshot'
    assert body['year'] == 2030


def test_get_tier_summary_with_snapshot_returns_200(ctx):
    admin = ctx.make_user(role='admin')
    _seed_snapshot(ctx, year=2026)
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/tier-summary?year=2026',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    # D-09 平铺 9 字段
    for key in (
        'year', 'computed_at', 'sample_size', 'insufficient_sample',
        'distribution_warning', 'tiers_count', 'actual_distribution',
        'skipped_invalid_grades',
    ):
        assert key in body
    assert body['tiers_count'].keys() >= {'1', '2', '3', 'none'}


# ---------------------------------------------------------------------------
# POST /performance/recompute-tiers
# ---------------------------------------------------------------------------

def test_recompute_tiers_admin_happy_returns_200(ctx):
    admin = ctx.make_user(role='admin')
    # 至少 50 条 perf records 才不会 insufficient_sample
    db = ctx.db()
    try:
        for i in range(55):
            emp = Employee(
                employee_no=f'EREC{i:04d}', name='X',
                department='Eng', job_family='e', job_level='P5',
            )
            db.add(emp)
        db.commit()
        emps = db.query(Employee).all()
        for e in emps:
            db.add(PerformanceRecord(
                employee_id=e.id, employee_no=e.employee_no,
                year=2026, grade='A', source='manual',
                department_snapshot=e.department,
            ))
        db.commit()
    finally:
        db.close()
    client = TestClient(ctx.app)
    resp = client.post(
        '/api/v1/performance/recompute-tiers?year=2026',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['year'] == 2026
    assert 'computed_at' in body
    assert body['sample_size'] >= 50


def test_recompute_tiers_busy_returns_409(ctx):
    """mock service 抛 TierRecomputeBusyError → 409。"""
    from backend.app.services.exceptions import TierRecomputeBusyError
    admin = ctx.make_user(role='admin')
    client = TestClient(ctx.app)
    with patch(
        'backend.app.api.v1.performance.PerformanceService.recompute_tiers',
        side_effect=TierRecomputeBusyError(2026),
    ):
        resp = client.post(
            '/api/v1/performance/recompute-tiers?year=2026',
            headers=ctx.auth_header(admin),
        )
    assert resp.status_code == 409
    body = resp.json()
    assert body['error'] == 'tier_recompute_busy'
    assert body['year'] == 2026
    assert body['retry_after_seconds'] == 5


def test_recompute_tiers_failure_returns_500(ctx):
    from backend.app.services.exceptions import TierRecomputeFailedError
    admin = ctx.make_user(role='admin')
    client = TestClient(ctx.app)
    with patch(
        'backend.app.api.v1.performance.PerformanceService.recompute_tiers',
        side_effect=TierRecomputeFailedError(2026, 'engine error'),
    ):
        resp = client.post(
            '/api/v1/performance/recompute-tiers?year=2026',
            headers=ctx.auth_header(admin),
        )
    assert resp.status_code == 500
    body = resp.json()
    assert body['error'] == 'tier_recompute_failed'
    assert body['year'] == 2026


# ---------------------------------------------------------------------------
# GET /performance/available-years (B-3)
# ---------------------------------------------------------------------------

def test_get_available_years_admin_returns_200(ctx):
    admin = ctx.make_user(role='admin')
    db = ctx.db()
    try:
        emp = Employee(
            employee_no='EYRS001', name='X',
            department='Eng', job_family='e', job_level='P5',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        db.add(PerformanceRecord(
            employee_id=emp.id, employee_no=emp.employee_no,
            year=2024, grade='A', source='manual',
            department_snapshot='Eng',
        ))
        db.add(PerformanceRecord(
            employee_id=emp.id, employee_no=emp.employee_no,
            year=2026, grade='B', source='manual',
            department_snapshot='Eng',
        ))
        db.commit()
    finally:
        db.close()
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/available-years',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 'years' in body
    assert isinstance(body['years'], list)
    assert body['years'] == sorted(body['years'], reverse=True)
    assert 2024 in body['years']
    assert 2026 in body['years']


# ---------------------------------------------------------------------------
# Phase 35 ESELF-03: GET /performance/me/tier
# ---------------------------------------------------------------------------

def test_me_tier_happy_path_returns_tier_for_bound_employee(ctx):
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35001')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 2},
        sample_size=120,
    )

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['tier'] == 2
    assert body['reason'] is None
    assert body['year'] == datetime.now().year
    assert body['data_updated_at'] is not None


def test_me_tier_happy_path_works_for_admin_role_too(ctx):
    admin_user = ctx.make_user(role='admin')
    emp_id = _seed_employee_and_bind(ctx, admin_user, 'PHE35002')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 1},
        sample_size=100,
    )

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(admin_user),
    )

    assert resp.status_code == 200
    assert resp.json()['tier'] == 1


def test_me_tier_insufficient_sample_returns_reason_not_tier(ctx):
    employee_user = ctx.make_user(role='employee')
    _seed_employee_and_bind(ctx, employee_user, 'PHE35003')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={},
        insufficient_sample=True,
        sample_size=10,
    )

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['tier'] is None
    assert body['reason'] == 'insufficient_sample'
    assert body['year'] == datetime.now().year


def test_me_tier_no_snapshot_when_db_empty(ctx):
    employee_user = ctx.make_user(role='employee')
    _seed_employee_and_bind(ctx, employee_user, 'PHE35004')

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['year'] is None
    assert body['tier'] is None
    assert body['reason'] == 'no_snapshot'
    assert body['data_updated_at'] is None


def test_me_tier_not_ranked_when_employee_absent_from_tiers_json(ctx):
    employee_user = ctx.make_user(role='employee')
    _seed_employee_and_bind(ctx, employee_user, 'PHE35005')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={'some-other-uuid-not-this-user': 1},
        sample_size=80,
    )

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['tier'] is None
    assert body['reason'] == 'not_ranked'


def test_me_tier_returns_422_for_unbound_user(ctx):
    employee_user = ctx.make_user(role='employee')

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 422
    assert '您尚未绑定员工信息' in resp.text


def test_me_tier_returns_404_when_employee_deleted(ctx):
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35006')

    db = ctx.db()
    try:
        emp = db.get(Employee, emp_id)
        assert emp is not None
        db.delete(emp)
        db.commit()
        user = db.get(User, employee_user.id)
        assert user is not None
        user.employee_id = emp_id
        db.add(user)
        db.commit()
    finally:
        db.close()

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 404
    assert '员工档案缺失' in resp.text


def test_me_tier_response_body_contains_no_other_employee_data(ctx):
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35007')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 2, 'other-1': 1, 'other-2': 3},
        sample_size=200,
    )

    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {'year', 'tier', 'reason', 'data_updated_at'}
    assert 'other-1' not in resp.text
    assert 'other-2' not in resp.text
    assert 'tiers_json' not in resp.text
    assert 'sample_size' not in resp.text
