from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'api-{uuid4().hex}.db').as_posix()
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


def bind_user_departments(context: ApiDatabaseContext, *, email: str, departments: list[str]) -> None:
    db = context.session_factory()
    try:
        user = db.query(User).filter(User.email == email).one()
        resolved_departments: list[Department] = []
        for name in departments:
            department = db.query(Department).filter(Department.name == name).one_or_none()
            if department is None:
                department = Department(name=name, description=f'{name} scope', status='active')
                db.add(department)
                db.flush()
            resolved_departments.append(department)
        user.departments = resolved_departments
        db.add(user)
        db.commit()
    finally:
        db.close()


def seed_departments(context: ApiDatabaseContext, *names: str) -> list[dict[str, str]]:
    db = context.session_factory()
    try:
        created: list[dict[str, str]] = []
        for name in names:
            department = db.query(Department).filter(Department.name == name).one_or_none()
            if department is None:
                department = Department(name=name, description=f'{name} scope', status='active')
                db.add(department)
                db.flush()
            created.append({'id': department.id, 'name': department.name})
        db.commit()
        return created
    finally:
        db.close()


def test_employee_and_cycle_api_flow() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed_departments(context, 'Engineering')

        create_employee_response = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-1001',
                'name': 'Alice Zhang',
                'id_card_no': '310101199001010123',
                'department': 'Engineering',
                'sub_department': 'Backend Platform',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=headers,
        )
        assert create_employee_response.status_code == 201
        employee_id = create_employee_response.json()['id']

        list_employees_response = client.get('/api/v1/employees?department=Engineering', headers=headers)
        assert list_employees_response.status_code == 200
        assert list_employees_response.json()['total'] == 1

        detail_response = client.get(f'/api/v1/employees/{employee_id}', headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()['employee_no'] == 'EMP-1001'
        assert detail_response.json()['id_card_no'] == '310101199001010123'
        assert detail_response.json()['sub_department'] == 'Backend Platform'

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2026 Annual Review',
                'review_period': '2026',
                'budget_amount': '250000.00',
                'status': 'draft',
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 201
        cycle_id = create_cycle_response.json()['id']

        list_cycles_response = client.get('/api/v1/cycles', headers=headers)
        assert list_cycles_response.status_code == 200
        assert list_cycles_response.json()['total'] == 1

        update_cycle_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={'name': '2026 Annual Review Updated', 'status': 'collecting'},
            headers=headers,
        )
        assert update_cycle_response.status_code == 200
        assert update_cycle_response.json()['name'] == '2026 Annual Review Updated'
        assert update_cycle_response.json()['status'] == 'collecting'

        publish_cycle_response = client.post(f'/api/v1/cycles/{cycle_id}/publish', headers=headers)
        assert publish_cycle_response.status_code == 200
        assert publish_cycle_response.json()['status'] == 'published'

        archive_cycle_response = client.post(f'/api/v1/cycles/{cycle_id}/archive', headers=headers)
        assert archive_cycle_response.status_code == 200
        assert archive_cycle_response.json()['status'] == 'archived'

        archived_update_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={'name': 'Should Fail'},
            headers=headers,
        )
        assert archived_update_response.status_code == 400
        assert archived_update_response.json()['message'] == 'Archived cycles cannot be edited.'


def test_employee_list_requires_authentication() -> None:
    client, _ = build_client()
    with client:
        response = client.get('/api/v1/employees')
        assert response.status_code == 401


def test_manager_only_sees_bound_department_employees() -> None:
    client, context = build_client()
    with client:
        admin_token = register_and_login_admin(client)
        manager_token = register_user(client, email='manager@example.com', role='manager')
        bind_user_departments(context, email='manager@example.com', departments=['Engineering'])
        admin_headers = {'Authorization': f'Bearer {admin_token}'}
        manager_headers = {'Authorization': f'Bearer {manager_token}'}
        seed_departments(context, 'Engineering', 'Sales')

        engineering_employee = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-1002',
                'name': 'Eng User',
                'department': 'Engineering',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=admin_headers,
        )
        sales_employee = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-1003',
                'name': 'Sales User',
                'department': 'Sales',
                'job_family': 'Commercial',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=admin_headers,
        )
        assert engineering_employee.status_code == 201
        assert sales_employee.status_code == 201

        list_response = client.get('/api/v1/employees', headers=manager_headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 1
        assert list_response.json()['items'][0]['department'] == 'Engineering'

        allowed_detail = client.get(f"/api/v1/employees/{engineering_employee.json()['id']}", headers=manager_headers)
        assert allowed_detail.status_code == 200

        denied_detail = client.get(f"/api/v1/employees/{sales_employee.json()['id']}", headers=manager_headers)
        assert denied_detail.status_code == 403


def test_employee_creation_requires_existing_department() -> None:
    client, _ = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}

        create_employee_response = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-1999',
                'name': 'No Department User',
                'department': 'Ghost Team',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=headers,
        )
        assert create_employee_response.status_code == 400
        payload = create_employee_response.json()
        assert payload.get('detail') == 'Department not found. Please create it in department management first.' or payload.get('message') == 'Department not found. Please create it in department management first.'


