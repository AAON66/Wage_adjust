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
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'salary-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            allow_self_registration=True,
            database_url=f'sqlite+pysqlite:///{database_path}',
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


def register_and_login_user(client: TestClient, *, email: str, role: str) -> str:
    register_response = client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Password123', 'role': role},
    )
    assert register_response.status_code == 201
    return register_response.json()['tokens']['access_token']


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


def seed_evaluation(context: ApiDatabaseContext) -> tuple[str, str]:
    db = context.session_factory()
    try:
        employee = Employee(
            employee_no='EMP-7001',
            name='Salary API User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='6000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=88,
            ai_level='Level 4',
            confidence_score=0.85,
            explanation='Confirmed evaluation.',
            status='confirmed',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        return evaluation.id, cycle.id
    finally:
        db.close()


def seed_department_budget_cycle(context: ApiDatabaseContext) -> tuple[str, str]:
    db = context.session_factory()
    try:
        engineering = Department(name='Engineering', description='Engineering scope', status='active')
        sales = Department(name='Sales', description='Sales scope', status='active')
        cycle = EvaluationCycle(name='2026 Budget Review', review_period='2026', budget_amount='6000.00', status='draft')
        db.add_all([engineering, sales, cycle])
        db.commit()
        db.refresh(cycle)

        employees = [
            Employee(
                employee_no='EMP-7101',
                name='Engineering Salary User',
                department='Engineering',
                job_family='Platform',
                job_level='P6',
                status='active',
            ),
            Employee(
                employee_no='EMP-7102',
                name='Sales Salary User',
                department='Sales',
                job_family='Commercial',
                job_level='P5',
                status='active',
            ),
        ]
        db.add_all(employees)
        db.commit()
        for employee in employees:
            db.refresh(employee)

        for employee in employees:
            submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
            db.add(submission)
            db.commit()
            db.refresh(submission)
            evaluation = AIEvaluation(
                submission_id=submission.id,
                overall_score=86,
                ai_level='Level 4',
                confidence_score=0.82,
                explanation=f'{employee.department} evaluation.',
                status='confirmed',
            )
            db.add(evaluation)
            db.commit()

        return cycle.id, engineering.id
    finally:
        db.close()


def test_salary_api_flow() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_user(client, email='admin@example.com', role='admin')
        headers = {'Authorization': f'Bearer {token}'}
        evaluation_id, cycle_id = seed_evaluation(context)

        recommend_response = client.post('/api/v1/salary/recommend', json={'evaluation_id': evaluation_id}, headers=headers)
        assert recommend_response.status_code == 201
        recommendation_id = recommend_response.json()['id']
        assert recommend_response.json()['status'] == 'recommended'
        assert recommend_response.json()['explanation']
        assert '预算视角' in recommend_response.json()['explanation']

        get_by_evaluation_response = client.get(f'/api/v1/salary/by-evaluation/{evaluation_id}', headers=headers)
        assert get_by_evaluation_response.status_code == 200
        assert get_by_evaluation_response.json()['id'] == recommendation_id
        assert '公平性判断' in get_by_evaluation_response.json()['explanation']

        get_response = client.get(f'/api/v1/salary/{recommendation_id}', headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()['evaluation_id'] == evaluation_id
        assert '风险提示' in get_response.json()['explanation'] or '预算视角' in get_response.json()['explanation']

        simulate_response = client.post('/api/v1/salary/simulate', json={'cycle_id': cycle_id, 'budget_amount': '7000.00'}, headers=headers)
        assert simulate_response.status_code == 200
        assert simulate_response.json()['cycle_id'] == cycle_id
        assert len(simulate_response.json()['items']) == 1

        update_response = client.patch(
            f'/api/v1/salary/{recommendation_id}',
            json={'final_adjustment_ratio': 0.16, 'status': 'adjusted'},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()['status'] == 'adjusted'

        lock_response = client.post(f'/api/v1/salary/{recommendation_id}/lock', headers=headers)
        assert lock_response.status_code == 200
        assert lock_response.json()['status'] == 'locked'


def test_salary_history_endpoint_is_role_restricted() -> None:
    client, context = build_client()
    with client:
        admin_token = register_and_login_user(client, email='admin-history@example.com', role='admin')
        employee_token = register_and_login_user(client, email='employee-history@example.com', role='employee')
        admin_headers = {'Authorization': f'Bearer {admin_token}'}
        employee_headers = {'Authorization': f'Bearer {employee_token}'}
        evaluation_id, _ = seed_evaluation(context)

        recommend_response = client.post('/api/v1/salary/recommend', json={'evaluation_id': evaluation_id}, headers=admin_headers)
        assert recommend_response.status_code == 201

        db = context.session_factory()
        try:
            evaluation = db.get(AIEvaluation, evaluation_id)
            assert evaluation is not None
            employee_id = evaluation.submission.employee_id
        finally:
            db.close()

        history_response = client.get(f'/api/v1/salary/history/by-employee/{employee_id}', headers=admin_headers)
        assert history_response.status_code == 200
        assert history_response.json()['total'] == 1
        assert history_response.json()['items'][0]['evaluation_id'] == evaluation_id

        forbidden_response = client.get(f'/api/v1/salary/history/by-employee/{employee_id}', headers=employee_headers)
        assert forbidden_response.status_code == 403


def test_salary_endpoints_are_scoped_by_bound_departments() -> None:
    client, context = build_client()
    with client:
        manager_token = register_and_login_user(client, email='manager@example.com', role='manager')
        outsider_token = register_and_login_user(client, email='outsider@example.com', role='manager')
        bind_user_departments(context, email='manager@example.com', department_names=['Engineering'])
        bind_user_departments(context, email='outsider@example.com', department_names=['Sales'])
        manager_headers = {'Authorization': f'Bearer {manager_token}'}
        outsider_headers = {'Authorization': f'Bearer {outsider_token}'}
        evaluation_id, cycle_id = seed_evaluation(context)

        recommend_response = client.post('/api/v1/salary/recommend', json={'evaluation_id': evaluation_id}, headers=manager_headers)
        assert recommend_response.status_code == 201
        recommendation_id = recommend_response.json()['id']

        history_db = context.session_factory()
        try:
            evaluation = history_db.get(AIEvaluation, evaluation_id)
            assert evaluation is not None
            employee_id = evaluation.submission.employee_id
        finally:
            history_db.close()

        allowed_history = client.get(f'/api/v1/salary/history/by-employee/{employee_id}', headers=manager_headers)
        assert allowed_history.status_code == 200
        assert allowed_history.json()['total'] == 1

        denied_get = client.get(f'/api/v1/salary/{recommendation_id}', headers=outsider_headers)
        assert denied_get.status_code == 403

        denied_history = client.get(f'/api/v1/salary/history/by-employee/{employee_id}', headers=outsider_headers)
        assert denied_history.status_code == 403

        denied_simulate = client.post(
            '/api/v1/salary/simulate',
            json={'cycle_id': cycle_id, 'department': 'Engineering', 'budget_amount': '7000.00'},
            headers=outsider_headers,
        )
        assert denied_simulate.status_code == 403


def test_salary_simulation_defaults_to_equal_department_budget_split() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_user(client, email='admin-budget@example.com', role='admin')
        headers = {'Authorization': f'Bearer {token}'}
        cycle_id, _ = seed_department_budget_cycle(context)

        simulate_response = client.post(
            '/api/v1/salary/simulate',
            json={'cycle_id': cycle_id, 'department': 'Engineering'},
            headers=headers,
        )
        assert simulate_response.status_code == 200
        assert simulate_response.json()['budget_amount'] == '3000.00'
        assert len(simulate_response.json()['items']) == 1
        assert simulate_response.json()['items'][0]['department'] == 'Engineering'


def test_salary_simulation_uses_explicit_cycle_department_budget() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_user(client, email='admin-budget-explicit@example.com', role='admin')
        headers = {'Authorization': f'Bearer {token}'}
        cycle_id, engineering_department_id = seed_department_budget_cycle(context)

        update_cycle_response = client.patch(
            f'/api/v1/cycles/{cycle_id}',
            json={
                'department_budgets': [
                    {'department_id': engineering_department_id, 'budget_amount': '4500.00'},
                ],
            },
            headers=headers,
        )
        assert update_cycle_response.status_code == 200

        simulate_response = client.post(
            '/api/v1/salary/simulate',
            json={'cycle_id': cycle_id, 'department': 'Engineering'},
            headers=headers,
        )
        assert simulate_response.status_code == 200
        assert simulate_response.json()['budget_amount'] == '4500.00'


def test_salary_simulation_skips_unready_evaluations_instead_of_failing() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_user(client, email='admin-skip@example.com', role='admin')
        headers = {'Authorization': f'Bearer {token}'}
        evaluation_id, cycle_id = seed_evaluation(context)

        db = context.session_factory()
        try:
            ready_evaluation = db.get(AIEvaluation, evaluation_id)
            assert ready_evaluation is not None
            ready_submission = ready_evaluation.submission
            employee = Employee(
                employee_no='EMP-7999',
                name='Pending User',
                department='Engineering',
                job_family='Platform',
                job_level='P5',
                status='active',
            )
            db.add(employee)
            db.commit()
            db.refresh(employee)

            pending_submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle_id, status='reviewing')
            db.add(pending_submission)
            db.commit()
            db.refresh(pending_submission)

            pending_evaluation = AIEvaluation(
                submission_id=pending_submission.id,
                overall_score=80,
                ai_level='Level 3',
                confidence_score=0.72,
                explanation='Not ready yet.',
                status='pending_hr',
            )
            db.add(pending_evaluation)
            db.commit()
        finally:
            db.close()

        simulate_response = client.post(
            '/api/v1/salary/simulate',
            json={'cycle_id': cycle_id, 'budget_amount': '7000.00'},
            headers=headers,
        )
        assert simulate_response.status_code == 200
        payload = simulate_response.json()
        assert len(payload['items']) == 1
        assert payload['items'][0]['employee_name'] == 'Salary API User'

