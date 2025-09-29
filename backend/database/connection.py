"""
Database connection management and session handling.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import psycopg2
from psycopg2 import OperationalError

from .config import DatabaseConfig, get_database_config
from ..models.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or get_database_config()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._is_initialized = False
    
    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._session_factory
    
    def _create_engine(self) -> Engine:
        """Create database engine with connection pooling."""
        logger.info(f"Creating database engine for {self.config.db_host}:{self.config.db_port}/{self.config.db_name}")
        
        engine = create_engine(
            self.config.database_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=self.config.pool_pre_ping,
            echo=self.config.db_echo,
            echo_pool=self.config.db_echo_pool,
            connect_args={
                "connect_timeout": self.config.connect_timeout,
                "command_timeout": self.config.command_timeout,
            }
        )
        
        # Add event listeners for connection management
        self._setup_engine_events(engine)
        
        return engine
    
    def _setup_engine_events(self, engine: Engine) -> None:
        """Setup engine event listeners for connection management."""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set connection parameters for PostgreSQL."""
            if hasattr(dbapi_connection, 'set_session'):
                # Set session parameters for PostgreSQL
                dbapi_connection.set_session(autocommit=False)
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout."""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Handle connection checkin."""
            logger.debug("Connection checked in to pool")
        
        @event.listens_for(engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation."""
            logger.warning(f"Connection invalidated: {exception}")
    
    def initialize(self) -> bool:
        """Initialize database connection and create tables."""
        try:
            logger.info("Initializing database connection...")
            
            # Test connection
            if not self.test_connection():
                logger.error("Failed to establish database connection")
                return False
            
            # Create tables if they don't exist
            self.create_tables()
            
            self._is_initialized = True
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            # Test using psycopg2 directly first
            conn_params = self.config.test_connection_params()
            conn = psycopg2.connect(**conn_params)
            conn.close()
            
            # Test using SQLAlchemy engine
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.info("Database connection test successful")
            return True
            
        except (OperationalError, SQLAlchemyError) as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {str(e)}")
            return False
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self._is_initialized:
            self.initialize()
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_raw_sql(self, sql: str, params: Optional[dict] = None) -> list:
        """Execute raw SQL query."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                if result.returns_rows:
                    return result.fetchall()
                return []
        except Exception as e:
            logger.error(f"Failed to execute raw SQL: {str(e)}")
            raise
    
    def get_connection_info(self) -> dict:
        """Get current connection information."""
        info = self.config.get_connection_info()
        info.update({
            "is_initialized": self._is_initialized,
            "engine_created": self._engine is not None,
            "session_factory_created": self._session_factory is not None
        })
        
        if self._engine:
            pool = self._engine.pool
            info.update({
                "pool_status": {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
            })
        
        return info
    
    def health_check(self) -> dict:
        """Perform database health check."""
        health_info = {
            "status": "unknown",
            "connection_test": False,
            "tables_exist": False,
            "pool_status": {},
            "error": None
        }
        
        try:
            # Test connection
            health_info["connection_test"] = self.test_connection()
            
            # Check if tables exist
            if health_info["connection_test"]:
                with self.engine.connect() as connection:
                    result = connection.execute(text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public'"
                    ))
                    table_count = result.scalar()
                    health_info["tables_exist"] = table_count > 0
            
            # Get pool status
            if self._engine:
                pool = self._engine.pool
                health_info["pool_status"] = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
            
            # Determine overall status
            if health_info["connection_test"] and health_info["tables_exist"]:
                health_info["status"] = "healthy"
            elif health_info["connection_test"]:
                health_info["status"] = "degraded"
            else:
                health_info["status"] = "unhealthy"
                
        except Exception as e:
            health_info["status"] = "error"
            health_info["error"] = str(e)
            logger.error(f"Database health check failed: {str(e)}")
        
        return health_info
    
    def close(self) -> None:
        """Close database connections and cleanup."""
        try:
            if self._engine:
                self._engine.dispose()
                logger.info("Database engine disposed")
            
            self._engine = None
            self._session_factory = None
            self._is_initialized = False
            
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Session:
    """Get a new database session."""
    return get_database_manager().get_session()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db_manager = get_database_manager()
    with db_manager.session_scope() as session:
        yield session


def initialize_database() -> bool:
    """Initialize the database."""
    return get_database_manager().initialize()


def close_database() -> None:
    """Close database connections."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None