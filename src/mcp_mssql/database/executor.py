import time
import json
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from mcp_mssql.database.connection import get_engine
from mcp_mssql.database.validator import validator
from mcp_mssql.config import settings

log = structlog.get_logger(__name__)

class QueryExecutor:

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def execute(self, query: str, params: dict | None = None, connection: str = "primary") -> dict:
        ok, msg = validator.validate(query)
        if not ok:
            raise ValueError(f"Validation failed: {msg}")

        engine = get_engine(connection)

        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text(f"SET ROWCOUNT {settings.MAX_ROWS}"))
            result = conn.execute(text(query), params or {})
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        log.info("query.executed", connection=connection, rows=len(rows), elapsed_ms=elapsed_ms)

        return {
            "connection": connection,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": elapsed_ms,
            "truncated": len(rows) == settings.MAX_ROWS,
        }

    def get_execution_plan(self, query: str, connection: str = "primary") -> dict:
        ok, msg = validator.validate(query)
        if not ok:
            raise ValueError(f"Validation failed: {msg}")

        engine = get_engine(connection)

        with engine.connect() as conn:
            conn.execute(text("SET SHOWPLAN_XML ON"))
            plan_result = conn.execute(text(query))
            plan_xml = plan_result.fetchone()[0]
            conn.execute(text("SET SHOWPLAN_XML OFF"))

        return {"connection": connection, "plan_xml": plan_xml}

executor = QueryExecutor()
