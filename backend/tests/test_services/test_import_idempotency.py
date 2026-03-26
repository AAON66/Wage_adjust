from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.certification import Certification
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.services.import_service import ImportService


def _make_test_db():
    load_model_modules()
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'idempotency-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


class UploadStub:
    def __init__(self, content: str, filename: str = 'cert.csv') -> None:
        self.filename = filename
        self.file = io.BytesIO(content.encode('utf-8-sig'))


def _setup_db_with_employee(session_factory):
    with session_factory() as db:
        dept = Department(name='Engineering', status='active')
        db.add(dept)
        db.flush()
        emp = Employee(
            employee_no='EMP-001',
            name='Test Employee',
            department='Engineering',
            job_family='Engineering',
            job_level='P5',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return emp.id


def test_importing_same_certification_twice_creates_one_row() -> None:
    """Importing a certification CSV twice results in exactly 1 Certification row, not 2."""
    SessionLocal = _make_test_db()
    emp_id = _setup_db_with_employee(SessionLocal)

    csv_content = '员工工号,认证类型,认证阶段,补贴比例,发证时间\nEMP-001,ai_skill,advanced,0.02,2026-01-15T00:00:00+00:00\n'

    with SessionLocal() as db:
        service = ImportService(db)
        service.run_import(import_type='certifications', upload=UploadStub(csv_content))

    with SessionLocal() as db:
        service = ImportService(db)
        service.run_import(import_type='certifications', upload=UploadStub(csv_content))

    with SessionLocal() as db:
        rows = list(db.scalars(select(Certification).where(Certification.employee_id == emp_id)))
        assert len(rows) == 1, f'Expected 1 row after double import, got {len(rows)}'


def test_certification_import_returns_success_on_second_import() -> None:
    """Second import of the same certification returns status='success' (not error)."""
    SessionLocal = _make_test_db()
    _setup_db_with_employee(SessionLocal)

    csv_content = '员工工号,认证类型,认证阶段,补贴比例,发证时间\nEMP-001,ai_skill,advanced,0.02,2026-01-15T00:00:00+00:00\n'

    with SessionLocal() as db:
        service = ImportService(db)
        service.run_import(import_type='certifications', upload=UploadStub(csv_content))

    with SessionLocal() as db:
        service = ImportService(db)
        job = service.run_import(import_type='certifications', upload=UploadStub(csv_content))

    rows = job.result_summary.get('rows', [])
    assert len(rows) == 1
    assert rows[0]['status'] == 'success'


def test_different_certification_type_creates_new_row() -> None:
    """Importing a second certification with a different type for the same employee creates a new row."""
    SessionLocal = _make_test_db()
    _setup_db_with_employee(SessionLocal)

    csv1 = '员工工号,认证类型,认证阶段,补贴比例,发证时间\nEMP-001,ai_skill,advanced,0.02,2026-01-15T00:00:00+00:00\n'
    csv2 = '员工工号,认证类型,认证阶段,补贴比例,发证时间\nEMP-001,data_skill,intermediate,0.03,2026-02-01T00:00:00+00:00\n'

    with SessionLocal() as db:
        service = ImportService(db)
        service.run_import(import_type='certifications', upload=UploadStub(csv1))

    with SessionLocal() as db:
        service = ImportService(db)
        service.run_import(import_type='certifications', upload=UploadStub(csv2))

    with SessionLocal() as db:
        rows = list(db.scalars(select(Certification)))
        assert len(rows) == 2, f'Expected 2 rows (different types), got {len(rows)}'
