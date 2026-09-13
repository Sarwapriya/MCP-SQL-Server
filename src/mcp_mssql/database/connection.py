from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
import structlog
from mcp_mssql.config import settings, CONNECTIONS, ConnectionSettings

log = structlog.get_logger(__name__)


def build_connection_url(conn: ConnectionSettings) -> str:
    driver = conn.driver.replace(" ", "+")
    encrypt = "yes" if conn.encrypt else "no"
    trust = "yes" if conn.trust_server_cert else "no"
    return (
        f"mssql+pyodbc://{conn.username}:{conn.password}"
        f"@{conn.server},{conn.port}/{conn.database}"
        f"?driver={driver}&Encrypt={encrypt}&TrustServerCertificate={trust}"
    )


def _build_engine(name: str, conn: ConnectionSettings) -> Engine:
    engine = create_engine(
        build_connection_url(conn),
        poolclass=QueuePool,
        pool_size=settings.POOL_SIZE,
        max_overflow=settings.POOL_MAX_OVERFLOW,
        pool_timeout=settings.POOL_TIMEOUT,
        pool_recycle=settings.POOL_RECYCLE,
        pool_pre_ping=True,
        echo=False,
        connect_args={"timeout": settings.QUERY_TIMEOUT},
    )

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, _):
        log.info("db.connection.established", connection=name)

    return engine


ENGINES: dict[str, Engine] = {
    name: _build_engine(name, conn) for name, conn in CONNECTIONS.items()
}


def get_engine(connection: str = "primary") -> Engine:
    try:
        return ENGINES[connection]
    except KeyError:
        raise ValueError(
            f"Unknown connection '{connection}'. Available: {sorted(ENGINES)}"
        )


# Backward-compatible default engine/session for the primary connection.
engine = ENGINES["primary"]
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
