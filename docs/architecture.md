# Architecture

## System Overview

```mermaid
graph TB
    Agent["AI Agent<br/>(Claude, etc)"]
    Config["MCP Config<br/>(one-time setup)"]
    Server["devmcp-context Server"]
    Storage["File Storage<br/>(ai-context/)"]
    Editor["You<br/>(Edit Files)"]
    
    Agent -->|discovers| Server
    Agent -->|calls tools| Server
    Config -->|registers| Server
    Server -->|reads/writes| Storage
    Editor -->|manual edits| Storage
    Storage -->|state changes| Server
    
    style Agent fill:#e8e8e8
    style Config fill:#e8e8e8
    style Server fill:#60a5fa,color:#0f172a
    style Storage fill:#e8e8e8
    style Editor fill:#e8e8e8
```

**Key insight:** The agent doesn't manage the server lifecycle. Once configured, the server runs automatically when the agent connects.

## Request Flow

```mermaid
sequenceDiagram
    participant Agent
    participant Server as devmcp-context Server
    participant Storage as ai-context/
    
    Agent->>Server: context_session_start()
    Server->>Storage: Read project.md + decisions.md
    Storage-->>Server: Full entries
    Server->>Storage: Read all .md files for index
    Storage-->>Server: Summary data
    Server-->>Agent: Auto-loaded entries + compact index
    
    Note over Agent: Agent reads memory, starts work
    
    Agent->>Server: context_save("decisions", "key", "value", what_worked="...", superseded_by="old-key")
    Server->>Storage: Write to decisions.md
    Storage-->>Server: Success
    Server-->>Agent: Saved
    
    Agent->>Server: context_search("keyword")
    Server->>Storage: Read all .md files
    Storage-->>Server: Markdown content
    Server->>Server: Parse, skip superseded, search
    Server-->>Agent: [matching entries]
    
    Note over Agent: Session ends
    
    Agent->>Server: context_log_session_recall()
    Server->>Storage: Append to _session_log.md
    Server-->>Agent: Logged
```

## Memory Organization

```mermaid
graph LR
    Root["ai-context/"]
    Root --> Project["project.md<br/>(never expires)"]
    Root --> Decisions["decisions.md<br/>(never expires)"]
    Root --> Errors["errors.md<br/>(expires 30 days)"]
    Root --> Tasks["tasks.md<br/>(expires 14 days)"]
    Root --> Ephemeral["ephemeral.md<br/>(expires 1 day)"]
    Root --> Meta["_meta.md<br/>(metadata)"]
    
    style Root fill:#60a5fa,color:#0f172a
    style Project fill:#e8e8e8
    style Decisions fill:#e8e8e8
    style Errors fill:#ffe8e8
    style Tasks fill:#fff8e8
    style Ephemeral fill:#f0e8ff
    style Meta fill:#e8e8e8
```

Each file contains entries in Markdown format. Entries include metadata (TTL, creation date, tags) and are parsed on each request.

## Tool Ecosystem

```mermaid
graph TB
    Server["devmcp-context Server"]
    
    T1["context_session_start<br/>(Auto-Recall)"]
    T2["context_save<br/>(Create/Update)"]
    T3["context_load<br/>(Retrieve)"]
    T4["context_search<br/>(Find)"]
    T5["context_delete<br/>(Remove)"]
    T6["context_status<br/>(Stats)"]
    T7["context_purge_expired<br/>(Cleanup)"]
    T8["context_log_session_recall<br/>(Metric)"]
    
    Server --> T1
    Server --> T2
    Server --> T3
    Server --> T4
    Server --> T5
    Server --> T6
    Server --> T7
    Server --> T8
    
    style Server fill:#60a5fa,color:#0f172a
    style T1 fill:#34d399,color:#0f172a
    style T2 fill:#e8e8e8
    style T3 fill:#e8e8e8
    style T4 fill:#e8e8e8
    style T5 fill:#e8e8e8
    style T6 fill:#e8e8e8
    style T7 fill:#e8e8e8
    style T8 fill:#fbbf24,color:#0f172a
```

All tools operate on the same file-based storage. No database, no complexity.

## Data Model

```mermaid
classDiagram
    class ContextEntry {
        +str key
        +str value
        +list tags
        +int ttl_days
        +datetime created_at
        +datetime updated_at
        +str what_worked
        +str what_failed
        +str superseded_by
        +bool is_expired()
        +bool is_superseded()
        +int age_days()
    }
    
    class Category {
        +project : str
        +decisions : str
        +errors : str
        +tasks : str
        +ephemeral : str
    }
    
    class CategoryFile {
        +Category category
        +list entries
        +list active_entries()
    }
    
    ContextEntry --> Category
    CategoryFile --> ContextEntry
```

- `created_at` is preserved across updates (not reset)
- `superseded_by` points to the successor entry; recall skips superseded entries
- `what_worked` / `what_failed` are only valid for `decisions` and `errors` categories
- Tags use pipe `|` as delimiter in markdown files (not comma)

## Deployment Models

```mermaid
graph TB
    subgraph Local["Local Development"]
        L1["User's Project"]
        L2["ai-context/"]
        L3["devmcp-context (local)"]
        L1 --> L3
        L3 --> L2
    end
    
    subgraph Agent["Agent Integration"]
        A1["Claude Desktop / Node.js / Python"]
        A2["MCP Config"]
        A3["devmcp-context Server"]
        A1 --> A2
        A2 --> A3
    end
    
    subgraph Production["Production"]
        P1["Docker Container"]
        P2["Persistent Volume"]
        P3["devmcp-context"]
        P1 --> P3
        P3 --> P2
    end
    
    style L1 fill:#e8e8e8
    style L2 fill:#f0f0f0
    style L3 fill:#60a5fa,color:#0f172a
    style A1 fill:#e8e8e8
    style A2 fill:#e8e8e8
    style A3 fill:#60a5fa,color:#0f172a
    style P1 fill:#e8e8e8
    style P2 fill:#f0f0f0
    style P3 fill:#60a5fa,color:#0f172a
```

Supports dev (CLI), agent-integrated (MCP config), and containerized deployments.
