# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP (Model Context Protocol) server, built on `fastmcp`, that exposes one or more Microsoft SQL
Server databases as a set of tools an LLM client (e.g. Claude Desktop) can call: schema
introspection, ad-hoc/parameterized SQL execution, table sampling, FK relationship discovery, and
execution-plan retrieval. All tool definitions live in `src/mcp_mssql/tools/query_tools.py`;
everything else in `src/mcp_mssql/database/` is plumbing (connection registry, query validation,
execution, schema cache) that those tools call into.

## Commands

Setup (Windows, existing `.venv` already present in the repo):
```
.venv\Scripts\pip install -r requirements.txt
```

Run the server locally (stdio transport, for Claude Desktop):
```
python run.py
```
Run with a different transport (streamable-http, for network/Docker clients — served at `/mcp/`):
```
set TRANSPORT=streamable-http && set PORT=8000 && python run.py
```
Transport is chosen at runtime via the `TRANSPORT` env var (`stdio` or `streamable-http`); there is
no build/compile step.

Exercise the tools against a live database without going through the MCP protocol (this is the
closest thing to a test suite in this repo — there is no pytest/unittest setup):
```
python test_direct.py
```
This requires a working `.env` with real MSSQL connection details; it connects, introspects the
schema, runs sample queries, and exercises the validator and every tool function directly. There
is no way to run a "single test" — it's a linear script, not a test framework.

No linter or type-checker is configured to run from the CLI; `pyrightconfig.json` only sets up
`src` on the analysis path for editor tooling (Pylance/Pyright).

`requirements.lock` is a full `pip freeze` dump (UTF-16, includes transitive deps); it isn't
referenced by any command in this repo — `requirements.txt` is the actual source of truth for
setup and Docker builds.

Docker (see `mcp.bat` for the Windows-friendly wrappers around `docker compose`):
```
mcp.bat build     # docker compose build --no-cache
mcp.bat up        # docker compose up -d  (server on :8000, redis on :6379)
mcp.bat logs      # tail mcp-mssql container logs
mcp.bat restart   # restart just the mcp-mssql service
mcp.bat shell     # bash shell inside the container
mcp.bat down      # stop
mcp.bat clean     # docker compose down --rmi local --volumes --remove-orphans
```

## Configuration

All settings come from `src/mcp_mssql/config.py` (`pydantic-settings`), populated from a `.env`
file at repo root (loaded via `python-dotenv`) with env vars overriding. Key groups: `MSSQL_*`
(primary connection), `MSSQL2_*` (optional second connection, see below), `POOL_*` (SQLAlchemy
pool sizing — shared across all connections), `MAX_ROWS`/`QUERY_TIMEOUT`/`ALLOW_WRITE_OPERATIONS`
(query safety, also shared), `REDIS_*`/`SCHEMA_CACHE_TTL` (schema cache), `LOG_LEVEL`. There's a
single module-level `settings` instance imported everywhere — don't re-instantiate `Settings()`.

### Multiple SQL Server connections

The server can talk to more than one SQL Server from a single process. `config.py` builds a
`CONNECTIONS: dict[str, ConnectionSettings]` registry: `"primary"` always exists (from `MSSQL_*`);
`"secondary"` is added only if `MSSQL2_SERVER` is set (from `MSSQL2_*`). To add a third, extend
that pattern (a `MSSQL3_*` block + registry entry) rather than hardcoding another one-off.

Every tool in `query_tools.py` takes a `connection: str = "primary"` argument that flows through
to `executor.execute()` / `schema_cache.get_full_schema()`, which resolve it to a SQLAlchemy engine
via `database/connection.py`'s `get_engine(name)` (backed by `ENGINES: dict[str, Engine]`, one
engine built per configured connection at import time). The `list_connections` tool reports which
names are currently configured, so an LLM client can discover them before picking one. The schema
cache key is namespaced per connection (`mssql:schema:<name>`) so their entries don't collide in
Redis or the in-process fallback dict.

## Architecture

**Startup order matters in `server.py`**: logging (`structlog` + stdlib `logging`, both writing to
stderr so stdout stays clean for stdio JSON-RPC) is configured via `configure_logging()` *before*
`mcp_mssql.config` / `mcp_mssql.tools.query_tools` are imported, so that anything those modules log
at import time is already formatted correctly.

**Everything is a module-level singleton, instantiated at import time** — there's no DI container
or app factory:
- `database/connection.py` → `ENGINES` (one SQLAlchemy engine per configured connection, over
  `pyodbc`, `QueuePool`, `pool_pre_ping=True`) plus `get_engine(name)`; `engine` is kept as a
  backward-compatible alias for `ENGINES["primary"]`
- `database/validator.py` → `validator` (`QueryValidator`) — connection-agnostic, validates query text only
- `database/executor.py` → `executor` (`QueryExecutor`)
- `database/schema_cache.py` → `schema_cache` (`SchemaCache`)
- `tools/query_tools.py` → `mcp` (the `FastMCP` app) plus all `@mcp.tool` functions

**Request path for query execution**: an MCP tool in `query_tools.py` calls
`executor.execute(query, connection=...)`, which first runs `validator.validate()`, resolves the
named connection to an engine via `get_engine()`, then executes with a `tenacity` retry (3
attempts, exponential backoff), applying `SET ROWCOUNT {MAX_ROWS}` first. Results come back as a
JSON-serializable dict (`connection`, `columns`, `rows`, `row_count`, `execution_time_ms`,
`truncated`).

**Query safety is entirely in `validator.py`** and runs on every query regardless of which tool
called it: a regex blocklist (xp_ procs, `OPENROWSET`/`OPENDATASOURCE`, `BULK INSERT`, `EXEC(`,
`sp_executesql`, inline comments) followed by an `sqlglot` (t-sql dialect) parse that rejects
multi-statement input and — unless `ALLOW_WRITE_OPERATIONS=true` — rejects any statement whose
parsed type is a write op (`Insert`/`Update`/`Delete`/`Drop`/`Create`/`AlterTable`/
`TruncateTable`/`Merge`). Any new tool that runs SQL must go through `executor`/`validator`, not
raw `engine` calls, to keep this guarantee. Note: `settings.ALLOWED_SCHEMAS` exists in
`config.py` but is never read anywhere else — it does not actually restrict which schemas a query
can touch, despite the name.

**Schema cache (`schema_cache.py`)** introspects `INFORMATION_SCHEMA` (tables/columns/PKs) plus
`sys.foreign_keys` for FK relationships, per connection, and caches each connection's schema dict
under its own key (`mssql:schema:<connection>`) — in Redis if `REDIS_ENABLED`, otherwise in an
in-process dict. Cache is invalidated per connection by the `refresh_schema_cache` tool. Note the
FK-merge step in `_introspect()` hardcodes the `dbo` schema prefix when matching parent tables back
into the schema dict.

**Transports**: `stdio` is for Claude Desktop, which spawns the process and pipes JSON-RPC over
stdin/stdout. `streamable-http` is for Docker/networked clients, served at `http://host:port/mcp/`.
The Dockerfile is a two-stage build (builder installs `msodbcsql18` + compiles deps into a venv;
runtime stage installs only the ODBC runtime, copies the venv, and runs as a non-root `mcpuser`),
and `docker-compose.yml` wires the server together with a Redis container used for the schema
cache.
