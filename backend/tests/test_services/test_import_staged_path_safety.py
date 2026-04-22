"""Phase 32-03 Task 1: _staged_file_path 路径遍历防护。

T-32-01 (Tampering): 双重防护
- 字符级校验：拒 `..`, `/`, `\\`, 空字符串
- resolve 后 is_relative_to(base_dir) 二次校验

外加 sha256 hash 一致性测试。
"""
from __future__ import annotations

import hashlib

import pytest


def test_staged_path_valid_uuid(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    path = svc._staged_file_path('123e4567-e89b-12d3-a456-426614174000')
    assert str(tmp_uploads_dir) in str(path)
    assert path.name == '123e4567-e89b-12d3-a456-426614174000.xlsx'


def test_staged_path_rejects_traversal_dotdot(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    with pytest.raises(ValueError, match='path traversal'):
        svc._staged_file_path('../etc/passwd')


def test_staged_path_rejects_traversal_slash(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    with pytest.raises(ValueError, match='path traversal'):
        svc._staged_file_path('valid/../../escape')


def test_staged_path_rejects_backslash(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    with pytest.raises(ValueError, match='path traversal'):
        svc._staged_file_path('windows\\escape')


def test_staged_path_rejects_empty(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    with pytest.raises(ValueError, match='path traversal'):
        svc._staged_file_path('')


def test_save_and_read_staged_with_hash(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    job_id = '123e4567-e89b-12d3-a456-426614174000'
    content = b'fake xlsx bytes for test'
    sha = svc._save_staged_file(job_id, content)
    assert sha == hashlib.sha256(content).hexdigest()
    # 读回 + hash 校验通过
    read_back = svc._read_staged_file(job_id, expected_sha256=sha)
    assert read_back == content


def test_read_staged_hash_mismatch_raises(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    job_id = '123e4567-e89b-12d3-a456-426614174001'
    svc._save_staged_file(job_id, b'original')
    with pytest.raises(ValueError, match='hash mismatch'):
        svc._read_staged_file(job_id, expected_sha256='wrong_hash_value' * 4)
