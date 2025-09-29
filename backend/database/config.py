"""
Database configuration management.
"""

import os
from typing import Optional
from pydantic import BaseSettings, validator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    # Database connection settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "olt_manager"
    db_user: str = "olt_user"
    db_password: str = "olt_password"
    
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Connection string settings
    db_echo: bool = False
    db_echo_pool: bool = False
    
    # SSL settings
    db_sslmode: str = "prefer"
    db_sslcert: Optional[str] = None
    db_sslkey: Optional[str] = None
    db_sslrootcert: Optional[str] = None
    
    # Connection timeout settings
    connect_timeout: int = 10
    command_timeout: int = 60
    
    # Migration settings
    alembic_config_path: str = "alembic.ini"
    migration_directory: str = "migrations"
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False
        env_file = ".env"
    
    @validator("db_password")
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Database password must be at least 8 characters long")
        return v
    
    @validator("db_port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Database port must be between 1 and 65535")
        return v
    
    @validator("pool_size")
    def validate_pool_size(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("Pool size must be between 1 and 100")
        return v
    
    @property
    def database_url(self) -> str:
        """Get the complete database URL."""
        url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        
        # Add SSL parameters if configured
        params = []
        if self.db_sslmode != "prefer":
            params.append(f"sslmode={self.db_sslmode}")
        if self.db_sslcert:
            params.append(f"sslcert={self.db_sslcert}")
        if self.db_sslkey:
            params.append(f"sslkey={self.db_sslkey}")
        if self.db_sslrootcert:
            params.append(f"sslrootcert={self.db_sslrootcert}")
        if self.connect_timeout != 10:
            params.append(f"connect_timeout={self.connect_timeout}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    @property
    def async_database_url(self) -> str:
        """Get the async database URL for asyncpg."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    def create_engine(self) -> Engine:
        """Create SQLAlchemy engine with configured settings."""
        return create_engine(
            self.database_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=self.pool_pre_ping,
            echo=self.db_echo,
            echo_pool=self.db_echo_pool,
            connect_args={
                "connect_timeout": self.connect_timeout,
                "command_timeout": self.command_timeout,
            }
        )
    
    def get_connection_info(self) -> dict:
        """Get connection information for debugging (without password)."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "sslmode": self.db_sslmode,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "echo": self.db_echo
        }
    
    def test_connection_params(self) -> dict:
        """Get parameters for testing database connection."""
        import psycopg2
        
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "connect_timeout": self.connect_timeout,
            "sslmode": self.db_sslmode
        }


# Global database configuration instance
db_config = DatabaseConfig()


def get_database_config() -> DatabaseConfig:
    """Get the global database configuration."""
    return db_config


def update_database_config(**kwargs) -> DatabaseConfig:
    """Update database configuration with new values."""
    global db_config
    
    # Create new config with updated values
    current_values = db_config.dict()
    current_values.update(kwargs)
    
    db_config = DatabaseConfig(**current_values)
    return db_config


def validate_database_config() -> tuple[bool, list[str]]:
    """Validate database configuration."""
    errors = []
    
    try:
        # Test basic configuration
        config = get_database_config()
        
        # Check required fields
        if not config.db_host:
            errors.append("Database host is required")
        if not config.db_name:
            errors.append("Database name is required")
        if not config.db_user:
            errors.append("Database user is required")
        if not config.db_password:
            errors.append("Database password is required")
        
        # Validate URL generation
        try:
            url = config.database_url
            if not url.startswith("postgresql://"):
                errors.append("Invalid database URL format")
        except Exception as e:
            errors.append(f"Error generating database URL: {str(e)}")
        
        # Test engine creation
        try:
            engine = config.create_engine()
            engine.dispose()  # Clean up
        except Exception as e:
            errors.append(f"Error creating database engine: {str(e)}")
        
    except Exception as e:
        errors.append(f"Configuration validation error: {str(e)}")
    
    return len(errors) == 0, errors


def get_environment_info() -> dict:
    """Get database-related environment variables."""
    env_vars = {}
    
    # Database connection variables
    db_env_vars = [
        "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
        "DB_SSLMODE", "DB_SSLCERT", "DB_SSLKEY", "DB_SSLROOTCERT",
        "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT",
        "DB_POOL_RECYCLE", "DB_ECHO", "DB_ECHO_POOL"
    ]
    
    for var in db_env_vars:
        value = os.getenv(var)
        if value is not None:
            # Mask password for security
            if "PASSWORD" in var:
                env_vars[var] = "*" * len(value) if value else None
            else:
                env_vars[var] = value
    
    return env_vars