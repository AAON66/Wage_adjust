from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'salary-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
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


def test_salary_api_flow() -> None:
    client, context = build_client()
    with client:
        token = register_and_login_admin(client)
        headers = {'Authorization': f'Bearer {token}'}
        evaluation_id, cycle_id = seed_evaluation(context)

        recommend_response = client.post('/api/v1/salary/recommend', json={'evaluation_id': evaluation_id}, headers=headers)
        assert recommend_response.status_code == 201
        recommendation_id = recommend_response.json()['id']
        assert recommend_response.json()['status'] == 'recommended'

        get_response = client.get(f'/api/v1/salary/{recommendation_id}', headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()['evaluation_id'] == evaluation_id

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