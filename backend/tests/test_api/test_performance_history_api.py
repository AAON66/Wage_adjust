from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.user import User
from backend.tests.test_api.test_salary_api import (
    ApiDatabaseContext,
    bind_user_departments,
    build_client,
    register_and_login_user,
)


def _bind_user_employee(
    context: ApiDatabaseContext,
    *,
    email: str,
    employee_id: str,
) -> None:
    db = context.session_factory()
    try:
        user = db.query(User).filter(User.email == email).one()
        user.employee_id = employee_id
        db.add(user)
        db.commit()
    finally:
        db.close()


def _seed_history_context() -> tuple[TestClient, ApiDatabaseContext, dict[str, str]]:
    client, context = build_client()

    admin_token = register_and_login_user(
        client,
        email='admin-history@example.com',
        role='admin',
    )
    hrbp_token = register_and_login_user(
        client,
        email='hrbp-history@example.com',
        role='hrbp',
    )
    manager_a_token = register_and_login_user(
        client,
        email='manager-a-history@example.com',
        role='manager',
    )
    manager_b_token = register_and_login_user(
        client,
        email='manager-b-history@example.com',
        role='manager',
    )
    employee_token = register_and_login_user(
        client,
        email='employee-history@example.com',
        role='employee',
    )

    bind_user_departments(
        context,
        email='hrbp-history@example.com',
        department_names=['Dept-A', 'Dept-B'],
    )
    bind_user_departments(
        context,
        email='manager-a-history@example.com',
        department_names=['Dept-A'],
    )
    bind_user_departments(
        context,
        email='manager-b-history@example.com',
        department_names=['Dept-B'],
    )

    db = context.session_factory()
    try:
        emp_a = Employee(
            employee_no='EMP-HIS-001',
            name='员工A',
            department='Dept-A',
            job_family='Engineering',
            job_level='P6',
            status='active',
        )
        emp_b = Employee(
            employee_no='EMP-HIS-002',
            name='员工B',
            department='Dept-B',
            job_family='Sales',
            job_level='P5',
            status='active',
        )
        emp_c = Employee(
            employee_no='EMP-HIS-003',
            name='员工C',
            department='Dept-A',
            job_family='Engineering',
            job_level='P4',
            status='active',
        )
        db.add_all([emp_a, emp_b, emp_c])
        db.commit()
        db.refresh(emp_a)
        db.refresh(emp_b)
        db.refresh(emp_c)

        db.add_all([
            PerformanceRecord(
                employee_id=emp_a.id,
                employee_no=emp_a.employee_no,
                year=2026,
                grade='A',
                source='manual',
                department_snapshot='Dept-A',
                comment='Q4 优秀',
            ),
            PerformanceRecord(
                employee_id=emp_a.id,
                employee_no=emp_a.employee_no,
                year=2025,
                grade='B',
                source='manual',
                department_snapshot='Dept-A',
                comment=None,
            ),
            PerformanceRecord(
                employee_id=emp_b.id,
                employee_no=emp_b.employee_no,
                year=2026,
                grade='C',
                source='manual',
                department_snapshot='Dept-B',
                comment='待提升',
            ),
        ])
        db.commit()
        emp_a_id = emp_a.id
        emp_b_id = emp_b.id
        emp_c_id = emp_c.id
    finally:
        db.close()

    _bind_user_employee(
        context,
        email='employee-history@example.com',
        employee_id=emp_a_id,
    )

    return client, context, {
        'admin': admin_token,
        'hrbp': hrbp_token,
        'manager_a': manager_a_token,
        'manager_b': manager_b_token,
        'employee': employee_token,
        'emp_a_id': emp_a_id,
        'emp_b_id': emp_b_id,
        'emp_c_id': emp_c_id,
    }


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_performance_history_admin_returns_items_year_desc() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_a_id']}",
            headers=_auth_headers(seeded['admin']),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body['items']) == 2
    assert body['items'][0]['year'] > body['items'][1]['year']
    assert 'comment' in body['items'][0]
    assert 'department_snapshot' in body['items'][0]


def test_performance_history_hrbp_returns_items() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_a_id']}",
            headers=_auth_headers(seeded['hrbp']),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body['items']) == 2
    assert body['items'][0]['year'] > body['items'][1]['year']
    assert 'comment' in body['items'][0]
    assert 'department_snapshot' in body['items'][0]


def test_performance_history_manager_same_department_returns_items() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_a_id']}",
            headers=_auth_headers(seeded['manager_a']),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body['items']) == 2
    assert body['items'][0]['year'] > body['items'][1]['year']
    assert 'comment' in body['items'][0]
    assert 'department_snapshot' in body['items'][0]


def test_performance_history_manager_cross_department_returns_403() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_b_id']}",
            headers=_auth_headers(seeded['manager_a']),
        )

    assert response.status_code == 403
    assert '无权查看该员工的历史绩效' in response.text


def test_performance_history_employee_role_returns_403() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_a_id']}",
            headers=_auth_headers(seeded['employee']),
        )

    assert response.status_code == 403


def test_performance_history_unauthenticated_returns_401() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_a_id']}",
        )

    assert response.status_code == 401


def test_performance_history_nonexistent_employee_returns_404() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{uuid4()}",
            headers=_auth_headers(seeded['admin']),
        )

    assert response.status_code == 404
    assert '员工不存在' in response.text


def test_performance_history_empty_records_returns_empty_items_200() -> None:
    client, _context, seeded = _seed_history_context()
    with client:
        response = client.get(
            f"/api/v1/performance/records/by-employee/{seeded['emp_c_id']}",
            headers=_auth_headers(seeded['admin']),
        )

    assert response.status_code == 200
    assert response.json() == {'items': []}
