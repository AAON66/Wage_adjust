from __future__ import annotations

import csv
import io
import logging

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.certification import Certification
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.import_job import ImportJob
from backend.app.services.identity_binding_service import IdentityBindingService

logger = logging.getLogger(__name__)


class ImportService:
    SUPPORTED_TYPES = {'employees', 'certifications'}
    MAX_ROWS = 5000  # D-06: 单次导入最大行数
    REQUIRED_COLUMNS = {
        'employees': ['employee_no', 'name', 'department', 'job_family', 'job_level'],
        'certifications': ['employee_no', 'certification_type', 'certification_stage', 'bonus_rate', 'issued_at'],
    }
    COLUMN_ALIASES = {
        'employees': {
            '员工工号': 'employee_no',
            '员工姓名': 'name',
            '身份证号': 'id_card_no',
            '所属部门': 'department',
            '下属部门': 'sub_department',
            '岗位族': 'job_family',
            '岗位级别': 'job_level',
            '在职状态': 'status',
            '直属上级工号': 'manager_employee_no',
        },
        'certifications': {
            '员工工号': 'employee_no',
            '认证类型': 'certification_type',
            '认证阶段': 'certification_stage',
            '补贴比例': 'bonus_rate',
            '发证时间': 'issued_at',
            '到期时间': 'expires_at',
        },
    }
    COLUMN_LABELS = {
        'employee_no': '员工工号',
        'name': '员工姓名',
        'id_card_no': '身份证号',
        'department': '所属部门',
        'sub_department': '下属部门',
        'job_family': '岗位族',
        'job_level': '岗位级别',
        'status': '在职状态',
        'manager_employee_no': '直属上级工号',
        'certification_type': '认证类型',
        'certification_stage': '认证阶段',
        'bonus_rate': '补贴比例',
        'issued_at': '发证时间',
        'expires_at': '到期时间',
    }

    def __init__(
        self,
        db: Session,
        *,
        operator_id: str | None = None,
        operator_role: str | None = None,
    ):
        self.db = db
        self._operator_id = operator_id
        self._operator_role = operator_role

    def _label_for_column(self, column_name: str) -> str:
        return self.COLUMN_LABELS.get(column_name, column_name)

    def _localize_error_message(self, message: str) -> str:
        mapping = {
            'Unsupported import type.': '暂不支持这个导入类型。',
            'Uploaded file is empty.': '上传文件为空，请重新选择文件后再导入。',
            'Import job not found.': '未找到这条导入任务记录。',
            'Unsupported file format. Please upload CSV for now.': '当前只支持导入 CSV 文件，请先把文件另存为 CSV 后再试。',
            'Excel import requires openpyxl in the current environment. Please upload CSV for now.': '当前环境暂不支持直接读取 Excel，请先另存为 CSV 后再导入。',
            'CSV 文件读取失败。': '文件读取失败，请检查文件内容后重试。',
            'Required employee fields cannot be empty.': '员工工号、员工姓名、所属部门、岗位族、岗位级别不能为空。',
            'Employee imported.': '导入成功。',
            'Certification imported.': '认证信息导入成功。',
            'Invalid certification date or bonus rate.': '认证信息格式不正确，请检查发证时间、到期时间或补贴比例。',
            'This ID card number is already used by another employee profile.': '该身份证号已被其他员工档案占用。',
            'This ID card number is already used by another account.': '该身份证号已被其他平台账号占用。',
            'This employee profile is already bound to another account.': '该员工档案已绑定其他平台账号。',
        }
        if message in mapping:
            return mapping[message]
        if message.startswith('Department ') and message.endswith(' was not found.'):
            department_name = message[len('Department '):-len(' was not found.')]
            return f'部门"{department_name}"未创建，请先到部门管理中新增。'
        if message.startswith('Department ') and message.endswith(' is inactive.'):
            department_name = message[len('Department '):-len(' is inactive.')]
            return f'部门"{department_name}"已停用，请启用后再导入。'
        return message

    def _resolve_department_name(self, department_name: str) -> str:
        normalized_name = department_name.strip()
        department = self.db.scalar(select(Department).where(Department.name == normalized_name))
        if department is None:
            raise ValueError(f'Department {normalized_name} was not found.')
        if department.status != 'active':
            raise ValueError(f'Department {normalized_name} is inactive.')
        return department.name

    def list_jobs(self) -> list[ImportJob]:
        query = select(ImportJob).order_by(ImportJob.created_at.desc())
        return list(self.db.scalars(query))

    def get_job(self, job_id: str) -> ImportJob | None:
        return self.db.get(ImportJob, job_id)

    def delete_job(self, job_id: str) -> str:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError('Import job not found.')
        self.db.delete(job)
        self.db.commit()
        return job_id

    def bulk_delete_jobs(self, job_ids: list[str]) -> list[str]:
        deleted_ids: list[str] = []
        for job_id in job_ids:
            job = self.get_job(job_id)
            if job is None:
                continue
            self.db.delete(job)
            deleted_ids.append(job_id)
        self.db.commit()
        return deleted_ids

    def run_import(self, *, import_type: str, upload: UploadFile) -> ImportJob:
        normalized_type = import_type.strip().lower()
        if normalized_type not in self.SUPPORTED_TYPES:
            raise ValueError(self._localize_error_message('Unsupported import type.'))
        file_name = upload.filename or f'{normalized_type}.csv'
        raw_bytes = upload.file.read()
        if not raw_bytes:
            raise ValueError(self._localize_error_message('Uploaded file is empty.'))

        job = ImportJob(
            file_name=file_name,
            import_type=normalized_type,
            status='processing',
            total_rows=0,
            success_rows=0,
            failed_rows=0,
            result_summary={'rows': []},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        try:
            dataframe = self._load_table(file_name, raw_bytes)
            # D-06: 单次导入不能超过 MAX_ROWS 行
            if len(dataframe) > self.MAX_ROWS:
                raise ValueError(f'单次导入不能超过 {self.MAX_ROWS} 行，请分批导入。')
            row_results = self._dispatch_import(normalized_type, dataframe)
            job.total_rows = len(row_results)
            job.success_rows = sum(1 for item in row_results if item['status'] == 'success')
            job.failed_rows = sum(1 for item in row_results if item['status'] == 'failed')
            job.result_summary = {
                'rows': row_results,
                'supported_types': sorted(self.SUPPORTED_TYPES),
            }
            # Status: 'partial' when mixed, 'failed' when all fail, 'completed' when all succeed
            if job.failed_rows == 0:
                job.status = 'completed'
            elif job.success_rows == 0:
                job.status = 'failed'
            else:
                job.status = 'partial'
        except Exception as exc:
            job.status = 'failed'
            job.result_summary = {
                'rows': [],
                'error': self._localize_error_message(str(exc)),
                'supported_types': sorted(self.SUPPORTED_TYPES),
            }
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def build_template(self, import_type: str) -> tuple[str, bytes, str]:
        normalized_type = import_type.strip().lower()
        if normalized_type not in self.SUPPORTED_TYPES:
            raise ValueError(self._localize_error_message('Unsupported import type.'))
        output = io.StringIO()
        writer = csv.writer(output)
        if normalized_type == 'employees':
            writer.writerow(['员工工号', '员工姓名', '身份证号', '所属部门', '下属部门', '岗位族', '岗位级别', '在职状态', '直属上级工号'])
            writer.writerow(['EMP-1001', '张小明', '310101199001010123', '产品技术中心', '后端平台组', '平台研发', 'P5', 'active', ''])
        else:
            writer.writerow(['员工工号', '认证类型', '认证阶段', '补贴比例', '发证时间', '到期时间'])
            writer.writerow(['EMP-1001', 'ai_skill', 'advanced', '0.02', '2026-01-15T00:00:00+00:00', ''])
        # UTF-8 BOM helps Excel on Windows open Chinese CSVs correctly.
        content = output.getvalue().encode('utf-8-sig')
        return f'{normalized_type}_template.csv', content, 'text/csv; charset=utf-8'

    def build_template_xlsx(self, import_type: str) -> tuple[str, bytes, str]:
        """Build an xlsx template file for the given import type (IMP-06, D-04)."""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        normalized_type = import_type.strip().lower()
        if normalized_type not in self.SUPPORTED_TYPES:
            raise ValueError(self._localize_error_message('Unsupported import type.'))

        wb = Workbook()
        ws = wb.active
        ws.title = '导入模板'

        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center')

        if normalized_type == 'employees':
            headers = ['员工工号', '员工姓名', '身份证号', '所属部门', '下属部门', '岗位族', '岗位级别', '在职状态', '直属上级工号']
            example = ['EMP-1001', '张小明', '310101199001010123', '产品技术中心', '后端平台组', '平台研发', 'P5', 'active', '']
        else:
            headers = ['员工工号', '认证类型', '认证阶段', '补贴比例', '发证时间', '到期时间']
            example = ['EMP-1001', 'ai_skill', 'advanced', '0.02', '2026-01-15T00:00:00+00:00', '']

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        for col_idx, value in enumerate(example, start=1):
            ws.cell(row=2, column=col_idx, value=value)

        # Set column widths
        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else 'A'].width = 20

        # Properly set column widths for all columns
        from openpyxl.utils import get_column_letter
        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 20

        buf = io.BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return f'{normalized_type}_template.xlsx', content, media_type

    def build_export_report(self, job: ImportJob) -> tuple[str, bytes, str]:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['行号', '结果', '提示'])
        rows = job.result_summary.get('rows', []) if isinstance(job.result_summary, dict) else []
        for item in rows:
            writer.writerow([item.get('row_index', ''), item.get('status', ''), item.get('message', '')])
        if not rows:
            writer.writerow([
                '',
                'failed',
                job.result_summary.get('error', '当前没有可导出的行级结果。') if isinstance(job.result_summary, dict) else '当前没有可导出的行级结果。',
            ])
        content = output.getvalue().encode('utf-8-sig')
        return f'{job.import_type}_{job.id}_report.csv', content, 'text/csv; charset=utf-8'

    def build_export_report_xlsx(self, job: ImportJob) -> tuple[str, bytes, str]:
        """Build an xlsx error report for a completed import job (D-02)."""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = '导入结果报告'

        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center')

        headers = ['行号', '结果', '错误字段', '错误原因']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        rows = job.result_summary.get('rows', []) if isinstance(job.result_summary, dict) else []
        # Only include failed rows in the report
        row_num = 2
        for item in rows:
            if item.get('status') != 'failed':
                continue
            ws.cell(row=row_num, column=1, value=item.get('row_index', ''))
            ws.cell(row=row_num, column=2, value=item.get('status', ''))
            ws.cell(row=row_num, column=3, value=item.get('error_column', ''))
            ws.cell(row=row_num, column=4, value=item.get('message', ''))
            row_num += 1

        if row_num == 2:
            # No failed rows — write a summary row
            error_msg = ''
            if isinstance(job.result_summary, dict):
                error_msg = job.result_summary.get('error', '当前没有失败行。')
            else:
                error_msg = '当前没有失败行。'
            ws.cell(row=2, column=1, value='')
            ws.cell(row=2, column=2, value='info')
            ws.cell(row=2, column=3, value='')
            ws.cell(row=2, column=4, value=error_msg)

        from openpyxl.utils import get_column_letter
        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 20

        buf = io.BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return f'{job.import_type}_{job.id}_report.xlsx', content, media_type

    def _load_table(self, file_name: str, raw_bytes: bytes) -> pd.DataFrame:
        suffix = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
        if suffix == 'csv':
            last_error: Exception | None = None
            for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk'):
                try:
                    return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding).fillna('')
                except UnicodeDecodeError as exc:
                    last_error = exc
            if last_error is not None:
                raise ValueError('CSV 文件编码格式不正确，请使用"CSV UTF-8"或 GBK/GB18030 编码重新保存后再导入。') from last_error
            raise ValueError(self._localize_error_message('CSV 文件读取失败。'))
        if suffix in {'xlsx', 'xls'}:
            # IMP-04: xlsx/xls support via openpyxl
            return pd.read_excel(io.BytesIO(raw_bytes), engine='openpyxl').fillna('')
        raise ValueError(self._localize_error_message('Unsupported file format. Please upload CSV for now.'))

    def _dispatch_import(self, import_type: str, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        dataframe = self._normalize_columns(import_type, dataframe)
        required = self.REQUIRED_COLUMNS[import_type]
        missing = [column for column in required if column not in dataframe.columns]
        if missing:
            missing_labels = '、'.join(self._label_for_column(column) for column in missing)
            raise ValueError(f'缺少必填列：{missing_labels}。请重新下载最新模板后填写。')
        if import_type == 'employees':
            return self._import_employees(dataframe)
        return self._import_certifications(dataframe)

    def _normalize_columns(self, import_type: str, dataframe: pd.DataFrame) -> pd.DataFrame:
        alias_map = self.COLUMN_ALIASES.get(import_type, {})
        normalized_columns: dict[str, str] = {}
        for column in dataframe.columns:
            stripped = str(column).strip()
            normalized_columns[column] = alias_map.get(stripped, stripped)
        return dataframe.rename(columns=normalized_columns)

    def _detect_error_column(self, exc: Exception) -> str:
        """Detect which column caused the employee import error based on exception message."""
        msg = str(exc)
        if '不能为空' in msg or 'cannot be empty' in msg.lower():
            return '必填字段'
        if '部门' in msg and ('未创建' in msg or 'not found' in msg.lower() or '停用' in msg):
            return '所属部门'
        if '身份证号' in msg or 'id_card' in msg.lower() or 'ID card' in msg:
            return '身份证号'
        if '员工工号' in msg or 'employee_no' in msg.lower():
            return '员工工号'
        return ''

    def _detect_cert_error_column(self, exc: Exception) -> str:
        """Detect which column caused the certification import error based on exception message."""
        msg = str(exc)
        if '员工工号' in msg or '未找到' in msg:
            return '员工工号'
        if '日期' in msg or '时间' in msg or 'datetime' in msg.lower() or 'date' in msg.lower():
            return '发证时间/到期时间'
        if '补贴' in msg or 'bonus_rate' in msg.lower() or 'float' in msg.lower():
            return '补贴比例'
        return ''

    def _import_employees(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        staged_rows: list[tuple[Employee, str | None]] = []
        identity_service = IdentityBindingService(self.db)
        for index, row in dataframe.iterrows():
            try:
                with self.db.begin_nested():  # SAVEPOINT
                    employee_no = str(row['employee_no']).strip()
                    name = str(row['name']).strip()
                    id_card_no = str(row['id_card_no']).strip() if 'id_card_no' in dataframe.columns else ''
                    department = str(row['department']).strip()
                    sub_department = str(row['sub_department']).strip() if 'sub_department' in dataframe.columns else ''
                    job_family = str(row['job_family']).strip()
                    job_level = str(row['job_level']).strip()
                    status_val = str(row['status']).strip() or 'active'
                    manager_no = str(row['manager_employee_no']).strip() if 'manager_employee_no' in dataframe.columns else ''
                    if not all([employee_no, name, department, job_family, job_level]):
                        raise ValueError(self._localize_error_message('Required employee fields cannot be empty.'))

                    employee = self.db.scalar(select(Employee).where(Employee.employee_no == employee_no))
                    # employee_no has DB-level unique constraint + index, upsert is reliable
                    department = self._resolve_department_name(department)
                    normalized_id_card_no = identity_service.ensure_employee_id_card_available(
                        id_card_no or None,
                        employee_id=employee.id if employee is not None else None,
                    )

                    if employee is None:
                        employee = Employee(
                            employee_no=employee_no,
                            name=name,
                            id_card_no=normalized_id_card_no,
                            department=department,
                            sub_department=sub_department or None,
                            job_family=job_family,
                            job_level=job_level,
                            status=status_val,
                        )
                    else:
                        # D-03/IMP-05: Record old values for audit log before updating
                        old_values = {
                            'name': employee.name,
                            'department': employee.department,
                            'job_family': employee.job_family,
                            'job_level': employee.job_level,
                            'status': employee.status,
                        }
                        employee.name = name
                        employee.id_card_no = normalized_id_card_no
                        employee.department = department
                        employee.sub_department = sub_department or None
                        employee.job_family = job_family
                        employee.job_level = job_level
                        employee.status = status_val
                        # Write audit log for employee update
                        audit_entry = AuditLog(
                            operator_id=self._operator_id,
                            action='employee_import_update',
                            target_type='employee',
                            target_id=employee.id,
                            detail={
                                'old_value': old_values,
                                'new_value': {
                                    'name': name,
                                    'department': department,
                                    'job_family': job_family,
                                    'job_level': job_level,
                                    'status': status_val,
                                },
                                'operator_role': self._operator_role,
                            },
                        )
                        self.db.add(audit_entry)

                    self.db.add(employee)
                    self.db.flush()

                    bind_warning: str | None = None
                    try:
                        identity_service.auto_bind_user_and_employee(employee=employee)
                    except ValueError as exc:
                        bind_warning = self._localize_error_message(str(exc))

                staged_rows.append((employee, manager_no or None))
                success_message = self._localize_error_message('Employee imported.')
                if bind_warning:
                    success_message = f'{success_message} 但自动绑定账号失败：{bind_warning}'
                results.append({'row_index': int(index) + 1, 'status': 'success', 'message': success_message})
            except Exception as exc:
                self.db.expire_all()  # Clean stale objects after SAVEPOINT rollback
                results.append({
                    'row_index': int(index) + 1,
                    'status': 'failed',
                    'message': self._localize_error_message(str(exc)),
                    'error_column': self._detect_error_column(exc),
                })

        # Second pass: manager binding with SAVEPOINT per row
        for employee, manager_no in staged_rows:
            try:
                with self.db.begin_nested():  # SAVEPOINT for manager binding
                    if not manager_no:
                        employee.manager_id = None
                        self.db.add(employee)
                    else:
                        manager = self.db.scalar(select(Employee).where(Employee.employee_no == manager_no))
                        if manager is None:
                            employee.manager_id = None
                            results.append({
                                'row_index': None,
                                'status': 'failed',
                                'message': f'未找到直属上级工号"{manager_no}"，员工 {employee.employee_no} 已跳过上级绑定。',
                                'error_column': '直属上级工号',
                            })
                        else:
                            employee.manager_id = manager.id
                            self.db.add(employee)
            except Exception as exc:
                self.db.expire_all()  # Clean stale objects after SAVEPOINT rollback
                results.append({
                    'row_index': None,
                    'status': 'failed',
                    'message': f'上级绑定失败：{exc!s}',
                    'error_column': '直属上级工号',
                })

        self.db.commit()
        return results

    def _import_certifications(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for index, row in dataframe.iterrows():
            try:
                with self.db.begin_nested():  # SAVEPOINT
                    employee_no = str(row['employee_no']).strip()
                    employee = self.db.scalar(select(Employee).where(Employee.employee_no == employee_no))
                    if employee is None:
                        raise ValueError(f'未找到员工工号"{employee_no}"，请先导入员工档案。')

                    try:
                        issued_at = pd.to_datetime(row['issued_at'], utc=True).to_pydatetime()
                        expires_value = str(row['expires_at']).strip() if 'expires_at' in dataframe.columns else ''
                        expires_at = pd.to_datetime(expires_value, utc=True).to_pydatetime() if expires_value else None
                        bonus_rate = float(row['bonus_rate'])
                    except Exception:
                        raise ValueError(self._localize_error_message('Invalid certification date or bonus rate.'))

                    certification_type = str(row['certification_type']).strip()
                    # Upsert on (employee_id, certification_type)
                    existing = self.db.scalar(
                        select(Certification).where(
                            Certification.employee_id == employee.id,
                            Certification.certification_type == certification_type,
                        )
                    )
                    if existing is not None:
                        existing.certification_stage = str(row['certification_stage']).strip()
                        existing.bonus_rate = bonus_rate
                        existing.issued_at = issued_at
                        existing.expires_at = expires_at
                        self.db.add(existing)
                    else:
                        certification = Certification(
                            employee_id=employee.id,
                            certification_type=certification_type,
                            certification_stage=str(row['certification_stage']).strip(),
                            bonus_rate=bonus_rate,
                            issued_at=issued_at,
                            expires_at=expires_at,
                        )
                        self.db.add(certification)
                    self.db.flush()
                results.append({'row_index': int(index) + 1, 'status': 'success', 'message': '认证导入成功。'})
            except Exception as exc:
                self.db.expire_all()  # Clean stale objects after SAVEPOINT rollback
                results.append({
                    'row_index': int(index) + 1,
                    'status': 'failed',
                    'message': self._localize_error_message(str(exc)),
                    'error_column': self._detect_cert_error_column(exc),
                })
        self.db.commit()
        return results
