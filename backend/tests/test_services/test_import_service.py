from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook
from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
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


def build_xlsx_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def seed_departments(db, *names: str) -> None:
    for name in names:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
    db.commit()


def seed_employee(
    db,
    *,
    employee_no: str,
    name: str = '绩效员工',
    department: str = 'Engineering',
) -> Employee:
    employee = Employee(
        employee_no=employee_no,
        name=name,
        department=department,
        job_family='Platform',
        job_level='P5',
        status='active',
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def test_import_service_imports_employees_and_certifications() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering', 'Product')
        service = ImportService(db)
        employee_csv = '\n'.join([
            'employee_no,name,id_card_no,department,sub_department,company,job_family,job_level,status,manager_employee_no',
            'EMP-1001,Alice Zhang,310101199001010123,Engineering,Backend Platform,Acme Group,Platform,P5,active,',
            'EMP-1002,Bob Li,310101199001010124,Product,Product Strategy,Beacon Labs,Product,P4,active,EMP-1001',
        ]).encode('utf-8')
        employee_job = service.run_import(import_type='employees', upload=UploadStub('employees.csv', employee_csv))
        assert employee_job.status == 'completed'
        assert employee_job.success_rows == 2

        bob = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1002'))
        assert bob is not None
        assert bob.manager_id is not None
        assert bob.company == 'Beacon Labs'
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
        assert '所属公司' in template_bytes.decode('utf-8-sig')

        report_name, report_bytes, _ = service.build_export_report(cert_job)
        assert report_name.endswith('_report.csv')
        assert '认证' in report_bytes.decode('utf-8-sig') and 'success' in report_bytes.decode('utf-8-sig')
    finally:
        db.close()


def test_import_service_rejects_invalid_xlsx() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        service = ImportService(db)
        upload = UploadStub('employees.xlsx', b'not-a-real-xlsx')
        job = service.run_import(import_type='employees', upload=upload)
        assert job.status == 'failed'
        # openpyxl now handles xlsx; an invalid file triggers a parse error
        assert job.result_summary.get('error') is not None
    finally:
        db.close()


def test_import_service_supports_gb18030_and_chinese_headers() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        service = ImportService(db)
        employee_csv = '\n'.join([
            '员工工号,员工姓名,身份证号,所属部门,下属部门,所属公司,岗位族,岗位级别,在职状态,直属上级工号',
            'EMP-1801,王小北,310101199001010128,Engineering,后端平台组,华东事业部,平台研发,P5,active,',
        ]).encode('gb18030')
        job = service.run_import(import_type='employees', upload=UploadStub('employees.csv', employee_csv))
        assert job.status == 'completed'
        created = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1801'))
        assert created is not None
        assert created.company == '华东事业部'
        assert created.name == '王小北'
        assert created.id_card_no == '310101199001010128'
    finally:
        db.close()


def test_import_service_company_column_can_clear_or_preserve_existing_value() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        service = ImportService(db)
        initial_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees.csv',
                '\n'.join([
                    'employee_no,name,id_card_no,department,sub_department,company,job_family,job_level,status,manager_employee_no',
                    'EMP-1901,Company User,310101199001010131,Engineering,Backend Platform,Legacy Co,Platform,P5,active,',
                ]).encode('utf-8'),
            ),
        )
        assert initial_job.status == 'completed'

        clear_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees-clear.csv',
                '\n'.join([
                    'employee_no,name,id_card_no,department,sub_department,company,job_family,job_level,status,manager_employee_no',
                    'EMP-1901,Company User,310101199001010131,Engineering,Backend Platform,   ,Platform,P5,active,',
                ]).encode('utf-8'),
            ),
        )
        assert clear_job.status == 'completed'
        employee = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1901'))
        assert employee is not None
        assert employee.company is None

        restore_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees-restore.csv',
                '\n'.join([
                    'employee_no,name,id_card_no,department,sub_department,company,job_family,job_level,status,manager_employee_no',
                    'EMP-1901,Company User,310101199001010131,Engineering,Backend Platform,  Acme Group  ,Platform,P5,active,',
                ]).encode('utf-8'),
            ),
        )
        assert restore_job.status == 'completed'

        preserve_job = service.run_import(
            import_type='employees',
            upload=UploadStub(
                'employees-preserve.csv',
                '\n'.join([
                    'employee_no,name,id_card_no,department,sub_department,job_family,job_level,status,manager_employee_no',
                    'EMP-1901,Company User Updated,310101199001010131,Engineering,Backend Platform,Platform,P5,active,',
                ]).encode('utf-8'),
            ),
        )
        assert preserve_job.status == 'completed'
        employee = db.scalar(__import__('sqlalchemy').select(Employee).where(Employee.employee_no == 'EMP-1901'))
        assert employee is not None
        assert employee.name == 'Company User Updated'
        assert employee.company == 'Acme Group'
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
        # With SAVEPOINT partial-success mode, single-row failure results in 'failed' status
        assert unknown_department_job.status == 'failed'
        first_row = unknown_department_job.result_summary['rows'][0]
        assert first_row['status'] == 'failed'
        assert '未创建部门' in first_row['message'] or '部门' in first_row['message']
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


