import json
from sqlalchemy import text
from mcp_mssql.database.connection import get_engine
from mcp_mssql.config import settings
import structlog

log = structlog.get_logger(__name__)

_local_cache: dict = {}

_redis = None
if settings.REDIS_ENABLED:
    try:
        import redis
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        log.warning("redis.init.failed", error=str(e))

class SchemaCache:
    @staticmethod
    def _key(connection: str) -> str:
        return f"mssql:schema:{connection}"

    def get_full_schema(self, connection: str = "primary") -> dict:
        key = self._key(connection)

        if _redis:
            try:
                cached = _redis.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                log.warning("redis.get.failed", error=str(e))

        if key in _local_cache:
            return _local_cache[key]

        schema = self._introspect(connection)
        self._store(connection, schema)
        return schema

    def _store(self, connection: str, schema: dict):
        key = self._key(connection)
        if _redis:
            try:
                _redis.setex(key, settings.SCHEMA_CACHE_TTL, json.dumps(schema))
                return
            except Exception:
                pass
        _local_cache[key] = schema

    def invalidate(self, connection: str = "primary"):
        key = self._key(connection)
        if _redis:
            try:
                _redis.delete(key)
            except Exception:
                pass
        _local_cache.pop(key, None)

    def _introspect(self, connection: str) -> dict:
        log.info("schema.introspection.start", connection=connection)
        engine = get_engine(connection)
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    t.TABLE_SCHEMA, t.TABLE_NAME,
                    c.COLUMN_NAME, c.DATA_TYPE,
                    c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE,
                    CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES' ELSE 'NO' END AS IS_PK
                FROM INFORMATION_SCHEMA.TABLES t
                JOIN INFORMATION_SCHEMA.COLUMNS c
                    ON t.TABLE_NAME = c.TABLE_NAME
                    AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
                LEFT JOIN (
                    SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                        ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ) pk ON pk.TABLE_NAME = t.TABLE_NAME
                     AND pk.COLUMN_NAME = c.COLUMN_NAME
                WHERE t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
            """))

            schema: dict = {}
            for r in rows:
                key = f"{r.TABLE_SCHEMA}.{r.TABLE_NAME}"
                if key not in schema:
                    schema[key] = {"columns": [], "foreign_keys": []}
                schema[key]["columns"].append({
                    "name": r.COLUMN_NAME,
                    "type": r.DATA_TYPE,
                    "nullable": r.IS_NULLABLE == "YES",
                    "primary_key": r.IS_PK == "YES",
                })

            fks = conn.execute(text("""
                SELECT
                    fk.name             AS fk_name,
                    tp.name             AS parent_table,
                    cp.name             AS parent_column,
                    tr.name             AS ref_table,
                    cr.name             AS ref_column
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc
                    ON fk.object_id = fkc.constraint_object_id
                JOIN sys.tables tp ON fkc.parent_object_id    = tp.object_id
                JOIN sys.columns cp ON fkc.parent_object_id   = cp.object_id
                    AND fkc.parent_column_id    = cp.column_id
                JOIN sys.tables tr ON fkc.referenced_object_id  = tr.object_id
                JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id
                    AND fkc.referenced_column_id = cr.column_id
            """))
            for r in fks:
                key = f"dbo.{r.parent_table}"
                if key in schema:
                    schema[key]["foreign_keys"].append({
                        "fk_name": r.fk_name,
                        "column": r.parent_column,
                        "references_table": r.ref_table,
                        "references_column": r.ref_column,
                    })

        log.info("schema.introspection.done", connection=connection, tables=len(schema))
        return schema

schema_cache = SchemaCache()