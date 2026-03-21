from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules


class HandbookDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f'handbook-{uuid4().hex}.db').as_posix()
        uploads_path = (temp_root / f'handbook-uploads-{uuid4().hex}').as_posix()
        self.settings = Settings(
            allow_self_registration=True,
            database_url=f'sqlite+pysqlite:///{database_path}',
            storage_base_dir=uploads_path,
        )
        load_model_modules()
        self.engine = create_db_engine(self.settings)
        init_database(self.engine)
        self.session_factory = create_session_factory(self.settings)

    def override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()



def build_client() -> TestClient:
    context = HandbookDatabaseContext()
    app = create_app(context.settings)
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app)



def register_admin(client: TestClient) -> dict[str, str]:
    response = client.post(
        '/api/v1/auth/register',
        json={'email': 'admin@example.com', 'password': 'Password123', 'role': 'admin'},
    )
    assert response.status_code == 201
    return {'Authorization': f"Bearer {response.json()['tokens']['access_token']}"}



def test_upload_list_and_delete_handbook() -> None:
    with build_client() as client:
        headers = register_admin(client)

        upload_response = client.post(
            '/api/v1/handbooks',
            headers=headers,
            files=[('file', ('员工手册.md', '# 员工手册\n考勤管理应按规定打卡。\n绩效评估每季度进行一次。', 'text/markdown'))],
        )
        assert upload_response.status_code == 201
        assert upload_response.json()['parse_status'] == 'parsed'
        assert upload_response.json()['summary']
        assert len(upload_response.json()['key_points_json']) >= 1

        list_response = client.get('/api/v1/handbooks', headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 1
        handbook_id = list_response.json()['items'][0]['id']

        delete_response = client.delete(f'/api/v1/handbooks/{handbook_id}', headers=headers)
        assert delete_response.status_code == 200
        assert delete_response.json()['deleted_handbook_id'] == handbook_id

        list_after_delete = client.get('/api/v1/handbooks', headers=headers)
        assert list_after_delete.status_code == 200
        assert list_after_delete.json()['total'] == 0
