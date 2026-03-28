from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import redis as redis_lib
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'dashboard-api-{uuid4().hex}.db').as_posix()
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


def build_client() -> tuple[TestClient, ApiDatabaseContext]:
    context = ApiDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app), context


def register_and_login_admin(client: TestClient) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': 'admin@example.com', 'password': 'Password123', 'role': 'admin'},
    )
    assert register_response.status_code == 201
    return register_response.json()['tokens']['access_token']


def register_user(client: TestClient, *, email: str, role: str) -> str:
    response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': role},
    )
    assert response.status_code == 201
    return response.json()['tokens']['access_token']


def bind_user_departments(context: ApiDatabaseContext, *, email: str, department_names: list[str]) -> None:
    db = context.session_factory()
    try:
        user = db.query(User).filter(User.email == email).one()
        departments: list[Department] = []
        for name in department_names:
            department = db.query(Department).filter(Department.name == name).one_or_none()
            if department is None:
                department = Department(name=name, description=f'{name} scope', status='active')
                db.add(department)
                db.flush()
            departments.append(department)
        user.departments = departments
        db.add(user)
        db.commit()
    finally:
        db.close()


def seed_dashboard_data(context: ApiDatabaseContext) -> str:
    db = context.session_factory()
    try:
        cycle = EvaluationCycle(name='2026 Dashboard', review_period='2026', budget_amount='10000.00', status='published')
        employee = Employee(employee_no='EMP-9101', name='Dana', department='Engineering', job_family='Platform', job_level='P6', status='active')
        db.add_all([cycle, employee])
        db.commit()
        db.refresh(cycle)
        db.refresh(employee)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(submission_id=submission.id, overall_score=88, ai_level='Level 4', confidence_score=0.84, explanation='Ready for dashboard', status='reviewed')
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(evaluation_id=evaluation.id, current_salary='60000.00', recommended_ratio=0.12, recommended_salary='67200.00', ai_multiplier=1.13, certification_bonus=0.0, final_adjustment_ratio=0.12, status='approved')
        db.add(recommendation)
        db.commit()
        return cycle.id
    finally:
        db.close()


def test_dashboard_snapshot_and_child_endpoints() -> None:
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            cycle_id = seed_dashboard_data(context)

            snapshot_response = client.get(f'/api/v1/dashboard/snapshot?cycle_id={cycle_id}', headers=headers)
            assert snapshot_response.status_code == 200
            body = snapshot_response.json()
            assert body['cycle_summary']['cycle_id'] == cycle_id
            assert body['overview']['items'][0]['label'] == '覆盖员工数'
            assert body['overview']['items'][0]['value'] == '1'
            assert body['ai_level_distribution']['total'] == 1
            assert body['heatmap']['total'] == 1
            assert body['roi_distribution']['total'] == 1
            assert body['department_insights'][0]['department'] == 'Engineering'
            assert body['top_talents'][0]['employee_name'] == 'Dana'
            assert body['action_items'][0]['title'] == '待人工复核'

            overview_response = client.get(f'/api/v1/dashboard/overview?cycle_id={cycle_id}', headers=headers)
            assert overview_response.status_code == 200
            assert overview_response.json()['items'][1]['label'] == '已用预算'

            distribution_response = client.get(f'/api/v1/dashboard/ai-level-distribution?cycle_id={cycle_id}', headers=headers)
            assert distribution_response.status_code == 200
            assert distribution_response.json()['items'][3]['label'] == 'Level 4'

            heatmap_response = client.get(f'/api/v1/dashboard/department-heatmap?cycle_id={cycle_id}', headers=headers)
            assert heatmap_response.status_code == 200
            assert heatmap_response.json()['items'][0]['department'] == 'Engineering'

            roi_response = client.get(f'/api/v1/dashboard/roi-distribution?cycle_id={cycle_id}', headers=headers)
            assert roi_response.status_code == 200
            assert roi_response.json()['total'] == 1


def test_dashboard_is_scoped_by_bound_departments() -> None:
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            manager_token = register_user(client, email='manager@example.com', role='manager')
            bind_user_departments(context, email='manager@example.com', department_names=['Sales'])
            headers = {'Authorization': f'Bearer {manager_token}'}
            cycle_id = seed_dashboard_data(context)

            snapshot_response = client.get(f'/api/v1/dashboard/snapshot?cycle_id={cycle_id}', headers=headers)
            assert snapshot_response.status_code == 200
            body = snapshot_response.json()
            assert body['overview']['items'][0]['value'] == '0'
            assert body['ai_level_distribution']['total'] == 0
            assert body['heatmap']['total'] == 0
            assert body['department_insights'] == []
            assert body['top_talents'] == []


# ---------------------------------------------------------------
# Helper: mock Redis for new cached endpoints
# ---------------------------------------------------------------

