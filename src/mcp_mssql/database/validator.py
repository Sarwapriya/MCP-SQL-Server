import re
import sqlglot
import sqlglot.expressions as exp
from mcp_mssql.config import settings

class QueryValidator:
    _DANGEROUS = [
        r"\bxp_\w+\b",
        r"\bOPENROWSET\b",
        r"\bOPENDATASOURCE\b",
        r"\bBULK\s+INSERT\b",
        r"\bEXEC\s*\(",
        r"\bsp_executesql\b",
        r"/\*.*?\*/",
    ]

    _WRITE_TYPES = {
        "Insert", "Update", "Delete", "Drop",
        "Create", "AlterTable", "TruncateTable", "Merge"
    }

    def validate(self, query: str) -> tuple[bool, str]:
        for pattern in self._DANGEROUS:
            if re.search(pattern, query, re.IGNORECASE | re.DOTALL):
                return False, f"Blocked pattern: {pattern}"

        try:
            statements = sqlglot.parse(query, dialect="tsql")
        except Exception as e:
            return False, f"Parse error: {e}"

        if len(statements) > 1:
            return False, "Multiple statements not allowed"

        stmt = statements[0]

        if not settings.ALLOW_WRITE_OPERATIONS:
            stmt_class = type(stmt).__name__
            if any(w in stmt_class for w in self._WRITE_TYPES):
                return False, f"Write operation '{stmt_class}' is disabled"

        return True, "OK"

validator = QueryValidator()