def test_cycle_department_budget_allocations_can_be_created_and_updated() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        departments = seed_departments(context, 'Engineering', 'Sales')

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2026 Department Budget',
                'review_period': '2026',
                'budget_amount': '300000.00',
                'status': 'draft',
                'department_budgets': [
                    {'department_id': departments[0]['id'], 'budget_amount': '180000.00'},
                ],
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 201
        cycle = create_cycle_response.json()
        assert len(cycle['department_budgets']) == 1
        assert cycle['department_budgets'][0]['department_name'] == 'Engineering'
        cycle_id = cycle['id']

        update_cycle_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={
                'budget_amount': '320000.00',
                'department_budgets': [
                    {'department_id': departments[0]['id'], 'budget_amount': '200000.00'},
                    {'department_id': departments[1]['id'], 'budget_amount': '120000.00'},
                ],
            },
            headers=headers,
        )
        assert update_cycle_response.status_code == 200
        updated_cycle = update_cycle_response.json()
        assert len(updated_cycle['department_budgets']) == 2
        assert {item['department_name'] for item in updated_cycle['department_budgets']} == {'Engineering', 'Sales'}


def test_cycle_department_budget_cannot_exceed_total_budget() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        departments = seed_departments(context, 'Engineering', 'Sales')

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2026 Over Budget',
                'review_period': '2026',
                'budget_amount': '100000.00',
                'status': 'draft',
                'department_budgets': [
                    {'department_id': departments[0]['id'], 'budget_amount': '60000.00'},
                    {'department_id': departments[1]['id'], 'budget_amount': '50000.00'},
                ],
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 400
        payload = create_cycle_response.json()
        assert payload.get('detail') == 'Department budget allocations cannot exceed the total cycle budget.' or payload.get('message') == 'Department budget allocations cannot exceed the total cycle budget.'


def test_cycle_can_be_deleted_when_no_submissions_exist() -> None:
    client, _ = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2027 Delete Ready',
                'review_period': '2027',
                'budget_amount': '120000.00',
                'status': 'draft',
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 201
        cycle_id = create_cycle_response.json()['id']

        delete_cycle_response = client.delete(f'/api/v1/cycles/{cycle_id}', headers=headers)
        assert delete_cycle_response.status_code == 204

        list_cycles_response = client.get('/api/v1/cycles', headers=headers)
        assert list_cycles_response.status_code == 200
        assert list_cycles_response.json()['total'] == 0


def test_cycle_delete_is_blocked_when_submissions_exist() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed_departments(context, 'Engineering')

        create_employee_response = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-2001',
                'name': 'Delete Guard',
                'department': 'Engineering',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=headers,
        )
        assert create_employee_response.status_code == 201
        employee_id = create_employee_response.json()['id']

        create_cycle_response = client.post(
            '/api/v1/cycles',
            json={
                'name': '2027 Protected Cycle',
                'review_period': '2027',
                'budget_amount': '220000.00',
                'status': 'draft',
            },
            headers=headers,
        )
        assert create_cycle_response.status_code == 201
        cycle_id = create_cycle_response.json()['id']

        ensure_submission_response = client.post(
            '/api/v1/submissions/ensure',
            json={'employee_id': employee_id, 'cycle_id': cycle_id},
            headers=headers,
        )
        assert ensure_submission_response.status_code == 200

        delete_cycle_response = client.delete(f'/api/v1/cycles/{cycle_id}', headers=headers)
        assert delete_cycle_response.status_code == 400
        payload = delete_cycle_response.json()
        assert payload.get('detail') == 'This cycle already has employee submissions and cannot be deleted.' or payload.get('message') == 'This cycle already has employee submissions and cannot be deleted.'


def test_employee_profile_can_be_updated() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        seed_departments(context, 'Engineering', 'Sales')

        create_employee_response = client.post(
            '/api/v1/employees',
            json={
                'employee_no': 'EMP-3001',
                'name': 'Editable User',
                'id_card_no': '310101199001010129',
                'department': 'Engineering',
                'sub_department': 'Backend Platform',
                'job_family': 'Platform',
                'job_level': 'P5',
                'status': 'active',
                'manager_id': None,
            },
            headers=headers,
        )
        assert create_employee_response.status_code == 201
        employee_id = create_employee_response.json()['id']

        update_employee_response = client.patch(
            f'/api/v1/employees/{employee_id}',
            json={
                'name': 'Updated User',
                'department': 'Sales',
                'sub_department': 'Commercial Ops',
                'job_family': 'Business',
                'job_level': 'P6',
                'status': 'inactive',
            },
            headers=headers,
        )
        assert update_employee_response.status_code == 200
        payload = update_employee_response.json()
        assert payload['name'] == 'Updated User'
        assert payload['department'] == 'Sales'
        assert payload['sub_department'] == 'Commercial Ops'
        assert payload['job_family'] == 'Business'
        assert payload['job_level'] == 'P6'
        assert payload['status'] == 'inactive'
