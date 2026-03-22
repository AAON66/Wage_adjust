from __future__ import annotations

import csv
import io

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.certification import Certification
from backend.app.models.employee import Employee
from backend.app.models.import_job import ImportJob


class ImportService:
    SUPPORTED_TYPES = {'employees', 'certifications'}
    REQUIRED_COLUMNS = {
        'employees': ['employee_no', 'name', 'department', 'job_family', 'job_level'],
        'certifications': ['employee_no', 'certification_type', 'certification_stage', 'bonus_rate', 'issued_at'],
    }

    def __init__(self, db: Session):
        self.db = db

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
            raise ValueError('Unsupported import type.')
        file_name = upload.filename or f'{normalized_type}.csv'
        raw_bytes = upload.file.read()
        if not raw_bytes:
            raise ValueError('Uploaded file is empty.')

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
            row_results = self._dispatch_import(normalized_type, dataframe)
            job.total_rows = len(row_results)
            job.success_rows = sum(1 for item in row_results if item['status'] == 'success')
            job.failed_rows = sum(1 for item in row_results if item['status'] == 'failed')
            job.result_summary = {
                'rows': row_results,
                'supported_types': sorted(self.SUPPORTED_TYPES),
            }
            job.status = 'completed' if job.failed_rows == 0 else ('failed' if job.success_rows == 0 else 'completed')
        except Exception as exc:
            job.status = 'failed'
            job.result_summary = {
                'rows': [],
                'error': str(exc),
                'supported_types': sorted(self.SUPPORTED_TYPES),
            }
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def build_template(self, import_type: str) -> tuple[str, bytes, str]:
        normalized_type = import_type.strip().lower()
        if normalized_type not in self.SUPPORTED_TYPES:
            raise ValueError('Unsupported import type.')
        output = io.StringIO()
        writer = csv.writer(output)
        if normalized_type == 'employees':
            writer.writerow(['employee_no', 'name', 'department', 'job_family', 'job_level', 'status', 'manager_employee_no'])
            writer.writerow(['EMP-1001', 'Alice Zhang', 'Engineering', 'Platform', 'P5', 'active', ''])
        else:
            writer.writerow(['employee_no', 'certification_type', 'certification_stage', 'bonus_rate', 'issued_at', 'expires_at'])
            writer.writerow(['EMP-1001', 'ai_skill', 'advanced', '0.02', '2026-01-15T00:00:00+00:00', ''])
        content = output.getvalue().encode('utf-8')
        return f'{normalized_type}_template.csv', content, 'text/csv; charset=utf-8'

    def build_export_report(self, job: ImportJob) -> tuple[str, bytes, str]:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['row_index', 'status', 'message'])
        rows = job.result_summary.get('rows', []) if isinstance(job.result_summary, dict) else []
        for item in rows:
            writer.writerow([item.get('row_index', ''), item.get('status', ''), item.get('message', '')])
        if not rows:
            writer.writerow(['', 'failed', job.result_summary.get('error', 'No row details available.') if isinstance(job.result_summary, dict) else 'No row details available.'])
        content = output.getvalue().encode('utf-8')
        return f'{job.import_type}_{job.id}_report.csv', content, 'text/csv; charset=utf-8'

    def _load_table(self, file_name: str, raw_bytes: bytes) -> pd.DataFrame:
        suffix = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
        if suffix == 'csv':
            return pd.read_csv(io.BytesIO(raw_bytes)).fillna('')
        if suffix in {'xlsx', 'xls'}:
            raise ValueError('Excel import requires openpyxl in the current environment. Please upload CSV for now.')
        raise ValueError('Unsupported file format. Please upload CSV for now.')

    def _dispatch_import(self, import_type: str, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        required = self.REQUIRED_COLUMNS[import_type]
        missing = [column for column in required if column not in dataframe.columns]
        if missing:
            raise ValueError(f'Missing required columns: {", ".join(missing)}')
        if import_type == 'employees':
            return self._import_employees(dataframe)
        return self._import_certifications(dataframe)

    def _import_employees(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        staged_rows: list[tuple[Employee, str | None]] = []
        for index, row in dataframe.iterrows():
            employee_no = str(row['employee_no']).strip()
            name = str(row['name']).strip()
            department = str(row['department']).strip()
            job_family = str(row['job_family']).strip()
            job_level = str(row['job_level']).strip()
            status = str(row['status']).strip() or 'active'
            manager_no = str(row['manager_employee_no']).strip() if 'manager_employee_no' in dataframe.columns else ''
            if not all([employee_no, name, department, job_family, job_level]):
                results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': 'Required employee fields cannot be empty.'})
                continue
            employee = self.db.scalar(select(Employee).where(Employee.employee_no == employee_no))
            if employee is None:
                employee = Employee(
                    employee_no=employee_no,
                    name=name,
                    department=department,
                    job_family=job_family,
                    job_level=job_level,
                    status=status,
                )
            else:
                employee.name = name
                employee.department = department
                employee.job_family = job_family
                employee.job_level = job_level
                employee.status = status
            self.db.add(employee)
            self.db.flush()
            staged_rows.append((employee, manager_no or None))
            results.append({'row_index': int(index) + 1, 'status': 'success', 'message': 'Employee imported.'})

        for employee, manager_no in staged_rows:
            if not manager_no:
                employee.manager_id = None
                self.db.add(employee)
                continue
            manager = self.db.scalar(select(Employee).where(Employee.employee_no == manager_no))
            if manager is None:
                employee.manager_id = None
                results.append({'row_index': None, 'status': 'failed', 'message': f'Manager {manager_no} was not found for {employee.employee_no}.'})
                continue
            employee.manager_id = manager.id
            self.db.add(employee)
        self.db.commit()
        return results

    def _import_certifications(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for index, row in dataframe.iterrows():
            employee_no = str(row['employee_no']).strip()
            employee = self.db.scalar(select(Employee).where(Employee.employee_no == employee_no))
            if employee is None:
                results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': f'Employee {employee_no} was not found.'})
                continue
            try:
                issued_at = pd.to_datetime(row['issued_at'], utc=True).to_pydatetime()
                expires_value = str(row['expires_at']).strip() if 'expires_at' in dataframe.columns else ''
                expires_at = pd.to_datetime(expires_value, utc=True).to_pydatetime() if expires_value else None
                bonus_rate = float(row['bonus_rate'])
            except Exception:
                results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': 'Invalid certification date or bonus rate.'})
                continue
            certification = Certification(
                employee_id=employee.id,
                certification_type=str(row['certification_type']).strip(),
                certification_stage=str(row['certification_stage']).strip(),
                bonus_rate=bonus_rate,
                issued_at=issued_at,
                expires_at=expires_at,
            )
            self.db.add(certification)
            results.append({'row_index': int(index) + 1, 'status': 'success', 'message': 'Certification imported.'})
        self.db.commit()
        return results
