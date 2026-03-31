from __future__ import annotations

import base64
import json


def encode_cursor(last_id: str, sort_value: str | None = None) -> str:
    """Base64 encode cursor. per D-05: base64(json({"id": last_id, "sort": sort_value}))"""
    payload = json.dumps({'id': last_id, 'sort': sort_value}, separators=(',', ':'))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str | None) -> dict[str, str | None] | None:
    """Decode cursor. Returns {"id": ..., "sort": ...}. Returns None if cursor is None. Raises ValueError on invalid input."""
    if cursor is None:
        return None
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(payload)
        if 'id' not in data:
            raise ValueError('Missing id in cursor')
        return data
    except Exception as exc:
        raise ValueError(f'Invalid cursor: {exc}') from exc


def apply_cursor_pagination(
    query,
    *,
    cursor: str | None = None,
    page_size: int = 20,
    id_column,
    sort_column=None,
):
    """Apply cursor pagination to a SQLAlchemy select statement.

    Returns (paginated_query, page_size).
    per D-06: page_size capped at max 100, default 20.
    """
    page_size = min(max(page_size, 1), 100)

    if cursor:
        data = decode_cursor(cursor)
        last_id = data['id']
        query = query.where(id_column > last_id)

    query = query.order_by(id_column.asc())
    # Fetch one extra row to determine has_more
    query = query.limit(page_size + 1)
    return query, page_size
