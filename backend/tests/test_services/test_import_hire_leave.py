from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.services.import_service import ImportService


def build_context():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'import-hire-leave-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


class UploadStub:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = __import__('io').BytesIO(content)


def seed_employee(db, emp_no: str = 'EMP-1001', name: str = 'Alice') -> Employee:
    dept = db.scalar(__import__('sqlalchemy').select(Department).where(Department.name == 'Engineering'))
    if dept is None:
        dept = Department(name='Engineering', description='Eng', status='active')
        db.add(dept)
        db.flush()
    emp = Employee(employee_no=emp_no, name=name, department='Engineering', job_family='Platform', job_level='P5')
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


# ------------------------------------------------------------------
# Test 1: SUPPORTED_TYPES includes hire_info and non_statutory_leave
# ------------------------------------------------------------------

def test_supported_types_include_new_types() -> None:
    assert 'hire_info' in ImportService.SUPPORTED_TYPES
    assert 'non_statutory_leave' in ImportService.SUPPORTED_TYPES


# ------------------------------------------------------------------
# Test 2: _import_hire_info updates employee hire_date
# ------------------------------------------------------------------

def test_import_hire_info_success() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        emp = seed_employee(db)
        service = ImportService(db)
        csv_content = 'employee_no,hire_date\nEMP-1001,2024-03-15\n'.encode('utf-8')
        job = service.run_import(import_type='hire_info', upload=UploadStub('hire.csv', csv_content))
        assert job.status == 'completed'
        assert job.success_rows == 1
        db.refresh(emp)
        assert emp.hire_date is not None
        assert str(emp.hire_date) == '2024-03-15'
    finally:
        db.close()


# ------------------------------------------------------------------
# Test 3: _import_hire_info fails for unknown employee_no
# ------------------------------------------------------------------

def test_import_hire_info_unknown_employee() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        csv_content = 'employee_no,hire_date\nNONEXIST-999,2024-01-01\n'.encode('utf-8')
        job = service.run_import(import_type='hire_info', upload=UploadStub('hire.csv', csv_content))
        assert job.failed_rows == 1
        rows = job.result_summary.get('rows', [])
        assert any('未找到' in r.get('message', '') for r in rows)
    finally:
        db.close()


# ------------------------------------------------------------------
# Test 4: _import_non_statutory_leave creates NonStatutoryLeave record
# ------------------------------------------------------------------

def test_import_non_statutory_leave_success() -> None:
    from backend.app.models.non_statutory_leave import NonStatutoryLeave
    import sqlalchemy

    session_factory = build_context()
    db = session_factory()
    try:
        emp = seed_employee(db)
        service = ImportService(db)
        csv_content = 'employee_no,year,total_days\nEMP-1001,2025,5.5\n'.encode('utf-8')
        job = service.run_import(import_type='non_statutory_leave', upload=UploadStub('leave.csv', csv_content))
        assert job.status == 'completed'
        assert job.success_rows == 1

        record = db.scalar(
            sqlalchemy.select(NonStatutoryLeave).where(
                NonStatutoryLeave.employee_id == emp.id,
                NonStatutoryLeave.year == 2025,
            )
        )
        assert record is not None
        assert float(record.total_days) == 5.5
        assert record.source == 'excel'
    finally:
        db.close()


# ------------------------------------------------------------------
# Test 5: _import_non_statutory_leave upsert on (employee_id, year)
# ------------------------------------------------------------------

def test_import_non_statutory_leave_upsert() -> None:
    from backend.app.models.non_statutory_leave import NonStatutoryLeave
    import sqlalchemy

    session_factory = build_context()
    db = session_factory()
    try:
        emp = seed_employee(db)
        service = ImportService(db)

        # First import
        csv1 = 'employee_no,year,total_days\nEMP-1001,2025,3.0\n'.encode('utf-8')
        service.run_import(import_type='non_statutory_leave', upload=UploadStub('leave.csv', csv1))

        # Second import (upsert)
        csv2 = 'employee_no,year,total_days\nEMP-1001,2025,7.5\n'.encode('utf-8')
        job2 = service.run_import(import_type='non_statutory_leave', upload=UploadStub('leave2.csv', csv2))
        assert job2.status == 'completed'

        # Verify only one record exists with updated value
        records = list(db.scalars(
            sqlalchemy.select(NonStatutoryLeave).where(
                NonStatutoryLeave.employee_id == emp.id,
                NonStatutoryLeave.year == 2025,
            )
        ))
        assert len(records) == 1
        assert float(records[0].total_days) == 7.5
    finally:
        db.close()


# ------------------------------------------------------------------
# Test 6: _import_non_statutory_leave handles optional leave_type
# ------------------------------------------------------------------

def test_import_non_statutory_leave_optional_leave_type() -> None:
    from backend.app.models.non_statutory_leave import NonStatutoryLeave
    import sqlalchemy

    session_factory = build_context()
    db = session_factory()
    try:
        emp = seed_employee(db)
        service = ImportService(db)

        # With leave_type
        csv1 = 'employee_no,year,total_days,leave_type\nEMP-1001,2025,2.0,事假\n'.encode('utf-8')
        job1 = service.run_import(import_type='non_statutory_leave', upload=UploadStub('leave.csv', csv1))
        assert job1.status == 'completed'
        record = db.scalar(
            sqlalchemy.select(NonStatutoryLeave).where(NonStatutoryLeave.employee_id == emp.id)
        )
        assert record.leave_type == '事假'

        # Without leave_type (empty)
        csv2 = 'employee_no,year,total_days,leave_type\nEMP-1001,2024,1.0,\n'.encode('utf-8')
        job2 = service.run_import(import_type='non_statutory_leave', upload=UploadStub('leave2.csv', csv2))
        assert job2.status == 'completed'
        record2 = db.scalar(
            sqlalchemy.select(NonStatutoryLeave).where(
                NonStatutoryLeave.employee_id == emp.id,
                NonStatutoryLeave.year == 2024,
            )
        )
        assert record2.leave_type is None
    finally:
        db.close()


# ------------------------------------------------------------------
# Test 7: build_template and build_template_xlsx support new types
# ------------------------------------------------------------------

def test_build_template_hire_info() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        name, content, media = service.build_template('hire_info')
        assert name == 'hire_info_template.csv'
        decoded = content.decode('utf-8-sig')
        assert '员工工号' in decoded
        assert '入职日期' in decoded
    finally:
        db.close()


def test_build_template_non_statutory_leave() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        name, content, media = service.build_template('non_statutory_leave')
        assert name == 'non_statutory_leave_template.csv'
        decoded = content.decode('utf-8-sig')
        assert '员工工号' in decoded
        assert '假期天数' in decoded
    finally:
        db.close()


def test_build_template_xlsx_hire_info() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        name, content, media = service.build_template_xlsx('hire_info')
        assert name == 'hire_info_template.xlsx'
        assert len(content) > 0
    finally:
        db.close()


def test_build_template_xlsx_non_statutory_leave() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        name, content, media = service.build_template_xlsx('non_statutory_leave')
        assert name == 'non_statutory_leave_template.xlsx'
        assert len(content) > 0
    finally:
        db.close()
