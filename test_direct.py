"""
Test all tools directly without any MCP protocol.
Just imports and calls the functions like normal Python.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load env first
from dotenv import load_dotenv
load_dotenv()

import json

print("=" * 60)
print("MCP MSSQL - Direct Tool Tests")
print("=" * 60)

# ── Test 1: Database Connection ────────────────────────────────
print("\n[TEST 1] Database Connection...")
try:
    from mcp_mssql.database.connection import engine
    with engine.connect() as conn:
        print("  ✅ Connected to SQL Server successfully")
except Exception as e:
    print(f"  ❌ Connection failed: {e}")
    sys.exit(1)

# ── Test 2: Schema Introspection ──────────────────────────────
print("\n[TEST 2] Schema Introspection...")
try:
    from mcp_mssql.database.schema_cache import schema_cache
    schema = schema_cache.get_full_schema()
    print(f"  ✅ Found {len(schema)} tables")
    for table_name in list(schema.keys())[:5]:
        cols = len(schema[table_name]['columns'])
        fks  = len(schema[table_name]['foreign_keys'])
        print(f"     → {table_name} ({cols} columns, {fks} FK)")
except Exception as e:
    print(f"  ❌ Schema failed: {e}")

# ── Test 3: Simple Query ───────────────────────────────────────
print("\n[TEST 3] Simple Query...")
try:
    from mcp_mssql.database.executor import executor
    result = executor.execute("SELECT TOP 5 * FROM INFORMATION_SCHEMA.TABLES")
    print(f"  ✅ Query returned {result['row_count']} rows in {result['execution_time_ms']}ms")
    for row in result['rows']:
        print(f"     → {row}")
except Exception as e:
    print(f"  ❌ Query failed: {e}")

# ── Test 4: Complex JOIN Query ─────────────────────────────────
print("\n[TEST 4] Complex JOIN Query...")
try:
    complex_query = """
    SELECT
        t.TABLE_SCHEMA,
        t.TABLE_NAME,
        COUNT(c.COLUMN_NAME)    AS column_count,
        SUM(CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END) AS nullable_cols,
        SUM(CASE WHEN c.IS_NULLABLE = 'NO'  THEN 1 ELSE 0 END) AS required_cols
    FROM INFORMATION_SCHEMA.TABLES t
    JOIN INFORMATION_SCHEMA.COLUMNS c
        ON t.TABLE_NAME   = c.TABLE_NAME
        AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
    WHERE t.TABLE_TYPE = 'BASE TABLE'
    GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
    ORDER BY column_count DESC
    """
    result = executor.execute(complex_query)
    print(f"  ✅ Complex query returned {result['row_count']} rows in {result['execution_time_ms']}ms")
    for row in result['rows'][:3]:
        print(f"     → {row}")
except Exception as e:
    print(f"  ❌ Complex query failed: {e}")

# ── Test 5: Query Validator ────────────────────────────────────
print("\n[TEST 5] Query Validator...")
try:
    from mcp_mssql.database.validator import validator

    # Should PASS
    ok, msg = validator.validate("SELECT * FROM Users WHERE Id = 1")
    print(f"  {'✅' if ok else '❌'} Safe SELECT: {msg}")

    # Should BLOCK
    ok, msg = validator.validate("DROP TABLE Users")
    print(f"  {'✅' if not ok else '❌'} DROP blocked: {msg}")

    # Should BLOCK
    ok, msg = validator.validate("EXEC xp_cmdshell('dir')")
    print(f"  {'✅' if not ok else '❌'} xp_cmdshell blocked: {msg}")

    # Should BLOCK
    ok, msg = validator.validate("SELECT 1; DROP TABLE Users")
    print(f"  {'✅' if not ok else '❌'} Multi-statement blocked: {msg}")

except Exception as e:
    print(f"  ❌ Validator test failed: {e}")

# ── Test 6: MCP Tool Functions ─────────────────────────────────
print("\n[TEST 6] MCP Tool Functions...")
try:
    from mcp_mssql.tools.query_tools import (
        get_database_schema,
        execute_sql_query,
        get_table_sample,
        find_related_tables,
    )

    # Schema tool
    schema_json = get_database_schema(table_filter="")
    schema_data = json.loads(schema_json)
    print(f"  ✅ get_database_schema: {len(schema_data)} tables")

    # Execute tool
    result_json = execute_sql_query("SELECT TOP 3 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
    result_data = json.loads(result_json)
    print(f"  ✅ execute_sql_query: {result_data['row_count']} rows")

    # Sample tool — replace 'Users' with any real table in your DB
    first_table = list(schema_data.keys())[0].split(".")[-1]
    sample_json = get_table_sample(table_name=first_table, sample_size=3)
    sample_data = json.loads(sample_json)
    print(f"  ✅ get_table_sample ({first_table}): {sample_data['row_count']} rows")

    # Related tables
    related_json = find_related_tables(table_name=first_table)
    related_data = json.loads(related_json)
    print(f"  ✅ find_related_tables ({first_table}): {related_data['row_count']} relationships")

except Exception as e:
    print(f"  ❌ Tool test failed: {e}")

print("\n" + "=" * 60)
print("All tests complete.")
print("=" * 60)