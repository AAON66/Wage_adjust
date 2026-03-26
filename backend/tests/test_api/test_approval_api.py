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
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class ApiDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'approval-api-{uuid4().hex}.db').as_posix()
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


def seed_recommendation(context: ApiDatabaseContext) -> tuple[str, str]:
    db = context.session_factory()
    try:
        employee = Employee(
            employee_no='EMP-8301',
            name='Approval API User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Approval', review_period='2026', budget_amount='12000.00', status='published')
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
            overall_score=90,
            ai_level='Level 4',
            confidence_score=0.87,
            explanation='Ready for approval.',
            status='pending_hr',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        recommendation = SalaryRecommendation(
            evaluation_id=evaluation.id,
            current_salary='60000.00',
            recommended_ratio=0.14,
            recommended_salary='68400.00',
            ai_multiplier=1.13,
            certification_bonus=0.0,
            final_adjustment_ratio=0.14,
            status='recommended',
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation.id, evaluation.id
    finally:
        db.close()


def test_approval_api_flow() -> None:
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        hrbp_id = register_user(client, email='hrbp@example.com', role='hrbp')
        manager_id = register_user(client, email='manager@example.com', role='manager')
        register_user(client, email='employee@example.com', role='employee')
        bind_user_departments(context, email='hrbp@example.com', department_names=['Engineering'])
        bind_user_departments(context, email='manager@example.com', department_names=['Engineering'])
        admin_token = login_token(client, email='admin@example.com')
        hrbp_token = login_token(client, email='hrbp@example.com')
        manager_token = login_token(client, email='manager@example.com')
        outsider_token = login_token(client, email='employee@example.com')
        recommendation_id, evaluation_id = seed_recommendation(context)

        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'hr_review', 'approver_id': hrbp_id, 'comment': 'HRBP review'},
                    {'step_name': 'committee', 'approver_id': manager_id, 'comment': 'Committee review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201
        assert submit_response.json()['total'] == 2

        calibration_response = client.get(
            '/api/v1/approvals/calibration-queue',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert calibration_response.status_code == 200
        assert calibration_response.json()['items'][0]['evaluation_id'] == evaluation_id

        hrbp_queue = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {hrbp_token}'})
        assert hrbp_queue.status_code == 200
        assert hrbp_queue.json()['total'] == 1
        hrbp_approval_id = hrbp_queue.json()['items'][0]['id']

        forbidden_response = client.patch(
            f'/api/v1/approvals/{hrbp_approval_id}',
            json={'decision': 'approved', 'comment': 'Not my task.'},
            headers={'Authorization': f'Bearer {outsider_token}'},
        )
        assert forbidden_response.status_code == 403

        approve_response = client.patch(
            f'/api/v1/approvals/{hrbp_approval_id}',
            json={'decision': 'approved', 'comment': 'Looks good.'},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()['recommendation_status'] == 'pending_approval'

        manager_queue = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {manager_token}'})
        assert manager_queue.status_code == 200
        manager_approval_id = manager_queue.json()['items'][0]['id']

        reject_response = client.patch(
            f'/api/v1/approvals/{manager_approval_id}',
            json={'decision': 'rejected', 'comment': 'Need tighter budget.'},
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()['recommendation_status'] == 'rejected'

        history_response = client.get(
            f'/api/v1/approvals/recommendations/{recommendation_id}/history',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert history_response.status_code == 200
        assert history_response.json()['total'] == 2

        admin_queue = client.get(
            '/api/v1/approvals?include_all=true',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert admin_queue.status_code == 200
        assert admin_queue.json()['total'] == 2


def test_approval_api_hides_cross_department_records() -> None:
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        hrbp_id = register_user(client, email='hrbp@example.com', role='hrbp')
        bind_user_departments(context, email='hrbp@example.com', department_names=['Sales'])
        admin_token = login_token(client, email='admin@example.com')
        hrbp_token = login_token(client, email='hrbp@example.com')
        recommendation_id, _ = seed_recommendation(context)

        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [{'step_name': 'hr_review', 'approver_id': hrbp_id, 'comment': 'Cross department'}],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201

        queue_response = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {hrbp_token}'})
        assert queue_response.status_code == 200
        assert queue_response.json()['total'] == 0

        history_response = client.get(
            f'/api/v1/approvals/recommendations/{recommendation_id}/history',
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert history_response.status_code == 403


def test_default_approval_route_and_sequential_actions() -> None:
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        register_user(client, email='hrbp@example.com', role='hrbp')
        register_user(client, email='manager@example.com', role='manager')
        bind_user_departments(context, email='hrbp@example.com', department_names=['Engineering'])
        bind_user_departments(context, email='manager@example.com', department_names=['Engineering'])

        admin_token = login_token(client, email='admin@example.com')
        hrbp_token = login_token(client, email='hrbp@example.com')
        manager_token = login_token(client, email='manager@example.com')
        recommendation_id, _ = seed_recommendation(context)

        candidate_response = client.get(
            '/api/v1/approvals/submission-candidates',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert candidate_response.status_code == 200
        assert candidate_response.json()['total'] >= 1
        candidate = next(item for item in candidate_response.json()['items'] if item['recommendation_id'] == recommendation_id)
        assert len(candidate['route_preview']) == 2

        submit_response = client.post(
            f'/api/v1/approvals/submit-default/{recommendation_id}',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert submit_response.status_code == 201
        body = submit_response.json()
        assert body['total'] == 2
        assert body['items'][0]['step_order'] == 1
        assert body['items'][0]['is_current_step'] is True
        assert body['items'][1]['step_order'] == 2
        assert body['items'][1]['is_current_step'] is False

        admin_queue_before = client.get(
            '/api/v1/approvals',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        admin_second_step = next(item for item in admin_queue_before.json()['items'] if item['step_order'] == 2)
        blocked_response = client.patch(
            f"/api/v1/approvals/{admin_second_step['id']}",
            json={'decision': 'approved', 'comment': 'Trying too early.'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert blocked_response.status_code == 400
        blocked_message = blocked_response.json().get('detail') or blocked_response.json().get('message') or ''
        assert 'not actionable yet' in blocked_message

        hrbp_queue = client.get(
            '/api/v1/approvals',
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert hrbp_queue.status_code == 200
        first_step = hrbp_queue.json()['items'][0]
        assert first_step['is_current_step'] is True

        reject_without_comment = client.patch(
            f"/api/v1/approvals/{first_step['id']}",
            json={'decision': 'rejected', 'comment': ''},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert reject_without_comment.status_code == 400
        reject_message = reject_without_comment.json().get('detail') or reject_without_comment.json().get('message') or ''
        assert 'required' in reject_message

        approve_first = client.patch(
            f"/api/v1/approvals/{first_step['id']}",
            json={'decision': 'approved', 'comment': 'HRBP approved.'},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert approve_first.status_code == 200
        assert approve_first.json()['recommendation_status'] == 'pending_approval'

        admin_queue_after = client.get(
            '/api/v1/approvals',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        current_admin_step = next(item for item in admin_queue_after.json()['items'] if item['step_order'] == 2)
        assert current_admin_step['is_current_step'] is True

        approve_second = client.patch(
            f"/api/v1/approvals/{current_admin_step['id']}",
            json={'decision': 'approved', 'comment': 'Admin approved.'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert approve_second.status_code == 200
        assert approve_second.json()['recommendation_status'] == 'approved'


def test_approval_can_be_deferred_with_time_or_target_score() -> None:
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        register_user(client, email='hrbp@example.com', role='hrbp')
        register_user(client, email='manager@example.com', role='manager')
        bind_user_departments(context, email='hrbp@example.com', department_names=['Engineering'])
        bind_user_departments(context, email='manager@example.com', department_names=['Engineering'])

        hrbp_token = login_token(client, email='hrbp@example.com')
        manager_token = login_token(client, email='manager@example.com')
        recommendation_id, _ = seed_recommendation(context)

        submit_response = client.post(
            f'/api/v1/approvals/submit-default/{recommendation_id}',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert submit_response.status_code == 201
        first_step = next(item for item in submit_response.json()['items'] if item['step_order'] == 1)

        missing_condition = client.patch(
            f"/api/v1/approvals/{first_step['id']}",
            json={'decision': 'deferred', 'comment': 'Need more time.'},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert missing_condition.status_code == 400

        deferred_response = client.patch(
            f"/api/v1/approvals/{first_step['id']}",
            json={
                'decision': 'deferred',
                'comment': 'Wait for next milestone review.',
                'defer_until': '2026-04-15T00:00:00Z',
                'defer_target_score': 88,
            },
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert deferred_response.status_code == 200
        body = deferred_response.json()
        assert body['recommendation_status'] == 'deferred'
        assert body['defer_target_score'] == 88
        assert body['defer_reason'] == 'Wait for next milestone review.'

        history_response = client.get(
            f'/api/v1/approvals/recommendations/{recommendation_id}/history',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert history_response.status_code == 200
        history_item = next(item for item in history_response.json()['items'] if item['id'] == first_step['id'])
        assert history_item['decision'] == 'deferred'
        assert history_item['recommendation_status'] == 'deferred'

        candidates_response = client.get(
            '/api/v1/approvals/submission-candidates',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert candidates_response.status_code == 200
        candidate = next(item for item in candidates_response.json()['items'] if item['recommendation_id'] == recommendation_id)
        assert candidate['recommendation_status'] == 'deferred'
        assert candidate['defer_target_score'] == 88


def test_approval_route_can_be_updated_before_processing_starts() -> None:
    client, context = build_client()
    with client:
        admin_id = register_user(client, email='admin@example.com', role='admin')
        register_user(client, email='hrbp@example.com', role='hrbp')
        manager_id = register_user(client, email='manager@example.com', role='manager')
        bind_user_departments(context, email='hrbp@example.com', department_names=['Engineering'])
        bind_user_departments(context, email='manager@example.com', department_names=['Engineering'])

        admin_token = login_token(client, email='admin@example.com')
        manager_token = login_token(client, email='manager@example.com')
        recommendation_id, _ = seed_recommendation(context)

        submit_response = client.post(
            f'/api/v1/approvals/submit-default/{recommendation_id}',
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert submit_response.status_code == 201

        update_response = client.put(
            f'/api/v1/approvals/recommendations/{recommendation_id}',
            json={
                'steps': [
                    {'step_name': 'custom_review_1', 'approver_id': manager_id, 'comment': 'Manager first.'},
                    {'step_name': 'admin_final_review', 'approver_id': admin_id, 'comment': 'Admin final.'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert update_response.status_code == 200
        body = update_response.json()
        assert body['total'] == 2
        assert body['items'][0]['step_name'] == 'custom_review_1'
        assert body['items'][0]['approver_email'] == 'manager@example.com'
        assert body['items'][1]['approver_email'] == 'admin@example.com'

        candidates_response = client.get(
            '/api/v1/approvals/submission-candidates',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert candidates_response.status_code == 200
        candidate = next(item for item in candidates_response.json()['items'] if item['recommendation_id'] == recommendation_id)
        assert candidate['can_edit_route'] is True
        assert candidate['route_preview'][0].endswith('manager@example.com')


def test_resubmit_preserves_history() -> None:
    """APPR-02: After reject + resubmit, history must contain records from BOTH generations.

    This test FAILS until Plan 02 adds the generation column and preserves old records
    on resubmit. Expected failure: AssertionError on len(items) > 2.
    """
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        hrbp_id = register_user(client, email='hrbp@h.com', role='hrbp')
        manager_id = register_user(client, email='mgr@h.com', role='manager')
        bind_user_departments(context, email='hrbp@h.com', department_names=['Engineering'])
        bind_user_departments(context, email='mgr@h.com', department_names=['Engineering'])

        admin_token = login_token(client, email='admin@example.com')
        hrbp_token = login_token(client, email='hrbp@h.com')
        recommendation_id, _ = seed_recommendation(context)

        # Submit two-step approval
        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'hr_review', 'approver_id': hrbp_id, 'comment': 'HRBP review'},
                    {'step_name': 'committee', 'approver_id': manager_id, 'comment': 'Committee review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201

        # HRBP rejects step 1
        hrbp_queue = client.get('/api/v1/approvals', headers={'Authorization': f'Bearer {hrbp_token}'})
        assert hrbp_queue.status_code == 200
        hr_review_id = hrbp_queue.json()['items'][0]['id']

        reject_response = client.patch(
            f'/api/v1/approvals/{hr_review_id}',
            json={'decision': 'rejected', 'comment': 'Needs revision'},
            headers={'Authorization': f'Bearer {hrbp_token}'},
        )
        assert reject_response.status_code == 200

        # Admin resubmits the same recommendation with the same steps
        resubmit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'hr_review', 'approver_id': hrbp_id, 'comment': 'HRBP review'},
                    {'step_name': 'committee', 'approver_id': manager_id, 'comment': 'Committee review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resubmit_response.status_code == 201

        # History should contain records from BOTH generations (old rejected + new pending)
        history_response = client.get(
            f'/api/v1/approvals/recommendations/{recommendation_id}/history',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert history_response.status_code == 200
        items = history_response.json()['items']
        # FAILS until Plan 02 adds generation column and preserves old records on resubmit
        assert len(items) > 2


def test_manager_queue_has_dimension_scores() -> None:
    """APPR-05: Each approval queue item must include a dimension_scores key.

    This test FAILS until Plan 03 extends ApprovalRecordRead schema with dimension_scores.
    Expected failure: AssertionError or KeyError on 'dimension_scores' missing.
    """
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        manager_id = register_user(client, email='mgr2@h.com', role='manager')
        bind_user_departments(context, email='mgr2@h.com', department_names=['Engineering'])

        admin_token = login_token(client, email='admin@example.com')
        manager_token = login_token(client, email='mgr2@h.com')
        recommendation_id, _ = seed_recommendation(context)

        # Admin submits one-step approval with manager as approver
        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'manager_review', 'approver_id': manager_id, 'comment': 'Manager review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201

        # Manager lists pending approvals
        queue_response = client.get(
            '/api/v1/approvals',
            params={'decision': 'pending'},
            headers={'Authorization': f'Bearer {manager_token}'},
        )
        assert queue_response.status_code == 200
        items = queue_response.json()['items']
        assert len(items) >= 1

        first_item = items[0]
        # FAILS until Plan 03 extends the response schema with dimension_scores
        assert 'dimension_scores' in first_item


def test_hrbp_cross_department_queue() -> None:
    """APPR-06: HRBP with include_all=true should see all pending items regardless of department.

    The HRBP is assigned to Engineering; the seeded employee is also in Engineering.
    This test asserts that include_all=true surfaces items to HRBP even when the HRBP
    is not the designated approver. May PASS or FAIL depending on current scoping behavior —
    either outcome is acceptable as long as it runs without crash.
    """
    client, context = build_client()
    with client:
        register_user(client, email='admin@example.com', role='admin')
        hrbp1_id = register_user(client, email='hrbp1@h.com', role='hrbp')
        bind_user_departments(context, email='hrbp1@h.com', department_names=['Engineering'])

        admin_token = login_token(client, email='admin@example.com')
        hrbp1_token = login_token(client, email='hrbp1@h.com')
        recommendation_id, _ = seed_recommendation(context)

        # Admin submits one-step with hrbp1 as approver
        submit_response = client.post(
            '/api/v1/approvals/submit',
            json={
                'recommendation_id': recommendation_id,
                'steps': [
                    {'step_name': 'hr_review', 'approver_id': hrbp1_id, 'comment': 'HRBP1 review'},
                ],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert submit_response.status_code == 201

        # Admin sees all items with include_all=true
        admin_queue = client.get(
            '/api/v1/approvals?include_all=true',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert admin_queue.status_code == 200
        assert admin_queue.json()['total'] >= 1

        # HRBP with include_all=true should also see items from their department
        hrbp_queue = client.get(
            '/api/v1/approvals?include_all=true',
            headers={'Authorization': f'Bearer {hrbp1_token}'},
        )
        assert hrbp_queue.status_code == 200
        # FAILS until Plan 02/03 fix include_all scoping for HRBP role
        assert len(hrbp_queue.json()['items']) >= 1



