"""
Database connection and session management for PostgreSQL
Singleton Database class that manages connection lifecycle
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from typing import Generator, Optional
from threading import Lock
from src.utils.exceptions import DatabaseConnectionError

# Base class for ORM models
Base = declarative_base()


class Database:
    """
    Singleton Database class for managing database connections.
    Initializes engine and session factory on first access or explicit initialization.
    """
    _instance: Optional['Database'] = None
    _lock: Lock = Lock()
    
    def __new__(cls):
        """Singleton pattern - ensures only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize instance variables (only runs once due to singleton)"""
        if not hasattr(self, '_initialized'):
            self._engine: Optional[create_engine] = None
            self._SessionLocal: Optional[sessionmaker] = None
            self._initialized = False
    
    def initialize(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20
    ) -> None:
        """
        Initialize database connection.
        
        Args:
            database_url: PostgreSQL connection string
            echo: Log SQL queries (default: False)
            pool_size: Number of connections to maintain (default: 10)
            max_overflow: Maximum overflow connections (default: 20)
        
        Raises:
            DatabaseConnectionError: If connection fails
        """
        if self._initialized:
            return  # Already initialized
        
        with self._lock:
            if self._initialized:
                return  # Double-check after acquiring lock
            
            try:
                if not database_url:
                    raise ValueError("database_url cannot be empty")
                
                self._engine = create_engine(
                    database_url,
                    pool_pre_ping=True,  # Verify connections before using
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    echo=echo
                )
                
                # Test the connection
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    conn.commit()
                
                self._SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self._engine
                )
                
                self._initialized = True
                
            except OperationalError as e:
                raise DatabaseConnectionError(
                    f"Failed to connect to database: {str(e)}. Check your DATABASE_URL configuration.",
                    e
                ) from e
            except SQLAlchemyError as e:
                raise DatabaseConnectionError(
                    f"Database initialization error: {str(e)}",
                    e
                ) from e
            except Exception as e:
                raise DatabaseConnectionError(
                    f"Unexpected error initializing database: {str(e)}",
                    e
                ) from e
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session (for use in FastAPI dependencies).
        
        Yields:
            Session: SQLAlchemy database session
        
        Raises:
            DatabaseConnectionError: If database is not initialized or connection fails
        
        Example:
            @router.get("/items")
            async def get_items(db: Session = Depends(database.get_session)):
                return db.query(Item).all()
        """
        if not self._initialized or self._SessionLocal is None:
            raise DatabaseConnectionError(
                "Database not initialized. Call database.initialize() first."
            )
        
        db = None
        try:
            db = self._SessionLocal()
            yield db
        except OperationalError as e:
            if db:
                db.rollback()
            raise DatabaseConnectionError(
                f"Database connection lost: {str(e)}",
                e
            ) from e
        except SQLAlchemyError as e:
            if db:
                db.rollback()
            raise DatabaseConnectionError(
                f"Database session error: {str(e)}",
                e
            ) from e
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass  # Ignore errors during cleanup
    
    def create_tables(self):
        """Create all database tables defined in models"""
        if not self._initialized or self._engine is None:
            raise DatabaseConnectionError(
                "Database not initialized. Call database.initialize() first."
            )
        Base.metadata.create_all(bind=self._engine)
    
    def get_engine(self):
        """Get the database engine (for advanced use cases)"""
        if not self._initialized or self._engine is None:
            raise DatabaseConnectionError(
                "Database not initialized. Call database.initialize() first."
            )
        return self._engine
    
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized
    
    def close(self):
        """Close all database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._SessionLocal = None
            self._initialized = False


# Global singleton instance
database = Database()

