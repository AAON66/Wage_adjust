from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.schemas.employee import EmployeeCreate
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



def test_create_and_list_employees() -> None:
    db = build_session()
    service = EmployeeService(db)
    created = service.create_employee(
        EmployeeCreate(
            employee_no='E001',
            name='Alice',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
    )

    items, total = service.get_employees(page=1, page_size=10, department='Engineering')

    assert created.employee_no == 'E001'
    assert total == 1
    assert items[0].name == 'Alice'



def test_duplicate_employee_number_is_rejected() -> None:
    db = build_session()
    service = EmployeeService(db)
    payload = EmployeeCreate(
        employee_no='E002',
        name='Bob',
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
