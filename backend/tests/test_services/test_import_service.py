from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.services.import_service import ImportService


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'import-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


class UploadStub:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = __import__('io').BytesIO(content)


def test_import_service_imports_employees_and_certifications() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        employee_csv = '\n'.join([
            'employee_no,name,department,job_family,job_level,status,manager_employee_no',
            'EMP-1001,Alice Zhang,Engineering,Platform,P5,active,',
            'EMP-1002,Bob Li,Product,Product,P4,active,EMP-1001',
        ]).encode('utf-8')
        employee_job = service.run_import(import_type='employees', upload=UploadStub('employees.csv', employee_csv))
        assert employee_job.status == 'completed'
        assert employee_job.success_rows == 2

        bob = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1002'))
        assert bob is not None
        assert bob.manager_id is not None

        cert_csv = '\n'.join([
            'employee_no,certification_type,certification_stage,bonus_rate,issued_at,expires_at',
            'EMP-1001,ai_skill,advanced,0.02,2026-01-15T00:00:00+00:00,',
        ]).encode('utf-8')
        cert_job = service.run_import(import_type='certifications', upload=UploadStub('certifications.csv', cert_csv))
        assert cert_job.status == 'completed'
        assert cert_job.success_rows == 1

        template_name, template_bytes, media_type = service.build_template('employees')
        assert template_name == 'employees_template.csv'
        assert media_type.startswith('text/csv')
        assert b'employee_no' in template_bytes

        report_name, report_bytes, _ = service.build_export_report(cert_job)
        assert report_name.endswith('_report.csv')
        assert b'Certification imported.' in report_bytes
    finally:
        db.close()


def test_import_service_rejects_xlsx_without_dependency() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        upload = UploadStub('employees.xlsx', b'not-a-real-xlsx')
        job = service.run_import(import_type='employees', upload=upload)
        assert job.status == 'failed'
        assert 'openpyxl' in job.result_summary['error']
    finally:
        db.close()


def test_import_service_can_delete_single_and_multiple_jobs() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        first_job = service.run_import(
            import_type='employees',
            upload=UploadStub('employees.csv', '\n'.join([
                'employee_no,name,department,job_family,job_level,status,manager_employee_no',
                'EMP-2001,Alice Zhang,Engineering,Platform,P5,active,',
            ]).encode('utf-8')),
        )
        second_job = service.run_import(
            import_type='employees',
            upload=UploadStub('employees2.csv', '\n'.join([
                'employee_no,name,department,job_family,job_level,status,manager_employee_no',
                'EMP-2002,Bob Li,Product,Product,P4,active,',
            ]).encode('utf-8')),
        )

        deleted_job_id = service.delete_job(first_job.id)
        assert deleted_job_id == first_job.id
        assert service.get_job(first_job.id) is None

        deleted_job_ids = service.bulk_delete_jobs([second_job.id, 'missing-job-id'])
        assert deleted_job_ids == [second_job.id]
        assert service.get_job(second_job.id) is None
    finally:
        db.close()
