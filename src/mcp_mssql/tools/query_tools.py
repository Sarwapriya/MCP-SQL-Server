import json
from fastmcp import FastMCP
from mcp_mssql.config import CONNECTIONS
from mcp_mssql.database.executor import executor
from mcp_mssql.database.schema_cache import schema_cache

mcp = FastMCP(
    name="MSSQL Intelligence Server",
    instructions="""
    You have access to one or more MS SQL Server databases, identified by a `connection` name.
    Call list_connections first if you don't already know which connections are available.
    ALWAYS call get_database_schema (for the right connection) first before writing any query.
    Use find_related_tables to discover JOIN paths.
    Use execute_parameterized_query for any user-supplied values.
    """,
)

@mcp.tool(description="List configured SQL Server connections by name (use as the `connection` argument on other tools).")
def list_connections() -> str:
    return json.dumps({
        name: {"server": conn.server, "database": conn.database}
        for name, conn in CONNECTIONS.items()
    }, indent=2)


@mcp.tool(description="Get full schema: tables, columns, PKs, FK relationships. Call this FIRST.")
def get_database_schema(table_filter: str = "", include_relationships: bool = True, connection: str = "primary") -> str:
    schema = schema_cache.get_full_schema(connection)
    if table_filter:
        schema = {k: v for k, v in schema.items() if table_filter.lower() in k.lower()}
    if not include_relationships:
        schema = {k: {"columns": v["columns"]} for k, v in schema.items()}
    return json.dumps(schema, indent=2)


@mcp.tool(description="Execute T-SQL. Supports CTEs, window functions, multi-table JOINs, subqueries.")
def execute_sql_query(query: str, description: str = "", connection: str = "primary") -> str:
    try:
        return json.dumps(executor.execute(query, connection=connection), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(description="Execute parameterized T-SQL safely. Use :param_name syntax.")
def execute_parameterized_query(query_template: str, parameters: dict, connection: str = "primary") -> str:
    try:
        return json.dumps(executor.execute(query_template, parameters, connection=connection), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(description="Get sample rows from a table to understand data shape.")
def get_table_sample(table_name: str, schema_name: str = "dbo", sample_size: int = 10, connection: str = "primary") -> str:
    sample_size = min(sample_size, 100)
    query = f"SELECT TOP {sample_size} * FROM [{schema_name}].[{table_name}] WITH (NOLOCK)"
    try:
        return json.dumps(executor.execute(query, connection=connection), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(description="Find all tables related to a given table via foreign keys.")
def find_related_tables(table_name: str, connection: str = "primary") -> str:
    query = """
    SELECT
        OBJECT_NAME(fkc.parent_object_id)                           AS child_table,
        COL_NAME(fkc.parent_object_id, fkc.parent_column_id)       AS child_column,
        OBJECT_NAME(fkc.referenced_object_id)                       AS parent_table,
        COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS parent_column,
        fk.name                                                      AS fk_name
    FROM sys.foreign_key_columns fkc
    JOIN sys.foreign_keys fk ON fkc.constraint_object_id = fk.object_id
    WHERE OBJECT_NAME(fkc.parent_object_id)     = :table_name
       OR OBJECT_NAME(fkc.referenced_object_id) = :table_name
    """
    try:
        return json.dumps(executor.execute(query, {"table_name": table_name}, connection=connection), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(description="Get XML execution plan for query performance diagnosis.")
def get_query_execution_plan(query: str, connection: str = "primary") -> str:
    try:
        return json.dumps(executor.get_execution_plan(query, connection=connection))
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(description="Refresh schema cache after DDL changes.")
def refresh_schema_cache(connection: str = "primary") -> str:
    schema_cache.invalidate(connection)
    schema = schema_cache.get_full_schema(connection)
    return json.dumps({"status": "refreshed", "connection": connection, "tables": len(schema)})
