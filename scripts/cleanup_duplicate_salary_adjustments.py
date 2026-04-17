"""清理 salary_adjustment_records 表中的重复记录。

保留每组 (employee_id, adjustment_date, adjustment_type) 中 created_at 最新的一条，
删除其余重复行。

用法:
    cd /opt/wage-adjust
    .venv/bin/python3.11 scripts/cleanup_duplicate_salary_adjustments.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.app.core.database import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        # 统计重复组数
        dupe_groups = db.execute(text(
            "SELECT employee_id, adjustment_date, adjustment_type, COUNT(*) as cnt "
            "FROM salary_adjustment_records "
            "GROUP BY employee_id, adjustment_date, adjustment_type "
            "HAVING cnt > 1"
        )).fetchall()
        print(f'Found {len(dupe_groups)} groups with duplicates')

        if not dupe_groups:
            print('No duplicates to clean up.')
            return

        # 统计总重复记录数
        total_before = db.execute(text("SELECT COUNT(*) FROM salary_adjustment_records")).scalar()
        print(f'Total records before cleanup: {total_before}')

        # 删除重复行，保留每组中 created_at 最大（最新）的一条
        # SQLite 兼容写法
        deleted = db.execute(text(
            "DELETE FROM salary_adjustment_records "
            "WHERE id NOT IN ("
            "  SELECT id FROM ("
            "    SELECT id, ROW_NUMBER() OVER ("
            "      PARTITION BY employee_id, adjustment_date, adjustment_type "
            "      ORDER BY created_at DESC"
            "    ) as rn"
            "    FROM salary_adjustment_records"
            "  ) WHERE rn = 1"
            ")"
        ))
        db.commit()

        total_after = db.execute(text("SELECT COUNT(*) FROM salary_adjustment_records")).scalar()
        print(f'Deleted {deleted.rowcount} duplicate records')
        print(f'Total records after cleanup: {total_after}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
