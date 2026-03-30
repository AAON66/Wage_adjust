"""飞书 API 响应 mock 数据，供测试复用。"""
from __future__ import annotations

# 多维表格搜索 — 第一页（has_more=True）
FEISHU_SEARCH_RESPONSE_PAGE1 = {
    'code': 0,
    'msg': 'success',
    'data': {
        'has_more': True,
        'page_token': 'page2_token',
        'total': 3,
        'items': [
            {
                'record_id': 'rec_001',
                'fields': {
                    '工号': '10001',
                    '考勤月份': '2026-03',
                    '出勤率': 0.95,
                    '缺勤天数': 1.0,
                    '加班时长': 12.5,
                    '迟到次数': 2,
                    '早退次数': 0,
                },
                'last_modified_time': 1774800000000,
            },
            {
                'record_id': 'rec_002',
                'fields': {
                    '工号': '10002',
                    '考勤月份': '2026-03',
                    '出勤率': 1.0,
                    '缺勤天数': 0.0,
                    '加班时长': 0.0,
                    '迟到次数': 0,
                    '早退次数': 0,
                },
                'last_modified_time': 1774800100000,
            },
        ],
    },
}

# 多维表格搜索 — 第二页（has_more=False）
FEISHU_SEARCH_RESPONSE_PAGE2 = {
    'code': 0,
    'msg': 'success',
    'data': {
        'has_more': False,
        'page_token': None,
        'total': 3,
        'items': [
            {
                'record_id': 'rec_003',
                'fields': {
                    '工号': '10003',
                    '考勤月份': '2026-03',
                    '出勤率': 0.80,
                    '缺勤天数': 4.0,
                    '加班时长': 0.0,
                    '迟到次数': 5,
                    '早退次数': 3,
                },
                'last_modified_time': 1774800200000,
            },
        ],
    },
}

# 飞书 API 错误响应
FEISHU_ERROR_RESPONSE = {
    'code': 99991663,
    'msg': 'token is expired',
    'data': None,
}

# 获取 tenant_access_token 成功响应
FEISHU_TOKEN_RESPONSE = {
    'code': 0,
    'msg': 'ok',
    'tenant_access_token': 't-g1234567890abcdefghijklmnopqrstuv',
    'expire': 7200,
}
