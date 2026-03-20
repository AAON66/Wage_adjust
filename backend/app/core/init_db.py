from __future__ import annotations

from backend.app.core.database import init_database
from backend.app.models import load_model_modules


def main() -> None:
    """CLI entrypoint for creating database tables from registered models."""
    load_model_modules()
    init_database()
    print("Database initialization completed.")


if __name__ == "__main__":
    main()
