"""MySQL connection and request-scoped database sessions."""

import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session


# Load local environment settings when this module is imported.
load_dotenv()


def _build_database_url() -> URL:
    """Build the connection details from environment variables."""

    password = os.getenv("DB_PASSWORD")

    if password is None:
        raise RuntimeError(
            "DB_PASSWORD is missing. Copy .env.example to .env "
            "and set your local MySQL password."
        )

    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER", "root"),
        password=password,
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "IdatenOps"),
        query={"charset": "utf8mb4"},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one reusable SQLAlchemy Engine."""

    return create_engine(
        _build_database_url(),
        pool_pre_ping=True,
    )


def get_db_session() -> Generator[Session, None, None]:
    """Provide a database session and close it after use."""

    with Session(get_engine()) as session:
        yield session


def check_database_connection() -> dict[str, str]:
    """Check that MySQL is reachable and the configured database exists."""

    with get_engine().connect() as connection:
        database_name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        database_version = connection.execute(
            text("SELECT VERSION()")
        ).scalar_one()

    return {
        "database": str(database_name),
        "version": str(database_version),
    }