from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.tasks.test_tasks import db_health_check


def main() -> None:
    async_result = db_health_check.delay()
    payload = async_result.get(timeout=30)
    print(f'PHASE19_TASK_ID={async_result.id}')
    print(f'PHASE19_TASK_RESULT={json.dumps(payload, sort_keys=True)}')


if __name__ == '__main__':
    main()
