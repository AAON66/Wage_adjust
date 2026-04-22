"""Phase 32 顶层共享 fixture。

提供以下 12 个 fixture，下游 Plan 02-06 的所有测试可直接 import 使用：

DB / ORM 层：
  - db_session: 隔离的 SQLite in-memory session（每个测试函数独立）
  - employee_factory: 创建 Employee 行（默认值齐全）
  - user_factory: 创建 User 行（默认值齐全 + 自动 hash 密码）
  - import_job_factory: 创建 ImportJob 行（Phase 32 新字段已就绪）

API 测试层（ApiDatabaseContext 模式 - 参考 test_audit_api.py 上抬）：
  - test_app: FastAPI app instance（settings 已 override，dep 已 override）
  - hrbp_user_token / employee_user_token: JWT access tokens（直接可用 Bearer 注入）
  - client_anon: TestClient 无 token
  - client_hrbp: TestClient + hrbp Bearer token
  - client_employee: TestClient + employee Bearer token

存储 / Phase 32 专用：
  - tmp_uploads_dir: 隔离 storage_base_dir 到 pytest tmp_path
  - xlsx_factory: 4 类资格 import_type 的 xlsx 字节 builder 字典入口
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.core.database import (
    Base,
    create_db_engine,
    create_session_factory,
    init_database,
)
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules

# ============ DB / ORM 层 ============

load_model_modules()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """SQLite in-memory + StaticPool；每个测试独立 schema。"""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def employee_factory(db_session: Session):
    """构造 Employee；返回 callable，可重复调用创建多人。"""
    from backend.app.models.employee import Employee
    counter = {'n': 0}

    def _make(
        *,
        employee_no: str | None = None,
        name: str = '测试员工',
        department: str = 'R&D',
        sub_department: str | None = None,
        job_family: str = 'engineering',
        job_level: str = 'P5',
        status: str = 'active',
        hire_date=None,
        last_salary_adjustment_date=None,
    ) -> Employee:
        counter['n'] += 1
        emp_no = employee_no or f'E{counter["n"]:05d}'
        emp = Employee(
            employee_no=emp_no,
            name=name,
            department=department,
            sub_department=sub_department,
            job_family=job_family,
            job_level=job_level,
            status=status,
            hire_date=hire_date,
            last_salary_adjustment_date=last_salary_adjustment_date,
        )
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)
        return emp

    return _make


@pytest.fixture()
def user_factory(db_session: Session):
    """构造 User；自动 hash 密码 'Password123'。"""
    from backend.app.models.user import User
    counter = {'n': 0}

    def _make(
        *,
        email: str | None = None,
        password: str = 'Password123',
        role: str = 'hrbp',
        employee_id: str | None = None,
    ) -> User:
        counter['n'] += 1
        user_email = email or f'user{counter["n"]}_{uuid4().hex[:6]}@example.com'
        user = User(
            email=user_email,
            hashed_password=get_password_hash(password),
            role=role,
            employee_id=employee_id,
            token_version=0,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def import_job_factory(db_session: Session):
    """创建 ImportJob 行；用于并发锁 / expire_stale 测试。"""
    from backend.app.models.import_job import ImportJob

    def _make(
        *,
        import_type: str = 'performance_grades',
        status: str = 'processing',
        file_name: str = 'test.xlsx',
        overwrite_mode: str = 'merge',
        actor_id: str | None = None,
        total_rows: int = 0,
        result_summary: dict | None = None,
    ) -> ImportJob:
        job = ImportJob(
            file_name=file_name,
            import_type=import_type,
            status=status,
            total_rows=total_rows,
            success_rows=0,
            failed_rows=0,
            result_summary=result_summary or {},
            overwrite_mode=overwrite_mode,
            actor_id=actor_id,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _make


# ============ Storage 层 ============

@pytest.fixture()
def tmp_uploads_dir(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """隔离 uploads/ 目录到 pytest tmp_path；防止测试污染开发文件系统。"""
    from backend.app.core import config as cfg_module
    uploads = tmp_path / 'uploads'
    uploads.mkdir(exist_ok=True)
    cfg_module.get_settings.cache_clear()
    monkeypatch.setenv('STORAGE_BASE_DIR', str(uploads))
    cfg_module.get_settings.cache_clear()
    yield uploads
    cfg_module.get_settings.cache_clear()


# ============ xlsx builder 入口 ============

@pytest.fixture()
def xlsx_factory():
    """构造测试用 xlsx 字节，可被 ImportService._load_table 读入。

    返回字典：{'hire_info': callable, 'non_statutory_leave': callable,
               'performance_grades': callable, 'salary_adjustments': callable}
    """
    from backend.tests.fixtures.imports.builders import (
        build_hire_info_xlsx,
        build_non_statutory_leave_xlsx,
        build_performance_grades_xlsx,
        build_salary_adjustments_xlsx,
    )
    return {
        'hire_info': build_hire_info_xlsx,
        'non_statutory_leave': build_non_statutory_leave_xlsx,
        'performance_grades': build_performance_grades_xlsx,
        'salary_adjustments': build_salary_adjustments_xlsx,
    }


# ============ API 测试层（ApiDatabaseContext 模式）============

class _ApiDatabaseContext:
    """File-based SQLite per-test app context，与 test_audit_api.py 模式一致。"""
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = (temp_root / f'phase32-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            allow_self_registration=True,
            database_url=f'sqlite+pysqlite:///{db_path}',
        )
        load_model_modules()
        self.engine = create_db_engine(self.settings)
        init_database(self.engine)
        self.session_factory = create_session_factory(self.settings)
        self._db_path = db_path

    def override_get_db(self) -> Generator[Session, None, None]:
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def cleanup(self) -> None:
        self.engine.dispose()
        try:
            Path(self._db_path).unlink(missing_ok=True)
        except OSError:
            pass


@pytest.fixture()
def _api_context() -> Generator[_ApiDatabaseContext, None, None]:
    ctx = _ApiDatabaseContext()
    try:
        yield ctx
    finally:
        ctx.cleanup()


@pytest.fixture()
def test_app(_api_context: _ApiDatabaseContext):
    """FastAPI app instance with overridden get_db dep。"""
    app = create_app(_api_context.settings)
    app.dependency_overrides[get_db] = _api_context.override_get_db
    return app


def _create_user_and_token(ctx: _ApiDatabaseContext, *, email: str, role: str) -> tuple[str, str]:
    """直接在 API context DB 中创建 User + 返回 (user_id, jwt_token)。"""
    from backend.app.models.user import User
    db = ctx.session_factory()
    try:
        user = User(
            email=email,
            hashed_password=get_password_hash('Password123'),
            role=role,
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
        user_role = user.role
        user_tv = user.token_version
    finally:
        db.close()
    token = create_access_token(
        subject=user_id, role=user_role, settings=ctx.settings, token_version=user_tv,
    )
    return user_id, token


@pytest.fixture()
def hrbp_user_token(_api_context: _ApiDatabaseContext) -> str:
    _, token = _create_user_and_token(
        _api_context, email=f'hrbp-{uuid4().hex[:6]}@example.com', role='hrbp',
    )
    return token


@pytest.fixture()
def employee_user_token(_api_context: _ApiDatabaseContext) -> str:
    _, token = _create_user_and_token(
        _api_context, email=f'emp-{uuid4().hex[:6]}@example.com', role='employee',
    )
    return token


@pytest.fixture()
def client_anon(test_app) -> TestClient:
    return TestClient(test_app)


@pytest.fixture()
def client_hrbp(test_app, hrbp_user_token: str) -> TestClient:
    client = TestClient(test_app)
    client.headers.update({'Authorization': f'Bearer {hrbp_user_token}'})
    return client


@pytest.fixture()
def client_employee(test_app, employee_user_token: str) -> TestClient:
    client = TestClient(test_app)
    client.headers.update({'Authorization': f'Bearer {employee_user_token}'})
    return client
