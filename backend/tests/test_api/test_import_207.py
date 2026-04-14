from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.department import Department


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'import-207-{uuid4().hex}.db').as_posix()
        self.settings = Settings(allow_self_registration=True, database_url=f'sqlite+pysqlite:///{database_path}')
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


def _build_client() -> tuple[TestClient, ApiDatabaseContext]:
    context = ApiDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app), context


def _register_and_login_admin(client: TestClient) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': 'admin@example.com', 'password': 'Password123', 'role': 'admin'},
    )
    assert register_response.status_code == 201
    return register_response.json()['tokens']['access_token']


def _seed_departments(context: ApiDatabaseContext, *names: str) -> None:
    db = context.session_factory()
    try:
        for name in names:
            db.add(Department(name=name, description=f'{name} scope', status='active'))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# IMP-02: HTTP 207 Multi-Status for partial failures
# ---------------------------------------------------------------------------


class TestHttp207Response:
    """IMP-02: Partial failure returns HTTP 207 Multi-Status."""

    def test_partial_failure_returns_207(self) -> None:
        """Upload CSV with valid + invalid rows, expect response.status_code == 207."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            _seed_departments(context, '产品技术中心')

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'API-001,有效行,产品技术中心,技术,P6,active,\n'
                'API-002,无效行,不存在部门,技术,P7,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            assert response.status_code == 207, f'Expected 207, got {response.status_code}'

    def test_all_success_returns_201(self) -> None:
        """Upload all-valid CSV, expect response.status_code == 201."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            _seed_departments(context, '产品技术中心')

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'OK-001,全成功,产品技术中心,技术,P6,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            assert response.status_code == 201

    def test_all_failure_returns_207(self) -> None:
        """Upload all-invalid CSV, expect response.status_code == 207."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'FAIL-001,全失败,不存在部门,技术,P7,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            assert response.status_code == 207


# ---------------------------------------------------------------------------
# IMP-03: Response contains summary fields + per-row error details
# ---------------------------------------------------------------------------


class TestResponseSummary:
    """IMP-03: Response includes total_rows, success_rows, failed_rows and row-level errors."""

    def test_response_contains_summary_fields(self) -> None:
        """Assert response JSON contains total_rows, success_rows, failed_rows."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            _seed_departments(context, '产品技术中心')

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'SUM-001,汇总测试,产品技术中心,技术,P6,active,\n'
                'SUM-002,汇总失败,不存在部门,技术,P7,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            data = response.json()
            assert 'total_rows' in data
            assert 'success_rows' in data
            assert 'failed_rows' in data
            assert data['total_rows'] == 2
            assert data['success_rows'] == 1
            assert data['failed_rows'] == 1

    def test_failed_rows_have_error_messages(self) -> None:
        """Each failed row must have row_index, status, and message fields."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'ERR-001,错误行,不存在部门,技术,P7,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            rows = response.json()['result_summary']['rows']
            failed = [r for r in rows if r['status'] == 'failed']
            assert len(failed) >= 1
            for row in failed:
                assert 'row_index' in row
                assert 'status' in row
                assert 'message' in row

    def test_failed_rows_have_error_column(self) -> None:
        """Failed rows must include error_column field identifying which column caused failure."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}

            csv = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'COL-001,错误列测试,不存在部门,技术,P7,active,\n'
            ).encode('utf-8')
            files = {'file': ('test.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            rows = response.json()['result_summary']['rows']
            failed = [r for r in rows if r['status'] == 'failed']
            assert len(failed) >= 1
            for row in failed:
                assert 'error_column' in row, 'Failed rows must include error_column field'

    def test_mixed_100_rows_90_success_10_failure(self) -> None:
        """IMP-01/IMP-02 gate test: 100 rows CSV (90 valid + 10 invalid),
        expect 207 response, success_rows=90, failed_rows=10."""
        client, context = _build_client()
        with client:
            token = _register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            _seed_departments(context, '产品技术中心')

            lines = ['员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号']
            for i in range(1, 91):
                lines.append(f'BULK-{i:03d},有效员工{i},产品技术中心,技术,P6,active,')
            for i in range(91, 101):
                lines.append(f'BULK-{i:03d},无效员工{i},不存在部门{i},技术,P7,active,')
            csv = '\n'.join(lines).encode('utf-8')
            files = {'file': ('bulk100.csv', io.BytesIO(csv), 'text/csv')}
            response = client.post('/api/v1/imports/jobs?import_type=employees', files=files, headers=headers)
            assert response.status_code == 207
            data = response.json()
            assert data['success_rows'] == 90
            assert data['failed_rows'] == 10
            assert data['total_rows'] == 100
