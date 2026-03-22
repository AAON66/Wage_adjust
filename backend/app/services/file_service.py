from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile

ALLOWED_EXTENSIONS = {
    '.ppt', '.pptx', '.pdf', '.png', '.jpg', '.jpeg', '.zip', '.md', '.xlsx', '.xls', '.py', '.ts', '.tsx', '.js', '.json', '.txt', '.yml', '.yaml'
}


class FileService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)

    def get_submission(self, submission_id: str) -> EmployeeSubmission | None:
        return self.db.get(EmployeeSubmission, submission_id)

    def list_files(self, submission_id: str) -> list[UploadedFile]:
        query = select(UploadedFile).where(UploadedFile.submission_id == submission_id).order_by(UploadedFile.created_at.desc())
        return list(self.db.scalars(query))

    def list_evidence(self, submission_id: str) -> list[EvidenceItem]:
        query = select(EvidenceItem).where(EvidenceItem.submission_id == submission_id).order_by(EvidenceItem.created_at.desc())
        return list(self.db.scalars(query))

    def get_file(self, file_id: str) -> UploadedFile | None:
        return self.db.get(UploadedFile, file_id)

    def _validate_file_name_and_content(self, file_name: str, content: bytes) -> None:
        extension = Path(file_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError('Unsupported file type.')
        if len(content) > self.settings.max_upload_size_mb * 1024 * 1024:
            raise ValueError('File exceeds maximum allowed size.')

    def validate_upload(self, upload: UploadFile, content: bytes) -> None:
        self._validate_file_name_and_content(upload.filename or 'upload.bin', content)

    def _create_file_record(self, *, submission_id: str, file_name: str, content: bytes) -> UploadedFile:
        storage_key = self.storage.save_bytes(
            submission_id=submission_id,
            file_name=file_name,
            content=content,
        )
        file_record = UploadedFile(
            submission_id=submission_id,
            file_name=file_name,
            file_type=Path(file_name).suffix.lower().lstrip('.') or 'bin',
            storage_key=storage_key,
            parse_status='pending',
        )
        self.db.add(file_record)
        return file_record

    def _mark_submission_uploaded(self, submission: EmployeeSubmission) -> None:
        submission.status = 'submitted'
        self.db.add(submission)

    def upload_files(self, submission_id: str, uploads: list[UploadFile]) -> list[UploadedFile]:
        submission = self.get_submission(submission_id)
        if submission is None:
            raise ValueError('Submission not found.')

        saved_files: list[UploadedFile] = []
        for upload in uploads:
            content = upload.file.read()
            self.validate_upload(upload, content)
            file_record = self._create_file_record(
                submission_id=submission_id,
                file_name=upload.filename or 'upload.bin',
                content=content,
            )
            saved_files.append(file_record)

        self._mark_submission_uploaded(submission)
        self.db.commit()
        for item in saved_files:
            self.db.refresh(item)
        return saved_files

    def _github_archive_url(self, owner: str, repo: str, ref: str | None = None) -> tuple[str, str]:
        archive_url = f'https://api.github.com/repos/{owner}/{repo}/zipball'
        if ref:
            archive_url = f'{archive_url}/{ref}'
        safe_ref = ref.replace('/', '-') if ref else None
        file_name = f'{repo}-{safe_ref}.zip' if safe_ref else f'{repo}.zip'
        return archive_url, file_name

    def _build_remote_request(self, remote_url: str) -> Request:
        headers = {'User-Agent': 'wage-adjust-platform'}
        host = urlparse(remote_url).netloc.lower()
        if host == 'api.github.com':
            headers['Accept'] = 'application/vnd.github+json'
        elif host == 'raw.githubusercontent.com':
            headers['Accept'] = 'application/octet-stream'
        return Request(remote_url, headers=headers)

    def _normalize_github_repo(self, owner: str, repo: str) -> tuple[str, str]:
        normalized_owner = unquote(owner).strip()
        normalized_repo = unquote(repo).strip()
        if normalized_repo.endswith('.git'):
            normalized_repo = normalized_repo[:-4]
        if not normalized_owner or not normalized_repo:
            raise ValueError('Unsupported GitHub link.')
        return normalized_owner, normalized_repo

    def _normalize_github_raw_url(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        parts = [part for part in parsed.path.split('/') if part]

        if host == 'raw.githubusercontent.com':
            if len(parts) < 4:
                raise ValueError('Unsupported GitHub file URL.')
            return url, parts[-1]

        if host in {'github.com', 'www.github.com'}:
            if len(parts) < 2:
                raise ValueError('Unsupported GitHub link.')

            owner, repo = self._normalize_github_repo(parts[0], parts[1])
            if len(parts) == 2:
                return self._github_archive_url(owner, repo)

            if len(parts) >= 4 and parts[2] == 'blob':
                ref = parts[3]
                file_parts = parts[4:]
                if not file_parts:
                    raise ValueError('Unsupported GitHub file URL.')
                file_path = '/'.join(file_parts)
                raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{file_path}'
                return raw_url, unquote(file_parts[-1])

            if len(parts) >= 4 and parts[2] == 'tree':
                ref = parts[3]
                return self._github_archive_url(owner, repo, ref)

            return self._github_archive_url(owner, repo)

        raise ValueError('Only GitHub repository, branch, folder, or file links are supported.')

    def _download_remote_file(self, raw_url: str) -> bytes:
        request = self._build_remote_request(raw_url)
        try:
            with urlopen(request, timeout=15) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code in {401, 403, 404}:
                raise ValueError('Unable to download from GitHub. Please confirm the link is correct and the repository is public.') from exc
            raise ValueError(f'GitHub returned HTTP {exc.code} while downloading the link.') from exc
        except URLError as exc:
            raise ValueError('Unable to reach GitHub right now. Please try again later.') from exc
        except TimeoutError as exc:
            raise ValueError('Timed out while downloading from GitHub. Please try again later.') from exc

    def import_github_file(self, submission_id: str, url: str) -> UploadedFile:
        submission = self.get_submission(submission_id)
        if submission is None:
            raise ValueError('Submission not found.')

        raw_url, file_name = self._normalize_github_raw_url(url)
        content = self._download_remote_file(raw_url)
        self._validate_file_name_and_content(file_name, content)
        file_record = self._create_file_record(submission_id=submission_id, file_name=file_name, content=content)
        self._mark_submission_uploaded(submission)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def delete_submission_evidence_for_file(self, submission_id: str, file_id: str) -> None:
        items = self.list_evidence(submission_id)
        for item in items:
            if item.metadata_json.get('file_id') == file_id:
                self.db.delete(item)

    def replace_file(self, file_id: str, upload: UploadFile) -> UploadedFile:
        file_record = self.get_file(file_id)
        if file_record is None:
            raise ValueError('File not found.')

        content = upload.file.read()
        self.validate_upload(upload, content)
        self.storage.delete(file_record.storage_key)
        self.delete_submission_evidence_for_file(file_record.submission_id, file_record.id)
        submission = self.get_submission(file_record.submission_id)
        if submission is None:
            raise ValueError('Submission not found.')

        new_storage_key = self.storage.save_bytes(
            submission_id=file_record.submission_id,
            file_name=upload.filename or file_record.file_name,
            content=content,
        )
        file_record.file_name = upload.filename or file_record.file_name
        file_record.file_type = Path(upload.filename or file_record.file_name).suffix.lower().lstrip('.') or 'bin'
        file_record.storage_key = new_storage_key
        file_record.parse_status = 'pending'
        self._mark_submission_uploaded(submission)
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def delete_file(self, file_id: str) -> str:
        file_record = self.get_file(file_id)
        if file_record is None:
            raise ValueError('File not found.')

        submission = self.get_submission(file_record.submission_id)
        self.storage.delete(file_record.storage_key)
        self.delete_submission_evidence_for_file(file_record.submission_id, file_record.id)
        self.db.delete(file_record)

        if submission is not None:
            remaining_files = [item for item in submission.uploaded_files if item.id != file_id]
            if not remaining_files:
                submission.status = 'collecting'
                self.db.add(submission)

        self.db.commit()
        return file_id

    def mark_file_status(self, file_record: UploadedFile, status: str) -> UploadedFile:
        file_record.parse_status = status
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def preview_file(self, file_id: str) -> tuple[UploadedFile, str] | None:
        file_record = self.get_file(file_id)
        if file_record is None:
            return None
        return file_record, self.storage.preview_url(file_record.storage_key)
