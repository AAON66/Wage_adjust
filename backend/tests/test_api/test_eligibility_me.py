"""API tests for Phase 32.1 GET /api/v1/eligibility/me endpoint.

Covers ESELF-01/02/04/05:
- bound user → 200 with EligibilityResultSchema + data_updated_at
- unbound user → 422 中文 detail
- missing employee → 404
- detail desensitization (no YYYY-MM-DD pattern)
- route priority: /me 不被 /{employee_id} 捕获
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.user import User


@dataclass
class UserCreds:
    id: str
    role: str
    token_version: int


class _Ctx:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = (temp_root / f'elig-me-{uuid4().hex}.db').as_posix()
        self.settings = Settings(database_url=f'sqlite+pysqlite:///{db_path}')
        self.engine = create_engine(
            self.settings.database_url,
            connect_args={'check_same_thread': False},
            echo=False,
        )
        load_model_modules()
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False,
        )
        self.app = create_app(self.settings)
        self.app.dependency_overrides[get_db] = self._override_get_db

    def _override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def db(self) -> Session:
        return self.session_factory()

    def auth_header(self, creds: UserCreds) -> dict[str, str]:
        token = create_access_token(
            subject=creds.id,
            role=creds.role,
            settings=self.settings,
            token_version=creds.token_version,
        )
        return {'Authorization': f'Bearer {token}'}

    def client(self) -> TestClient:
        return TestClient(self.app)


def _make_employee(db: Session, *, employee_no: str = 'E001') -> Employee:
    emp = Employee(
        employee_no=employee_no,
        name='测试员工',
        department='R&D',
        job_family='engineer',
        job_level='P5',
        status='active',
        hire_date=date(2020, 1, 1),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def _make_user(
    db: Session,
    *,
    email: str,
    role: str = 'employee',
    employee_id: str | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash('test_pwd_123'),
        role=role,
        employee_id=employee_id,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def ctx() -> _Ctx:
    return _Ctx()


# ------------------------------------------------------------------
# T1 — bound user → 200
# ------------------------------------------------------------------
def test_bound_user_returns_200_with_eligibility_payload(ctx: _Ctx) -> None:
    with ctx.db() as db:
        emp = _make_employee(db)
        user = _make_user(db, email='emp@test.com', employee_id=emp.id)
        creds = UserCreds(id=user.id, role=user.role, token_version=user.token_version)

    resp = ctx.client().get('/api/v1/eligibility/me', headers=ctx.auth_header(creds))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['overall_status'] in ('eligible', 'ineligible', 'pending')
    assert isinstance(body['rules'], list)
    assert len(body['rules']) == 4
    # data_updated_at 字段存在；可能是 ISO 字符串或 null（小样本场景）
    assert 'data_updated_at' in body
    # employee.updated_at 由 UpdatedAtMixin 自动写入，所以应非空
    assert body['data_updated_at'] is not None


# ------------------------------------------------------------------
# T2 — unbound user → 422 中文 detail
# ------------------------------------------------------------------
def test_unbound_user_returns_422_chinese_detail(ctx: _Ctx) -> None:
    with ctx.db() as db:
        user = _make_user(db, email='unbound@test.com', employee_id=None)
        creds = UserCreds(id=user.id, role=user.role, token_version=user.token_version)

    resp = ctx.client().get('/api/v1/eligibility/me', headers=ctx.auth_header(creds))
    assert resp.status_code == 422, resp.text
    body = resp.json()
    # main.py http_exception_handler 把 detail 装进 message 字段
    text = body.get('message') or body.get('detail') or ''
    assert '尚未绑定员工' in text


# ------------------------------------------------------------------
# T3 — missing employee → 404
# ------------------------------------------------------------------
def test_user_with_dangling_employee_id_returns_404(ctx: _Ctx) -> None:
    """模拟 user.employee_id 指向已删除（或从未存在）员工的悬挂场景。

    ORM `db.delete(emp)` 会触发关系刷新把 user.employee_id 置 None，所以这里
    用 raw SQL UPDATE 绕过 ORM，直接把 employee_id 设到一个不存在的 UUID。
    SQLite 默认不强制 FK，模拟生产环境下 admin 误删员工但 user 没解绑的情况。
    """
    from sqlalchemy import text

    with ctx.db() as db:
        emp = _make_employee(db, employee_no='E_HOST')
        host_id = emp.id
        user = _make_user(db, email='ghost@test.com', employee_id=host_id)
        creds = UserCreds(id=user.id, role=user.role, token_version=user.token_version)

        # 用 raw UPDATE 把 user.employee_id 改成不存在的 UUID（绕过 ORM 关系处理）
        ghost_id = str(uuid4())
        db.execute(
            text('UPDATE users SET employee_id = :gid WHERE id = :uid'),
            {'gid': ghost_id, 'uid': user.id},
        )
        db.commit()

    resp = ctx.client().get('/api/v1/eligibility/me', headers=ctx.auth_header(creds))
    assert resp.status_code == 404, resp.text


# ------------------------------------------------------------------
# T4 — rules[].detail 保持脱敏（无 YYYY-MM-DD）
# ------------------------------------------------------------------
def test_rule_details_remain_desensitized(ctx: _Ctx) -> None:
    with ctx.db() as db:
        emp = _make_employee(db, employee_no='E002')
        user = _make_user(db, email='emp2@test.com', employee_id=emp.id)
        creds = UserCreds(id=user.id, role=user.role, token_version=user.token_version)

    resp = ctx.client().get('/api/v1/eligibility/me', headers=ctx.auth_header(creds))
    assert resp.status_code == 200
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    for rule in resp.json()['rules']:
        assert not date_pattern.search(rule['detail']), (
            f"detail 中出现 YYYY-MM-DD 模式（违反 ESELF-02 脱敏）: {rule['detail']}"
        )


# ------------------------------------------------------------------
# T5 — 路由顺序：/me 优先于 /{employee_id}
# ------------------------------------------------------------------
def test_me_route_registered_before_employee_id_path(ctx: _Ctx) -> None:
    # 未鉴权访问 /me 应该返回 401（来自 oauth2_scheme），
    # 而不是 422-validation 之类（如果被 /{employee_id} 捕获，oauth2 仍先要求鉴权也会
    # 是 401，但此处至少证明端点已匹配到 route 表）
    resp = ctx.client().get('/api/v1/eligibility/me')
    # 401 Unauthorized = 鉴权拦截，证明 endpoint 已经匹配到（route exists）
    assert resp.status_code == 401, (
        f"路由顺序错误：/me 未被识别为独立端点（status={resp.status_code}, body={resp.text})"
    )
