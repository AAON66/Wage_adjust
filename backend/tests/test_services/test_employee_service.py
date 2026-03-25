from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.user import User
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate
from backend.app.services.employee_service import EmployeeService


def build_session() -> Session:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'service-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)()


def seed_departments(db: Session, *names: str) -> None:
    for name in names:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
    db.commit()



def test_create_and_list_employees() -> None:
    db = build_session()
    seed_departments(db, 'Engineering')
    service = EmployeeService(db)
    created = service.create_employee(
        EmployeeCreate(
            employee_no='E001',
            name='Alice',
            id_card_no='310101199001010123',
            department='Engineering',
            sub_department='Backend Platform',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
    )

    items, total = service.get_employees(page=1, page_size=10, department='Engineering')

    assert created.employee_no == 'E001'
    assert created.id_card_no == '310101199001010123'
    assert created.sub_department == 'Backend Platform'
    assert total == 1
    assert items[0].name == 'Alice'



def test_duplicate_employee_number_is_rejected() -> None:
    db = build_session()
    seed_departments(db, 'HR')
    service = EmployeeService(db)
    payload = EmployeeCreate(
        employee_no='E002',
        name='Bob',
        id_card_no='310101199001010124',
        department='HR',
        job_family='People',
        job_level='P4',
        status='active',
    )
    service.create_employee(payload)

    try:
        service.create_employee(payload)
    except ValueError as exc:
        assert str(exc) == 'Employee number already exists.'
    else:
        raise AssertionError('Expected duplicate employee number to raise ValueError.')


def test_unknown_department_is_rejected() -> None:
    db = build_session()
    service = EmployeeService(db)
    try:
        service.create_employee(
            EmployeeCreate(
                employee_no='E003',
                name='Cara',
                id_card_no='310101199001010125',
                department='Unknown',
                job_family='Platform',
                job_level='P5',
                status='active',
            )
        )
    except ValueError as exc:
        assert str(exc) == 'Department not found. Please create it in department management first.'
    else:
        raise AssertionError('Expected missing department to raise ValueError.')


def test_employee_auto_binds_existing_user_by_id_card() -> None:
    db = build_session()
    seed_departments(db, 'Engineering')
    user = User(
        email='employee@example.com',
        hashed_password='hashed',
        role='employee',
        id_card_no='310101199001010126',
        must_change_password=False,
    )
    db.add(user)
    db.commit()

    service = EmployeeService(db)
    created = service.create_employee(
        EmployeeCreate(
            employee_no='E004',
            name='Dylan',
            id_card_no='310101199001010126',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
    )

    db.refresh(user)
    assert user.employee_id == created.id


def test_update_employee_changes_profile_fields() -> None:
    db = build_session()
    seed_departments(db, 'Engineering', 'Sales')
    service = EmployeeService(db)
    created = service.create_employee(
        EmployeeCreate(
            employee_no='E005',
            name='Erin',
            id_card_no='310101199001010127',
            department='Engineering',
            sub_department='Backend Platform',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
    )

    updated = service.update_employee(
        created.id,
        EmployeeUpdate(
            employee_no='E005-UPDATED',
            name='Erin Updated',
            id_card_no='310101199001010128',
            department='Sales',
            sub_department='Commercial Ops',
            job_family='Business',
            job_level='P6',
            status='inactive',
        ),
    )

    assert updated is not None
    assert updated.employee_no == 'E005-UPDATED'
    assert updated.name == 'Erin Updated'
    assert updated.department == 'Sales'
    assert updated.sub_department == 'Commercial Ops'
    assert updated.job_family == 'Business'
    assert updated.job_level == 'P6'
    assert updated.status == 'inactive'
    assert updated.id_card_no == '310101199001010128'
