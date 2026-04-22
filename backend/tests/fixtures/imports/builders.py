"""Phase 32 Wave 0 — xlsx test fixture builders.

每个 builder 接收 rows 参数（可选），返回 xlsx 字节。默认 rows 含合法 + 边界 + 冲突场景。

下游 Plan 02-06 测试可直接 import 使用，无需重复造数据。
"""
from __future__ import annotations

import io
from typing import Iterable

from openpyxl import Workbook


def _to_xlsx_bytes(headers: list[str], rows: Iterable[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_hire_info_xlsx(
    rows: list[list] | None = None,
    *,
    with_serial_date: bool = False,
) -> bytes:
    """hire_info 模板字段（D-02）：员工工号 / 入职日期 / 末次调薪日期"""
    headers = ['员工工号', '入职日期', '末次调薪日期']
    default_rows = [
        ['E00001', '2024-03-15', '2025-08-01'],  # ISO string
        ['E00002', '2023-11-20', None],           # 可选字段为空
    ]
    if with_serial_date:
        default_rows.append(['E00003', 45292, '2025-06-01'])  # Excel serial date
    return _to_xlsx_bytes(headers, rows if rows is not None else default_rows)


def build_non_statutory_leave_xlsx(
    rows: list[list] | None = None,
    *,
    with_conflict: bool = False,
) -> bytes:
    """non_statutory_leave 模板字段（D-03）：员工工号 / 年度 / 假期天数 / 假期类型"""
    headers = ['员工工号', '年度', '假期天数', '假期类型']
    default_rows = [
        ['E00001', 2026, 10.5, '事假'],
        ['E00002', 2026, 5.0, None],   # leave_type 可选
    ]
    if with_conflict:
        default_rows.append(['E00001', 2026, 8.0, '病假'])  # 同业务键 (E00001, 2026) 重复
    return _to_xlsx_bytes(headers, rows if rows is not None else default_rows)


def build_performance_grades_xlsx(rows: list[list] | None = None) -> bytes:
    """performance_grades 模板字段：员工工号 / 年度 / 绩效等级"""
    headers = ['员工工号', '年度', '绩效等级']
    default_rows = [
        ['E00001', 2026, 'A'],
        ['E00002', 2026, 'B'],
    ]
    return _to_xlsx_bytes(headers, rows if rows is not None else default_rows)


def build_salary_adjustments_xlsx(rows: list[list] | None = None) -> bytes:
    """salary_adjustments 模板字段：员工工号 / 调薪日期 / 调薪类型 / 调薪金额"""
    headers = ['员工工号', '调薪日期', '调薪类型', '调薪金额']
    default_rows = [
        ['E00001', '2026-01-01', 'annual', 1000.00],
        ['E00002', '2026-01-01', 'annual', 800.00],
    ]
    return _to_xlsx_bytes(headers, rows if rows is not None else default_rows)
