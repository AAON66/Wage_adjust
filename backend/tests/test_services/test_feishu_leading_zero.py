from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.services.feishu_service import (
    FeishuConfigValidationError,
    FeishuService,
)

load_model_modules()


# ---------------------------------------------------------------------------
# Local fixtures (no conftest.py exists for this test tree — inline by design)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """In-memory SQLite session shared across threads via StaticPool."""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_service(db_session: Session) -> FeishuService:
    return FeishuService(db_session)


# ---------------------------------------------------------------------------
# _map_fields tests (EMPNO-02 / D-08)
# ---------------------------------------------------------------------------

def test_map_fields_float_employee_no_produces_string_with_decimal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """W-1 修复：_extract_cell_value 对 float 原样返回 → str(2615.0) = '2615.0'。

    关键断言：value == '2615.0'（不再走 str(int(value)) 丢零路径，得到的是 str(float)）。
    同时 raw_value 为 float 会触发 warning。
    """
    raw_fields = {'工号': 2615.0, '姓名': '张三'}
    field_mapping = {'工号': 'employee_no', '姓名': 'name'}
    with caplog.at_level(logging.WARNING):
        mapped = FeishuService._map_fields(raw_fields, field_mapping)
    assert mapped is not None
    assert mapped['employee_no'] == '2615.0'
    assert '飞书 employee_no 非文本类型' in caplog.text


