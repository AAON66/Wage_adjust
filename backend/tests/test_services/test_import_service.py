from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.user import User
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


def seed_departments(db, *names: str) -> None:
    for name in names:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
    db.commit()


def test_import_service_imports_employees_and_certifications() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering', 'Product')
        service = ImportService(db)
        employee_csv = '\n'.join([
            'employee_no,name,id_card_no,department,sub_department,job_family,job_level,status,manager_employee_no',
            'EMP-1001,Alice Zhang,310101199001010123,Engineering,Backend Platform,Platform,P5,active,',
            'EMP-1002,Bob Li,310101199001010124,Product,Product Strategy,Product,P4,active,EMP-1001',
        ]).encode('utf-8')
        employee_job = service.run_import(import_type='employees', upload=UploadStub('employees.csv', employee_csv))
        assert employee_job.status == 'completed'
        assert employee_job.success_rows == 2

        bob = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1002'))
        assert bob is not None
        assert bob.manager_id is not None
        assert bob.id_card_no == '310101199001010124'
        assert bob.sub_department == 'Product Strategy'

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
        assert '员工工号' in template_bytes.decode('utf-8-sig')
        assert '身份证号' in template_bytes.decode('utf-8-sig')

        report_name, report_bytes, _ = service.build_export_report(cert_job)
        assert report_name.endswith('_report.csv')
        assert '认证信息导入成功。' in report_bytes.decode('utf-8-sig')
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
        assert '暂不支持直接读取 Excel' in job.result_summary['error']
    finally:
        db.close()


def test_import_service_supports_gb18030_and_chinese_headers() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        service = ImportService(db)
        employee_csv = '\n'.join([
            '员工工号,员工姓名,身份证号,所属部门,下属部门,岗位族,岗位级别,在职状态,直属上级工号',
            'EMP-1801,王小北,310101199001010128,Engineering,后端平台组,平台研发,P5,active,',
        ]).encode('gb18030')
        job = service.run_import(import_type='employees', upload=UploadStub('employees.csv', employee_csv))
        assert job.status == 'completed'
        created = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1801'))
        assert created is not None
        assert created.name == '王小北'
        assert created.id_card_no == '310101199001010128'
    finally:
        db.close()


def test_import_service_reports_missing_columns_and_unknown_department_in_chinese() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        service = ImportService(db)

        missing_column_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees.csv',
                '\n'.join([
                    '员工工号,员工姓名,身份证号,所属部门,下属部门,岗位族',
                    'EMP-1991,缺列用户,310101199001010129,Engineering,后端平台组,平台研发',
                ]).encode('utf-8-sig'),
            ),
        )
        assert missing_column_job.status == 'failed'
        assert '缺少必填列：岗位级别' in missing_column_job.result_summary['error']

        unknown_department_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees.csv',
                '\n'.join([
                    '员工工号,员工姓名,身份证号,所属部门,下属部门,岗位族,岗位级别,在职状态,直属上级工号',
                    'EMP-1992,部门不存在,310101199001010130,未创建部门,后端平台组,平台研发,P5,active,',
                ]).encode('utf-8-sig'),
            ),
        )
        assert unknown_department_job.status == 'failed'
        first_row = unknown_department_job.result_summary['rows'][0]
        assert '部门“未创建部门”未创建' in first_row['message']
    finally:
        db.close()


def test_import_service_can_delete_single_and_multiple_jobs() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering', 'Product')
        service = ImportService(db)
        first_job = service.run_import(
            import_type='employees',
            upload=UploadStub('employees.csv', '\n'.join([
                'employee_no,name,id_card_no,department,sub_department,job_family,job_level,status,manager_employee_no',
                'EMP-2001,Alice Zhang,310101199001010125,Engineering,Backend Platform,Platform,P5,active,',
            ]).encode('utf-8')),
        )
        second_job = service.run_import(
            import_type='employees',
            upload=UploadStub('employees2.csv', '\n'.join([
                'employee_no,name,id_card_no,department,sub_department,job_family,job_level,status,manager_employee_no',
                'EMP-2002,Bob Li,310101199001010126,Product,Product Strategy,Product,P4,active,',
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


def test_import_service_auto_binds_existing_user_by_id_card() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        db.add(
            User(
                email='employee@example.com',
                hashed_password='hashed',
                role='employee',
                id_card_no='310101199001010127',
                must_change_password=False,
            )
        )
        db.commit()

        service = ImportService(db)
        employee_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees.csv',
                '\n'.join([
                    'employee_no,name,id_card_no,department,sub_department,job_family,job_level,status,manager_employee_no',
                    'EMP-3001,Auto Match,310101199001010127,Engineering,Backend Platform,Platform,P5,active,',
                ]).encode('utf-8'),
            ),
        )
        assert employee_job.status == 'completed'

        employee = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-3001'))
        user = db.scalar(__import__('sqlalchemy').select(User).where(User.email == 'employee@example.com'))
        assert employee is not None
        assert user is not None
        assert user.employee_id == employee.id
    finally:
        db.close()
