# ─────────────────────────────────────────────────────────────
# Stage 1: Builder
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install build tools needed for pyodbc
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    gnupg2 \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Create venv using the builder's own pip — do NOT upgrade pip separately
RUN python -m venv /opt/venv

# Use venv pip directly via full path — avoids any PATH confusion
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install dependencies into venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# ─────────────────────────────────────────────────────────────
# Stage 2: Runtime
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL description="MCP Server for MS SQL Server"
LABEL version="1.0.0"

# Install ODBC runtime only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    curl \
    gnupg2 \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder — fully built with all dependencies
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser -d /app -s /bin/bash mcpuser

WORKDIR /app

# Copy application source
COPY src/ ./src/
COPY run.py .

RUN chown -R mcpuser:mcpuser /app

USER mcpuser

# Use venv binaries directly — no PATH tricks needed
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRANSPORT=sse
ENV HOST=127.0.0.1
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8000

CMD ["/opt/venv/bin/python", "run.py"]