def test_import_performance_grades_with_comment_header_persists_comment() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        seed_employee(db, employee_no='EMP-C001')
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级', '评语'],
                [['EMP-C001', 2025, 'A', '年度表现突出']],
            ),
        )
        job = service.run_import(import_type='performance_grades', upload=upload)

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C001',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.comment == '年度表现突出'
    finally:
        db.close()


def test_import_performance_grades_without_comment_column_defaults_to_none() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        seed_employee(db, employee_no='EMP-C002')
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级'],
                [['EMP-C002', 2025, 'B']],
            ),
        )
        job = service.run_import(import_type='performance_grades', upload=upload)

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C002',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.comment is None
    finally:
        db.close()


def test_import_performance_grades_with_english_comment_alias() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        seed_employee(db, employee_no='EMP-C003')
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级', 'comment'],
                [['EMP-C003', 2025, 'C', 'Needs stronger execution']],
            ),
        )
        job = service.run_import(import_type='performance_grades', upload=upload)

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C003',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.comment == 'Needs stronger execution'
    finally:
        db.close()


def test_import_performance_grades_with_note_alias() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        seed_employee(db, employee_no='EMP-C004')
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级', '备注'],
                [['EMP-C004', 2025, 'A', '备注字段写入评语']],
            ),
        )
        job = service.run_import(import_type='performance_grades', upload=upload)

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C004',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.comment == '备注字段写入评语'
    finally:
        db.close()


def test_import_performance_grades_merge_without_comment_column_keeps_existing() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        employee = seed_employee(db, employee_no='EMP-C005')
        db.add(
            PerformanceRecord(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                year=2025,
                grade='A',
                source='manual',
                department_snapshot=employee.department,
                comment='保留原评语',
            )
        )
        db.commit()
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级'],
                [['EMP-C005', 2025, 'B']],
            ),
        )
        job = service.run_import(
            import_type='performance_grades',
            upload=upload,
            overwrite_mode='merge',
        )

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C005',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.grade == 'B'
        assert record.comment == '保留原评语'
    finally:
        db.close()


def test_import_performance_grades_merge_with_comment_column_updates_existing() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        seed_departments(db, 'Engineering')
        employee = seed_employee(db, employee_no='EMP-C006')
        db.add(
            PerformanceRecord(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                year=2025,
                grade='A',
                source='manual',
                department_snapshot=employee.department,
                comment=None,
            )
        )
        db.commit()
        service = ImportService(db)

        upload = UploadStub(
            'performance_grades.xlsx',
            build_xlsx_bytes(
                ['员工工号', '年度', '绩效等级', '评语'],
                [['EMP-C006', 2025, 'B', '评语A']],
            ),
        )
        job = service.run_import(
            import_type='performance_grades',
            upload=upload,
            overwrite_mode='merge',
        )

        assert job.status == 'completed'
        record = db.scalar(
            __import__('sqlalchemy').select(PerformanceRecord).where(
                PerformanceRecord.employee_no == 'EMP-C006',
                PerformanceRecord.year == 2025,
            )
        )
        assert record is not None
        assert record.grade == 'B'
        assert record.comment == '评语A'
    finally:
        db.close()
