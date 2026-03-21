from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.storage import LocalStorageService
from backend.app.models.employee_handbook import EmployeeHandbook
from backend.app.models.user import User
from backend.app.parsers.document_parser import DocumentParser
from backend.app.services.llm_service import DeepSeekService

ALLOWED_HANDBOOK_EXTENSIONS = {'.pdf', '.md', '.txt'}


class EmployeeHandbookService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.storage = LocalStorageService(settings)
        self.parser = DocumentParser()
        self.llm = DeepSeekService(settings)

    def list_handbooks(self) -> list[EmployeeHandbook]:
        query = select(EmployeeHandbook).order_by(EmployeeHandbook.created_at.desc())
        return list(self.db.scalars(query))

    def get_handbook(self, handbook_id: str) -> EmployeeHandbook | None:
        return self.db.get(EmployeeHandbook, handbook_id)

    def _storage_key_for_handbook(self, file_name: str, content: bytes) -> str:
        return self.storage.save_bytes(submission_id='handbooks', file_name=file_name, content=content)

    def _validate_upload(self, upload: UploadFile, content: bytes) -> tuple[str, str]:
        file_name = upload.filename or 'employee-handbook.txt'
        extension = Path(file_name).suffix.lower()
        if extension not in ALLOWED_HANDBOOK_EXTENSIONS:
            raise ValueError('员工手册仅支持 PDF、Markdown 和 TXT 文件。')
        if len(content) > self.settings.max_upload_size_mb * 1024 * 1024:
            raise ValueError('员工手册文件超过当前允许的大小限制。')
        return file_name, extension.lstrip('.')

    def _fallback_payload(self, text: str, file_name: str) -> dict[str, object]:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        segments = [segment.strip(' -•') for segment in re.split(r'[。；\n]', cleaned) if segment.strip()]
        key_points = segments[:5] or ['已上传员工手册，但未能提取到明确条目。']
        tags: list[str] = []
        keywords = {
            '考勤': ('考勤', '出勤', '请假', '打卡'),
            '绩效': ('绩效', '考核', '评估'),
            '薪酬': ('薪酬', '调薪', '奖金', '补贴'),
            '行为规范': ('行为', '纪律', '规范', '合规'),
            '培训发展': ('培训', '学习', '发展', '晋升'),
        }
        lowered = cleaned.lower()
        for label, entries in keywords.items():
            if any(entry.lower() in lowered for entry in entries):
                tags.append(label)
        return {
            'title': Path(file_name).stem,
            'summary': cleaned[:500] or '已上传员工手册，等待解析。',
            'key_points': key_points,
            'tags': tags or ['员工手册'],
        }

    def upload_handbook(self, upload: UploadFile, *, operator: User) -> EmployeeHandbook:
        content = upload.file.read()
        file_name, file_type = self._validate_upload(upload, content)
        storage_key = self._storage_key_for_handbook(file_name, content)
        path = self.storage.resolve_path(storage_key)
        parsed = self.parser.parse(path)
        fallback_payload = self._fallback_payload(parsed.text, file_name)
        llm_result = self.llm.parse_handbook(parsed, file_name=file_name, file_type=file_type, fallback_payload=fallback_payload)
        payload = llm_result.payload

        handbook = EmployeeHandbook(
            title=str(payload.get('title') or fallback_payload['title'])[:255],
            file_name=file_name,
            file_type=file_type,
            storage_key=storage_key,
            parse_status='parsed',
            summary=str(payload.get('summary') or fallback_payload['summary'])[:4000],
            key_points_json=self._normalize_string_list(payload.get('key_points') or fallback_payload['key_points']),
            tags_json=self._normalize_string_list(payload.get('tags') or fallback_payload['tags']),
            uploaded_by_user_id=operator.id,
        )
        self.db.add(handbook)
        self.db.commit()
        self.db.refresh(handbook)
        return handbook

    def delete_handbook(self, handbook_id: str) -> str:
        handbook = self.get_handbook(handbook_id)
        if handbook is None:
            raise ValueError('Employee handbook not found.')
        self.storage.delete(handbook.storage_key)
        self.db.delete(handbook)
        self.db.commit()
        return handbook_id

    def _normalize_string_list(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()][:8]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r'[；;，,\n]', value) if item.strip()][:8]
        return []
