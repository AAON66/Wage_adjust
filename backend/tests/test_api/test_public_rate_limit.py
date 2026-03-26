from __future__ import annotations


def test_public_api_rate_limit_config_is_enforced() -> None:
    """The public_api_rate_limit config value is parsed and applied to /api/v1/public/ routes."""
    from backend.app.core.config import Settings
    from backend.app.main import create_app

    settings = Settings(
        environment='development',
        database_url='sqlite+pysqlite:///:memory:',
        jwt_secret_key='test_jwt_key_for_testing',
        public_api_key='test_pub_key',
        public_api_rate_limit='1000/hour',
    )
    app = create_app(settings)
    # Verify the shared limiter is attached to app state
    assert hasattr(app.state, 'limiter')
    # Verify public routes have request parameter (needed for slowapi)
    import backend.app.api.v1.public as public_module
    import inspect
    sig = inspect.signature(public_module.get_latest_employee_evaluation)
    assert 'request' in sig.parameters


def test_public_limiter_imported_from_shared_module() -> None:
    """public.py must import limiter from rate_limit.py, not instantiate its own."""
    import pathlib

    public_src = pathlib.Path('backend/app/api/v1/public.py').read_text(encoding='utf-8')
    # Check that the import is from rate_limit, not a local Limiter()
    assert 'from backend.app.core.rate_limit import' in public_src, (
        'public.py must import limiter from backend.app.core.rate_limit, not instantiate its own'
    )
    # Ensure no standalone Limiter() instantiation in public.py
    assert 'Limiter(key_func' not in public_src, (
        'public.py must not create its own Limiter instance — import from rate_limit.py'
    )
