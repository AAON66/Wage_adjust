from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.services.parse_service import ParseService


class ExplodingParser:
    def parse(self, path: Path):
        raise RuntimeError('boom')


def build_context() -> tuple[Settings, object]:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'parse-{uuid4().hex}.db').as_posix()
    uploads_path = (temp_root / f'uploads-{uuid4().hex}').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        storage_base_dir=uploads_path,
        deepseek_api_key='your_deepseek_api_key',
    )
    settings.deepseek_require_real_call_for_parsing = False
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def seed_submission_with_file() -> tuple[Settings, object, EmployeeSubmission, UploadedFile, Path]:
    settings, session_factory = build_context()
    db = session_factory()
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
    return settings, db, submission, uploaded_file, target_file


def seed_submission_with_zip_file() -> tuple[Settings, object, EmployeeSubmission, UploadedFile, Path]:
    settings, session_factory = build_context()
    db = session_factory()
    employee = Employee(
        employee_no='EMP-2002',
        name='Archive User',
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
    target_file = submission_dir / 'repo.zip'
    with ZipFile(target_file, 'w') as archive:
        archive.writestr('Wage_adjust-main/README.md', '# Wage Adjust\nRepository for salary automation insights.\n')
        archive.writestr('Wage_adjust-main/backend/service.py', 'def summarize():\n    return "AI automation improved salary review efficiency"\n')
        archive.writestr('Wage_adjust-main/docs/impact.txt', 'Impact: reduced manual review time by 35 percent.\n')

    uploaded_file = UploadedFile(
        submission_id=submission.id,
        file_name='repo.zip',
        file_type='zip',
        storage_key=f'{submission.id}/repo.zip',
        parse_status='pending',
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)
    return settings, db, submission, uploaded_file, target_file


def test_parse_service_extracts_evidence_from_markdown_file() -> None:
    settings, db, submission, uploaded_file, _ = seed_submission_with_file()
    try:
        service = ParseService(db, settings)
        parsed_file, evidence_count = service.parse_file(uploaded_file)

        db.refresh(submission)
        assert parsed_file.parse_status == 'parsed'
        assert evidence_count == 1
        assert len(submission.evidence_items) == 1
        assert 'Delivered AI workflow improvements.' in submission.evidence_items[0].content
    finally:
        db.close()


def test_parse_service_reparses_existing_file_and_refreshes_evidence() -> None:
    settings, db, submission, uploaded_file, target_file = seed_submission_with_file()
    try:
        service = ParseService(db, settings)
        service.parse_file(uploaded_file)

        target_file.write_text('# Impact\nSecond version with refreshed evidence.', encoding='utf-8')
        refreshed_file = db.get(UploadedFile, uploaded_file.id)
        assert refreshed_file is not None

        updated_files, evidence_count = service.parse_submission_files([refreshed_file])

        db.expire_all()
        refreshed_submission = db.get(EmployeeSubmission, submission.id)
        assert refreshed_submission is not None
        assert updated_files[0].parse_status == 'parsed'
        assert evidence_count == 1
        assert len(refreshed_submission.evidence_items) == 1
        assert 'Second version with refreshed evidence.' in refreshed_submission.evidence_items[0].content
    finally:
        db.close()


def test_parse_service_removes_stale_evidence_when_reparse_fails() -> None:
    settings, db, submission, uploaded_file, _ = seed_submission_with_file()
    try:
        service = ParseService(db, settings)
        service.parse_file(uploaded_file)
        service._pick_parser = lambda path: ExplodingParser()  # type: ignore[method-assign]

        refreshed_file = db.get(UploadedFile, uploaded_file.id)
        assert refreshed_file is not None
        parsed_file, evidence_count = service.parse_file(refreshed_file)

        db.expire_all()
        refreshed_submission = db.get(EmployeeSubmission, submission.id)
        assert refreshed_submission is not None
        assert parsed_file.parse_status == 'failed'
        assert evidence_count == 0
        assert len(refreshed_submission.evidence_items) == 0
    finally:
        db.close()


def test_parse_service_extracts_repository_content_from_zip_file() -> None:
    settings, db, submission, uploaded_file, _ = seed_submission_with_zip_file()
    try:
        service = ParseService(db, settings)
        parsed_file, evidence_count = service.parse_file(uploaded_file)

        db.refresh(submission)
        assert parsed_file.parse_status == 'parsed'
        assert evidence_count == 3
        assert len(submission.evidence_items) == 3
        contents = [item.content for item in submission.evidence_items]
        assert any('salary review efficiency' in content for content in contents)
        assert any('35 percent' in content for content in contents)
        assert any(item.metadata_json['archive_member_path'].endswith('README.md') for item in submission.evidence_items)
        assert any(item.metadata_json['archive_member_path'].endswith('service.py') for item in submission.evidence_items)
        assert any(item.metadata_json['archive_member_path'].endswith('impact.txt') for item in submission.evidence_items)
    finally:
        db.close()


def test_parse_service_reparse_refreshes_zip_repository_evidence() -> None:
    settings, db, submission, uploaded_file, target_file = seed_submission_with_zip_file()
    try:
        service = ParseService(db, settings)
        service.parse_file(uploaded_file)

        with ZipFile(target_file, 'w') as archive:
            archive.writestr('Wage_adjust-main/README.md', '# Wage Adjust\nUpdated repository summary.\n')
            archive.writestr('Wage_adjust-main/backend/service.py', 'def summarize():\n    return "AI parser now reads repository source files"\n')
            archive.writestr('Wage_adjust-main/docs/impact.txt', 'Impact: evidence quality improved after archive parsing.\n')

        refreshed_file = db.get(UploadedFile, uploaded_file.id)
        assert refreshed_file is not None

        parsed_file, evidence_count = service.parse_file(refreshed_file)

        db.expire_all()
        refreshed_submission = db.get(EmployeeSubmission, submission.id)
        assert refreshed_submission is not None
        assert parsed_file.parse_status == 'parsed'
        assert evidence_count == 3
        assert len(refreshed_submission.evidence_items) == 3
        contents = [item.content for item in refreshed_submission.evidence_items]
        assert any('archive parsing' in content for content in contents)
        assert not any('salary review efficiency' in content for content in contents)
    finally:
        db.close()
