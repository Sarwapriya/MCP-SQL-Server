C:\Projects\mcp-mssql\
├── src\
│   └── mcp_mssql\
│       ├── __init__.py
│       ├── server.py
│       ├── config.py
│       ├── database\
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   ├── executor.py
│       │   ├── schema_cache.py
│       │   └── validator.py
│       └── tools\
│           ├── __init__.py
│           └── query_tools.py
├── requirements.txt
├── .env
└── run.py


https://claude.ai/share/1d5b820c-c063-4c9b-bfda-5ae852f438fa

Rebuild
# Full clean rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs -f mcp-mssql

# local mcp client config
    "mssql": {
      "command": "D:\\Projects\\AI\\mcp_mssql_py-main\\mcp_mssql_py-main\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\Projects\\AI\\mcp_mssql_py-main\\mcp_mssql_py-main\\run.py"
      ],
      "env": {
        "MSSQL_SERVER": "127.0.0.1",
        "MSSQL_DATABASE": "demo_db",
        "MSSQL_USERNAME": "sa",
        "MSSQL_PASSWORD": "YourStrong!Passw0rd"
      },
      "url":"http://localhost:8000/sse"
    }


# docker mcp client config
    "mssql": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "--env-file", "D:\\Projects\\AI\\mcp_mssql_py-main\\mcp_mssql_py-main\\.env",
        "-e", "TRANSPORT=stdio",
        "mcp-mssql-mcp-mssql:latest"
      ]
    }


# Claude local MCP configuration

{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\User\\Desktop",
        "C:\\Users\\User\\Downloads"
      ]
    },
    "MCP_DOCKER": {
      "command": "docker",
      "args": [
        "mcp",
        "gateway",
        "run"
      ],
      "env": {
        "LOCALAPPDATA": "C:\\Users\\User\\AppData\\Local",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles": "C:\\Program Files"
      }
    },
    "duckduckgo": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "mcp/duckduckgo"
      ]
    },
"mssql": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "--env-file", "D:\\Projects\\AI\\mcp_mssql_py-main\\mcp_mssql_py-main\\.env",
        "-e", "TRANSPORT=stdio",
        "mcp-mssql-mcp-mssql:latest"
      ]
    }
  },
  "preferences": {
    "sidebarMode": "chat",
    "coworkScheduledTasksEnabled": false
  }
}