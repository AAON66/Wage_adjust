from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, func

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
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
    database_path = (temp_root / f'partial-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def _seed_department(db, name: str = '产品技术中心') -> None:
    """Ensure the test department exists."""
    existing = db.scalar(select(Department).where(Department.name == name))
    if existing is None:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
        db.commit()


# ---------------------------------------------------------------------------
# IMP-01: Lazy validation -- collect all row-level errors, do not stop at first
# ---------------------------------------------------------------------------


class TestLazyValidation:
    """IMP-01: All row errors are collected and returned together, not stopped at first error."""

    def test_all_row_errors_collected_not_stopped_at_first(self) -> None:
        """3 rows with non-existent departments -- all 3 must appear in results."""
        session_factory = _make_test_db()
        with session_factory() as db:
            csv_content = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'BAD-001,张一,不存在部门A,技术,P6,active,\n'
                'BAD-002,李二,不存在部门B,技术,P7,active,\n'
                'BAD-003,王三,不存在部门C,产品,P5,active,\n'
            ).encode('utf-8')
            upload = UploadStub('bad.csv', csv_content)
            service = ImportService(db)
            job = service.run_import(import_type='employees', upload=upload)
            assert job.failed_rows == 3, f'Expected 3 failures, got {job.failed_rows}'
            failed_rows = [r for r in job.result_summary.get('rows', []) if r['status'] == 'failed']
            assert len(failed_rows) == 3, 'All 3 invalid rows must be collected'

    def test_mixed_valid_and_invalid_rows(self) -> None:
        """5 rows CSV: 3 valid + 2 invalid. Expect success_rows=3, failed_rows=2."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv_content = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'MIX-001,张有效一,产品技术中心,技术,P6,active,\n'
                'MIX-002,李无效一,不存在部门X,技术,P7,active,\n'
                'MIX-003,王有效二,产品技术中心,产品,P5,active,\n'
                'MIX-004,赵无效二,不存在部门Y,设计,P4,active,\n'
                'MIX-005,孙有效三,产品技术中心,技术,P8,active,\n'
            ).encode('utf-8')
            upload = UploadStub('mixed.csv', csv_content)
            service = ImportService(db)
            job = service.run_import(import_type='employees', upload=upload)
            assert job.success_rows == 3
            assert job.failed_rows == 2


# ---------------------------------------------------------------------------
# IMP-02: SAVEPOINT partial commit -- valid rows committed despite failures
# ---------------------------------------------------------------------------


class TestSavepointPartialCommit:
    """IMP-02: Valid rows are committed to DB even when other rows fail."""

    def test_valid_rows_committed_despite_failures(self) -> None:
        """Import 5 rows: 3 valid + 2 invalid. DB must have exactly 3 Employee records."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv_content = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'SP-001,张存活一,产品技术中心,技术,P6,active,\n'
                'SP-002,李失败一,不存在部门,技术,P7,active,\n'
                'SP-003,王存活二,产品技术中心,产品,P5,active,\n'
                'SP-004,赵失败二,不存在部门,设计,P4,active,\n'
                'SP-005,孙存活三,产品技术中心,技术,P8,active,\n'
            ).encode('utf-8')
            upload = UploadStub('savepoint.csv', csv_content)
            service = ImportService(db)
            service.run_import(import_type='employees', upload=upload)
            # DB assertion: 3 valid rows committed
            count = db.scalar(select(func.count()).select_from(Employee).where(
                Employee.employee_no.in_(['SP-001', 'SP-003', 'SP-005'])
            ))
            assert count == 3, f'Expected 3 committed employees, got {count}'
            # DB assertion: invalid rows NOT committed
            bad_count = db.scalar(select(func.count()).select_from(Employee).where(
                Employee.employee_no.in_(['SP-002', 'SP-004'])
            ))
            assert bad_count == 0, f'Expected 0 failed employees in DB, got {bad_count}'

    def test_savepoint_failure_does_not_corrupt_session(self) -> None:
        """3 rows: row 2 fails. Row 3 (after failure) must still be committed -- session not corrupted."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv_content = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'SESS-001,第一行正常,产品技术中心,技术,P6,active,\n'
                'SESS-002,第二行失败,不存在部门,技术,P7,active,\n'
                'SESS-003,第三行也正常,产品技术中心,产品,P5,active,\n'
            ).encode('utf-8')
            upload = UploadStub('session.csv', csv_content)
            service = ImportService(db)
            job = service.run_import(import_type='employees', upload=upload)
            assert job.success_rows == 2
            assert job.failed_rows == 1
            # Critical assertion: row 3 (after failed row 2) must be committed
            third = db.scalar(select(Employee).where(Employee.employee_no == 'SESS-003'))
            assert third is not None, 'Row after failure must be committed (session cleanup works)'

    def test_partial_commit_db_row_count_matches_success_count(self) -> None:
        """After importing mixed rows, total Employee count in DB matches success_rows from job."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_department(db)
            csv_content = (
                '员工工号,员工姓名,所属部门,岗位族,岗位级别,在职状态,身份证号\n'
                'RC-001,行数测试一,产品技术中心,技术,P6,active,\n'
                'RC-002,行数测试二,不存在部门,技术,P7,active,\n'
                'RC-003,行数测试三,产品技术中心,产品,P5,active,\n'
            ).encode('utf-8')
            upload = UploadStub('rowcount.csv', csv_content)
            service = ImportService(db)
            job = service.run_import(import_type='employees', upload=upload)
            total = db.scalar(select(func.count()).select_from(Employee))
            assert total == job.success_rows, f'DB row count {total} must match success_rows {job.success_rows}'
