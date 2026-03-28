from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, func

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.certification import Certification
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
    database_path = (temp_root / f'cert-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def _seed_employee(db, employee_no: str = 'CERT-EMP-001', name: str = '认证测试员工') -> Employee:
    """Create test department and employee."""
    dept = db.scalar(select(Department).where(Department.name == '产品技术中心'))
    if dept is None:
        dept = Department(name='产品技术中心', description='test', status='active')
        db.add(dept)
        db.flush()
    emp = db.scalar(select(Employee).where(Employee.employee_no == employee_no))
    if emp is None:
        emp = Employee(
            employee_no=employee_no,
            name=name,
            department='产品技术中心',
            job_family='技术',
            job_level='P6',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
    return emp


# ---------------------------------------------------------------------------
# Certification import: SAVEPOINT partial success + missing employee + upsert
# ---------------------------------------------------------------------------


class TestCertificationSavepoint:
    """Certification import with SAVEPOINT partial success, missing employee reference,
    and upsert deduplication. Addresses review HIGH: certification import path clarity."""

    def test_missing_employee_reference_recorded_as_failure(self) -> None:
        """Certification CSV referencing non-existent employee_no:
        that row marked failed, valid rows still succeed."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_employee(db, 'CERT-EMP-001')
            csv = (
                '员工工号,认证类型,认证阶段,补贴比例,发证时间,到期时间\n'
                'CERT-EMP-001,AI基础认证,AI意识唤醒,0.02,2026-01-01T00:00:00+00:00,2027-01-01T00:00:00+00:00\n'
                'NONEXIST-999,AI基础认证,AI意识唤醒,0.02,2026-01-01T00:00:00+00:00,2027-01-01T00:00:00+00:00\n'
            ).encode('utf-8')
            upload = UploadStub('cert.csv', csv)
            service = ImportService(db)
            job = service.run_import(import_type='certifications', upload=upload)
            assert job.success_rows == 1, 'Valid certification row must succeed'
            assert job.failed_rows == 1, 'Missing employee reference must be recorded as failure'
            failed = [r for r in job.result_summary.get('rows', []) if r['status'] == 'failed']
            assert len(failed) == 1
            assert '未找到' in failed[0]['message'] or 'NONEXIST' in failed[0]['message']

    def test_certification_upsert_overwrites_existing(self) -> None:
        """Same employee + same certification_type imported twice:
        second import overwrites (updates), no duplicate rows."""
        session_factory = _make_test_db()
        with session_factory() as db:
            emp = _seed_employee(db, 'CERT-UPS-001')
            csv_v1 = (
                '员工工号,认证类型,认证阶段,补贴比例,发证时间,到期时间\n'
                'CERT-UPS-001,AI基础认证,AI意识唤醒,0.02,2026-01-01T00:00:00+00:00,2027-01-01T00:00:00+00:00\n'
            ).encode('utf-8')
            csv_v2 = (
                '员工工号,认证类型,认证阶段,补贴比例,发证时间,到期时间\n'
                'CERT-UPS-001,AI基础认证,AI技能应用,0.05,2026-06-01T00:00:00+00:00,2027-06-01T00:00:00+00:00\n'
            ).encode('utf-8')
            service = ImportService(db)
            service.run_import(import_type='certifications', upload=UploadStub('cv1.csv', csv_v1))
            service.run_import(import_type='certifications', upload=UploadStub('cv2.csv', csv_v2))
            # DB assertion: only 1 Certification record
            count = db.scalar(
                select(func.count()).select_from(Certification).where(
                    Certification.employee_id == emp.id,
                    Certification.certification_type == 'AI基础认证',
                )
            )
            assert count == 1, f'Expected 1 certification, got {count}'
            # DB assertion: updated to new stage and bonus_rate
            cert = db.scalar(select(Certification).where(
                Certification.employee_id == emp.id,
                Certification.certification_type == 'AI基础认证',
            ))
            assert cert.certification_stage == 'AI技能应用'
            assert cert.bonus_rate == 0.05

    def test_certification_partial_commit_with_mixed_rows(self) -> None:
        """Certification CSV: 2 valid rows (employee exists) + 1 invalid row (employee missing).
        Verify partial commit: 2 success, 1 failed."""
        session_factory = _make_test_db()
        with session_factory() as db:
            _seed_employee(db, 'CERT-MIX-001', '混合员工一')
            _seed_employee(db, 'CERT-MIX-002', '混合员工二')
            csv = (
                '员工工号,认证类型,认证阶段,补贴比例,发证时间,到期时间\n'
                'CERT-MIX-001,AI基础认证,AI意识唤醒,0.02,2026-01-01T00:00:00+00:00,2027-01-01T00:00:00+00:00\n'
                'CERT-MIX-002,AI应用认证,AI技能应用,0.05,2026-03-01T00:00:00+00:00,2027-03-01T00:00:00+00:00\n'
                'CERT-NOEXIST,AI基础认证,AI意识唤醒,0.02,2026-01-01T00:00:00+00:00,2027-01-01T00:00:00+00:00\n'
            ).encode('utf-8')
            upload = UploadStub('cert_mix.csv', csv)
            service = ImportService(db)
            job = service.run_import(import_type='certifications', upload=upload)
            assert job.success_rows == 2
            assert job.failed_rows == 1
            # DB assertion: 2 Certification records committed
            total_certs = db.scalar(select(func.count()).select_from(Certification))
            assert total_certs >= 2
