from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.schemas.cycle import CycleCreate, CycleUpdate
from backend.app.services.cycle_service import CycleService



def build_session() -> Session:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'cycle-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)()



def test_create_update_and_publish_cycle() -> None:
    db = build_session()
    service = CycleService(db)

    cycle = service.create_cycle(
        CycleCreate(name='2026 Mid-Year', review_period='2026-H1', budget_amount=Decimal('100000.00'), status='draft')
    )
    created_cycle_id = cycle.id
    updated = service.update_cycle(created_cycle_id, CycleUpdate(name='2026 Mid-Year Updated'))
    published = service.update_cycle_status(created_cycle_id, 'published')

    assert created_cycle_id == cycle.id
    assert updated is not None and updated.name == '2026 Mid-Year Updated'
    assert published is not None and published.status == 'published'