def _make_mock_redis() -> MagicMock:
    """Dict-backed mock Redis."""
    store: dict[str, str] = {}
    mock = MagicMock(spec=redis_lib.Redis)
    mock.get = MagicMock(side_effect=lambda k: store.get(k))
    mock.setex = MagicMock(side_effect=lambda k, t, v: store.__setitem__(k, v))
    mock.keys = MagicMock(side_effect=lambda p: [k for k in store if fnmatch.fnmatch(k, p)])
    mock.delete = MagicMock(side_effect=lambda *ks: sum(1 for k in ks if store.pop(k, None) is not None))
    mock.ping = MagicMock(return_value=True)
    return mock


def _build_client_with_redis(mock_redis=None):
    """Build test client with Redis mock injected."""
    client, context = build_client()
    if mock_redis is None:
        mock_redis = _make_mock_redis()
    # Patch get_redis to return our mock
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        yield client, context, mock_redis


# ---------------------------------------------------------------
# New endpoint tests
# ---------------------------------------------------------------

def test_kpi_summary_endpoint_returns_200() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        cycle_id = seed_dashboard_data(context)

        response = client.get(f'/api/v1/dashboard/kpi-summary?cycle_id={cycle_id}', headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert 'pending_approvals' in body
        assert 'total_employees' in body
        assert 'evaluated_employees' in body
        assert 'avg_adjustment_ratio' in body
        assert 'level_summary' in body


def test_salary_distribution_endpoint_returns_200() -> None:
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            cycle_id = seed_dashboard_data(context)

            response = client.get(f'/api/v1/dashboard/salary-distribution?cycle_id={cycle_id}', headers=headers)
            assert response.status_code == 200
            body = response.json()
            assert 'items' in body
            assert 'total' in body


def test_approval_pipeline_endpoint_returns_200() -> None:
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            cycle_id = seed_dashboard_data(context)

            response = client.get(f'/api/v1/dashboard/approval-pipeline?cycle_id={cycle_id}', headers=headers)
            assert response.status_code == 200
            body = response.json()
            assert 'items' in body
            assert 'total' in body


def test_department_drilldown_endpoint_returns_200() -> None:
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            seed_dashboard_data(context)

            response = client.get('/api/v1/dashboard/department-drilldown?department=Engineering', headers=headers)
            assert response.status_code == 200
            body = response.json()
            assert body['department'] == 'Engineering'
            assert 'level_distribution' in body
            assert 'employee_count' in body


def test_dashboard_endpoints_require_auth() -> None:
    client, _ = build_client()
    with client:
        endpoints = [
            '/api/v1/dashboard/overview',
            '/api/v1/dashboard/ai-level-distribution',
            '/api/v1/dashboard/kpi-summary',
            '/api/v1/dashboard/salary-distribution',
            '/api/v1/dashboard/approval-pipeline',
            '/api/v1/dashboard/department-drilldown?department=X',
            '/api/v1/dashboard/snapshot',
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f'{endpoint} should require auth'


def test_employee_role_gets_403() -> None:
    """Employee role should get 403 on all dashboard endpoints (review fix #3)."""
    mock_redis = _make_mock_redis()
    with patch('backend.app.api.v1.dashboard.get_redis', return_value=mock_redis):
        client, context = build_client()
        with client:
            employee_token = register_user(client, email='emp@example.com', role='employee')
            headers = {'Authorization': f'Bearer {employee_token}'}

            endpoints = [
                '/api/v1/dashboard/overview',
                '/api/v1/dashboard/kpi-summary',
                '/api/v1/dashboard/salary-distribution',
                '/api/v1/dashboard/approval-pipeline',
                '/api/v1/dashboard/snapshot',
            ]
            for endpoint in endpoints:
                response = client.get(endpoint, headers=headers)
                assert response.status_code == 403, f'{endpoint} should return 403 for employee, got {response.status_code}'


def test_cached_endpoint_returns_503_when_redis_down() -> None:
    """Cached endpoints should return 503 when Redis is unavailable (per D-03)."""
    def raise_connection_error():
        raise redis_lib.ConnectionError('Redis down')

    with patch('backend.app.api.v1.dashboard.get_redis', side_effect=raise_connection_error):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}

            cached_endpoints = [
                '/api/v1/dashboard/salary-distribution',
                '/api/v1/dashboard/approval-pipeline',
                '/api/v1/dashboard/department-drilldown?department=Engineering',
            ]
            for endpoint in cached_endpoints:
                response = client.get(endpoint, headers=headers)
                assert response.status_code == 503, f'{endpoint} should return 503 when Redis down, got {response.status_code}'


def test_kpi_summary_works_without_redis() -> None:
    """KPI summary does NOT use Redis -- should work even when Redis is down (review fix #2)."""
    def raise_connection_error():
        raise redis_lib.ConnectionError('Redis down')

    with patch('backend.app.api.v1.dashboard.get_redis', side_effect=raise_connection_error):
        client, context = build_client()
        with client:
            token = register_and_login_admin(client)
            headers = {'Authorization': f'Bearer {token}'}
            cycle_id = seed_dashboard_data(context)

            response = client.get(f'/api/v1/dashboard/kpi-summary?cycle_id={cycle_id}', headers=headers)
            assert response.status_code == 200, f'kpi-summary should work without Redis, got {response.status_code}'

