"""
Database configuration and connection management for SQLModel.
"""

from typing import Optional
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import Engine
from pathlib import Path


class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database configuration"""
        if database_url is None:
            # Default to SQLite database in data directory
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            database_url = f"sqlite:///{data_dir}/news_aggregator.db"

        self.database_url = database_url
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        """Get or create database engine"""
        if self._engine is None:
            # For SQLite, enable foreign keys and journal mode
            connect_args = {}
            if self.database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}

            self._engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                connect_args=connect_args,
            )
        return self._engine

    def create_tables(self) -> None:
        """Create all tables defined in SQLModel models"""
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return Session(self.engine)

    def close(self) -> None:
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Global database instance
_db_config: Optional[DatabaseConfig] = None


def get_database() -> DatabaseConfig:
    """Get the global database instance"""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


def init_database(database_url: Optional[str] = None) -> DatabaseConfig:
    """Initialize the database with optional custom URL"""
    global _db_config
    _db_config = DatabaseConfig(database_url)
    _db_config.create_tables()
    return _db_config


def get_session() -> Session:
    """Get a database session (convenience function)"""
    return get_database().get_session()
