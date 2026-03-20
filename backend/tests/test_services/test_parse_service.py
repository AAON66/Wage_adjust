from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.services.parse_service import ParseService


def build_context() -> tuple[Settings, object]:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'parse-{uuid4().hex}.db').as_posix()
    uploads_path = (temp_root / f'uploads-{uuid4().hex}').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}', storage_base_dir=uploads_path)
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def test_parse_service_extracts_evidence_from_markdown_file() -> None:
    settings, session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-2001',
            name='Parser User',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='1000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='submitted')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        storage_dir = Path(settings.storage_base_dir).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)
        submission_dir = storage_dir / submission.id
        submission_dir.mkdir(parents=True, exist_ok=True)
        target_file = submission_dir / 'notes.md'
        target_file.write_text('# Impact\nDelivered AI workflow improvements.', encoding='utf-8')

        uploaded_file = UploadedFile(
            submission_id=submission.id,
            file_name='notes.md',
            file_type='md',
            storage_key=f'{submission.id}/notes.md',
            parse_status='pending',
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        service = ParseService(db, settings)
        parsed_file, evidence_count = service.parse_file(uploaded_file)

        assert parsed_file.parse_status == 'parsed'
        assert evidence_count == 1
        assert len(submission.evidence_items) == 1
        assert 'Delivered AI workflow improvements.' in submission.evidence_items[0].content
    finally:
        db.close()