def test_map_fields_warns_when_employee_no_not_string(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """int 12345 经 _extract_cell_value 原样返回 → str(12345) = '12345'；warning 触发。"""
    raw_fields = {'工号': 12345, '姓名': '李四'}
    field_mapping = {'工号': 'employee_no', '姓名': 'name'}
    with caplog.at_level(logging.WARNING):
        mapped = FeishuService._map_fields(raw_fields, field_mapping)
    assert mapped is not None
    assert mapped['employee_no'] == '12345'
    assert '飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）' in caplog.text


def test_map_fields_preserves_string_employee_no_with_leading_zero(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """raw value 是 str '02615' → 保留前导零；不触发 warning。"""
    raw_fields = {'工号': '02615', '姓名': '王五'}
    field_mapping = {'工号': 'employee_no', '姓名': 'name'}
    with caplog.at_level(logging.WARNING):
        mapped = FeishuService._map_fields(raw_fields, field_mapping)
    assert mapped is not None
    assert mapped['employee_no'] == '02615'
    assert '飞书 employee_no 非文本类型' not in caplog.text


# ---------------------------------------------------------------------------
# _lookup_employee fallback counter tests (EMPNO-04 / D-03 / D-04 / B-10 修复)
# ---------------------------------------------------------------------------

def test_lookup_employee_fallback_scenario_A_db_has_leading_zero_feishu_missing(
    db_session: Session,
) -> None:
    """场景 A：DB 存 '02615'、飞书返回 '2615' → fallback 命中 → 计数 +1。

    验证 B-10 修复：_build_employee_map 不再预填充 stripped 版本，
    此场景下 exact '2615' miss、走 lstrip 比对分支。
    """
    svc = _make_service(db_session)
    emp_map = {'02615': 'emp-uuid-1'}  # 模拟 _build_employee_map 的真实视图（无预填充）
    counter: dict[str, int] = {'count': 0}
    emp_id = svc._lookup_employee(emp_map, '2615', fallback_counter=counter)
    assert emp_id == 'emp-uuid-1'
    assert counter['count'] == 1


def test_lookup_employee_exact_match_scenario_B_no_fallback(
    db_session: Session,
) -> None:
    """场景 B：DB 存 '02615'、飞书返回 '02615' → exact 命中 → 计数 0。"""
    svc = _make_service(db_session)
    emp_map = {'02615': 'emp-uuid-1'}
    counter: dict[str, int] = {'count': 0}
    emp_id = svc._lookup_employee(emp_map, '02615', fallback_counter=counter)
    assert emp_id == 'emp-uuid-1'
    assert counter['count'] == 0


def test_lookup_employee_exact_match_scenario_C_no_leading_zero(
    db_session: Session,
) -> None:
    """场景 C：DB 存 '12345'、飞书返回 '12345' → exact 命中 → 计数 0。"""
    svc = _make_service(db_session)
    emp_map = {'12345': 'emp-uuid-1'}
    counter: dict[str, int] = {'count': 0}
    emp_id = svc._lookup_employee(emp_map, '12345', fallback_counter=counter)
    assert emp_id == 'emp-uuid-1'
    assert counter['count'] == 0


def test_lookup_employee_fallback_scenario_D_feishu_extra_zero(
    db_session: Session,
) -> None:
    """场景 D：DB 存 '02615'、飞书返回 '002615'（飞书多 0）→ fallback 命中 → 计数 +1。

    两端 lstrip('0') 都得到 '2615'，匹配成功。
    """
    svc = _make_service(db_session)
    emp_map = {'02615': 'emp-uuid-1'}
    counter: dict[str, int] = {'count': 0}
    emp_id = svc._lookup_employee(emp_map, '002615', fallback_counter=counter)
    assert emp_id == 'emp-uuid-1'
    assert counter['count'] == 1


def test_lookup_employee_miss_returns_none_no_counter_change(
    db_session: Session,
) -> None:
    """完全找不到匹配 → None，计数 0。"""
    svc = _make_service(db_session)
    emp_map = {'02615': 'emp-uuid-1'}
    counter: dict[str, int] = {'count': 0}
    emp_id = svc._lookup_employee(emp_map, '99999', fallback_counter=counter)
    assert emp_id is None
    assert counter['count'] == 0


def test_build_employee_map_no_stripped_prefill(db_session: Session) -> None:
    """B-10 修复验证：_build_employee_map 仅含 DB 原始 emp_no，无预填充 stripped 版本。"""
    from backend.app.models.employee import Employee
    emp = Employee(
        id='emp-test-1', employee_no='02615', name='Test',
        department='Eng', job_family='SW', job_level='P5',
    )
    db_session.add(emp)
    db_session.commit()

    svc = _make_service(db_session)
    emp_map = svc._build_employee_map()
    assert emp_map == {'02615': 'emp-test-1'}
    assert '2615' not in emp_map  # 关键：stripped 版本不被预填充


# ---------------------------------------------------------------------------
# validate_field_mapping tests (EMPNO-03 / D-01 / D-02)
# ---------------------------------------------------------------------------

def test_validate_field_mapping_accepts_text_type_for_employee_no(
    db_session: Session,
) -> None:
    """mock httpx.get 返回 type=1（text） — validate 通过不抛。"""
    svc = _make_service(db_session)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'code': 0,
        'data': {
            'items': [
                {'field_id': 'fld_1', 'field_name': '工号', 'type': 1, 'ui_type': 'Text'},
            ],
            'has_more': False,
            'page_token': None,
        },
    }
    with patch.object(FeishuService, '_ensure_token', return_value='mock-token'), \
         patch('backend.app.services.feishu_service.httpx.get', return_value=mock_resp):
        svc._validate_field_mapping_with_credentials(
            app_id='test-id',
            app_secret='test-secret',
            app_token='test-token',
            table_id='test-table',
            field_mapping={'工号': 'employee_no'},
        )  # 不应抛异常


def test_validate_field_mapping_rejects_number_type_for_employee_no(
    db_session: Session,
) -> None:
    """mock httpx 返回 type=2（number），走真实 validator 逻辑，断言 raise 且 detail 结构严格。"""
    svc = _make_service(db_session)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'code': 0,
        'data': {
            'items': [
                {'field_id': 'fld_1', 'field_name': '工号', 'type': 2, 'ui_type': 'Number'},
            ],
            'has_more': False,
            'page_token': None,
        },
    }
    with patch.object(FeishuService, '_ensure_token', return_value='mock-token'), \
         patch('backend.app.services.feishu_service.httpx.get', return_value=mock_resp):
        with pytest.raises(FeishuConfigValidationError) as exc_info:
            svc._validate_field_mapping_with_credentials(
                app_id='test-id',
                app_secret='test-secret',
                app_token='test-token',
                table_id='test-table',
                field_mapping={'工号': 'employee_no'},
            )
        assert exc_info.value.detail == {
            'error': 'invalid_field_type',
            'field': 'employee_no',
            'expected': 'text',
            'actual': 'number',
        }


def test_validate_field_mapping_raises_when_field_name_not_in_bitable(
    db_session: Session,
) -> None:
    """mock 返回的 field_name 不含配置里的映射名 → field_not_found_in_bitable。"""
    svc = _make_service(db_session)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'code': 0,
        'data': {
            'items': [
                {'field_id': 'fld_1', 'field_name': '员工姓名', 'type': 1},
            ],
            'has_more': False,
            'page_token': None,
        },
    }
    with patch.object(FeishuService, '_ensure_token', return_value='mock-token'), \
         patch('backend.app.services.feishu_service.httpx.get', return_value=mock_resp):
        with pytest.raises(FeishuConfigValidationError) as exc_info:
            svc._validate_field_mapping_with_credentials(
                app_id='test-id',
                app_secret='test-secret',
                app_token='test-token',
                table_id='test-table',
                field_mapping={'工号': 'employee_no'},  # '工号' 不在 bitable 中
            )
        assert exc_info.value.detail['error'] == 'field_not_found_in_bitable'
        assert exc_info.value.detail['field'] == 'employee_no'
