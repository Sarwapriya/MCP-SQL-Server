from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    MSSQL_SERVER: str = Field(default="localhost")
    MSSQL_DATABASE: str = Field(default="master")
    MSSQL_USERNAME: str = Field(default="sa")
    MSSQL_PASSWORD: str = Field(default="your_password")
    MSSQL_PORT: int = Field(default=1433)
    MSSQL_DRIVER: str = Field(default="ODBC Driver 18 for SQL Server")
    MSSQL_ENCRYPT: bool = Field(default=True)
    MSSQL_TRUST_SERVER_CERT: bool = Field(default=False)

    # Optional second named connection ("secondary") — set MSSQL2_SERVER to enable it.
    MSSQL2_SERVER: Optional[str] = Field(default=None)
    MSSQL2_DATABASE: str = Field(default="master")
    MSSQL2_USERNAME: str = Field(default="sa")
    MSSQL2_PASSWORD: str = Field(default="")
    MSSQL2_PORT: int = Field(default=1433)
    MSSQL2_DRIVER: str = Field(default="ODBC Driver 18 for SQL Server")
    MSSQL2_ENCRYPT: bool = Field(default=True)
    MSSQL2_TRUST_SERVER_CERT: bool = Field(default=False)

    POOL_SIZE: int = Field(default=10)
    POOL_MAX_OVERFLOW: int = Field(default=20)
    POOL_TIMEOUT: int = Field(default=30)
    POOL_RECYCLE: int = Field(default=3600)

    MAX_ROWS: int = Field(default=10000)
    QUERY_TIMEOUT: int = Field(default=120)
    ALLOW_WRITE_OPERATIONS: bool = Field(default=False)
    ALLOWED_SCHEMAS: List[str] = Field(default=["dbo"])

    REDIS_URL: str = Field(default="redis://localhost:6379")
    REDIS_ENABLED: bool = Field(default=False)
    SCHEMA_CACHE_TTL: int = Field(default=3600)

    LOG_LEVEL: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()


class ConnectionSettings:
    def __init__(self, *, server: str, database: str, username: str, password: str,
                 port: int, driver: str, encrypt: bool, trust_server_cert: bool):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.driver = driver
        self.encrypt = encrypt
        self.trust_server_cert = trust_server_cert


CONNECTIONS: dict[str, ConnectionSettings] = {
    "primary": ConnectionSettings(
        server=settings.MSSQL_SERVER,
        database=settings.MSSQL_DATABASE,
        username=settings.MSSQL_USERNAME,
        password=settings.MSSQL_PASSWORD,
        port=settings.MSSQL_PORT,
        driver=settings.MSSQL_DRIVER,
        encrypt=settings.MSSQL_ENCRYPT,
        trust_server_cert=settings.MSSQL_TRUST_SERVER_CERT,
    ),
}

if settings.MSSQL2_SERVER:
    CONNECTIONS["secondary"] = ConnectionSettings(
        server=settings.MSSQL2_SERVER,
        database=settings.MSSQL2_DATABASE,
        username=settings.MSSQL2_USERNAME,
        password=settings.MSSQL2_PASSWORD,
        port=settings.MSSQL2_PORT,
        driver=settings.MSSQL2_DRIVER,
        encrypt=settings.MSSQL2_ENCRYPT,
        trust_server_cert=settings.MSSQL2_TRUST_SERVER_CERT,
    )