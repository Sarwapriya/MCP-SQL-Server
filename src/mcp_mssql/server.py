import sys
import os
import logging
import structlog


def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


configure_logging()

from mcp_mssql.config import settings
from mcp_mssql.tools.query_tools import mcp

log = structlog.get_logger(__name__)


def main():
    transport = os.getenv("TRANSPORT", "stdio")
    host      = os.getenv("HOST", "0.0.0.0")   # 0.0.0.0 required for Docker
    port      = int(os.getenv("PORT", "8000"))

    log.info(
        "mcp.server.starting",
        transport=transport,
        host=host,
        port=port,
        database=settings.MSSQL_DATABASE,
        server=settings.MSSQL_SERVER,
    )

    if transport == "stdio":
        # Claude Desktop — spawns process, pipes JSON-RPC via stdin/stdout
        mcp.run(transport="stdio")

    elif transport == "streamable-http":
        # Docker / local HTTP — MCP over Streamable HTTP
        # Client connects to: http://localhost:8000/mcp/
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
        )

    else:
        log.error(
            "mcp.server.unknown_transport",
            transport=transport,
            valid_options=["stdio", "streamable-http"],
        )
        sys.exit(1)


if __name__ == "__main__":
    main()