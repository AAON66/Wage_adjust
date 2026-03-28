from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, func

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.audit_log import AuditLog
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.services.import_service import ImportService


class UploadStub:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = io.BytesIO(content)


def _make_test_db():
    load_model_modules()
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'upsert-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def _seed_department(db, name: str = '产品技术中心') -> None:
    existing = db.scalar(select(Department).where(Department.name == name))
    if existing is None:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
        db.commit()


# ---------------------------------------------------------------------------
# IMP-05: employee_no upsert idempotency + audit logging
# ---------------------------------------------------------------------------


class TestEmployeeUpsert:
    """IMP-05: employee_no upsert is idempotent -- duplicate import does not create duplicates."""

    def test_second_import_updates_existing_employee(self) -> None:
        """Import EMP UPS-001, then import same employee_no with different name.
        DB must have exactly 1 record with updated name."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv_v1 = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nUPS-001,原始姓名,产品技术中心,技术,P6,active,\n'.encode('utf-8')
            csv_v2 = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nUPS-001,更新姓名,产品技术中心,技术,P7,active,\n'.encode('utf-8')

            service = ImportService(db)
            service.run_import(import_type='employees', upload=UploadStub('v1.csv', csv_v1))
            service.run_import(import_type='employees', upload=UploadStub('v2.csv', csv_v2))

            # DB assertion: only 1 record
            count = db.scalar(select(func.count()).select_from(Employee).where(Employee.employee_no == 'UPS-001'))
            assert count == 1, f'Expected 1 employee, got {count}'
            # DB assertion: name updated
            emp = db.scalar(select(Employee).where(Employee.employee_no == 'UPS-001'))
            assert emp.name == '更新姓名'

    def test_upsert_does_not_create_duplicate(self) -> None:
        """Import same file twice -- Employee table must not have duplicate rows."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nDUP-001,重复测试,产品技术中心,技术,P6,active,\n'.encode('utf-8')
            service = ImportService(db)
            service.run_import(import_type='employees', upload=UploadStub('dup1.csv', csv))
            service.run_import(import_type='employees', upload=UploadStub('dup2.csv', csv))
            count = db.scalar(select(func.count()).select_from(Employee).where(Employee.employee_no == 'DUP-001'))
            assert count == 1

    def test_upsert_writes_audit_log(self) -> None:
        """Import existing employee (update), verify AuditLog has 'employee_import_update' record
        with old_value and new_value in detail."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nAUD-001,审计原始,产品技术中心,技术,P6,active,\n'.encode('utf-8')
            csv_v2 = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nAUD-001,审计更新,产品技术中心,技术,P7,active,\n'.encode('utf-8')
            service = ImportService(db)
            service.run_import(import_type='employees', upload=UploadStub('aud1.csv', csv))
            service.run_import(import_type='employees', upload=UploadStub('aud2.csv', csv_v2))
            # DB assertion: audit log exists
            audit_count = db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == 'employee_import_update')
            )
            assert audit_count >= 1, 'Update operation must produce audit log'
            # DB assertion: audit log contains old_value and new_value
            audit = db.scalar(select(AuditLog).where(AuditLog.action == 'employee_import_update'))
            assert 'old_value' in str(audit.detail)
            assert 'new_value' in str(audit.detail)

    def test_new_employee_no_update_audit_log(self) -> None:
        """Import new employee (create), verify no 'employee_import_update' audit log is created."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv = '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\nNEW-001,新员工,产品技术中心,技术,P6,active,\n'.encode('utf-8')
            service = ImportService(db)
            service.run_import(import_type='employees', upload=UploadStub('new.csv', csv))
            audit_count = db.scalar(
                select(func.count()).select_from(AuditLog).where(
                    AuditLog.action == 'employee_import_update',
                    AuditLog.target_type == 'employee',
                )
            )
            assert audit_count == 0, 'New employee creation must NOT produce update audit log'
