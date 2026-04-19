# Interactive Knowledge Hub — Project Plan

## Overview

A self-hosted, desktop-oriented web application for organizing and reading interactive HTML and PDF files, with full-text search, folder management, inline commenting, and optional Ollama AI assistance.

---

## Architecture

```
knowledge-hub/
├── docker-compose.yml
├── .env
├── frontend/                  # Standalone HTML (served via nginx on port 3006)
│   └── index.html
├── backend/                   # FastAPI on port 3007
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── folders.py
│   │   ├── topics.py
│   │   ├── comments.py
│   │   └── search.py
│   ├── requirements.txt
│   └── Dockerfile
└── data/                      # Mounted to host
    ├── db/
    │   └── knowledge.db       # SQLite database
    └── uploads/               # Uploaded HTML and PDF files
```

---

## Tech Stack

| Layer     | Technology                                   |
|-----------|----------------------------------------------|
| Frontend  | Vanilla HTML + CSS + JS (single file, port 3006) |
| Backend   | FastAPI + Python (port 3007)                 |
| Database  | SQLite (via SQLAlchemy)                      |
| File storage | Local filesystem (`./data/uploads/`)      |
| PDF reading | PDF.js (CDN, in-browser)                  |
| Full-text search | SQLite FTS5                          |
| AI assist | Ollama HTTP API (host: `http://localhost:11434`) |
| Container | Docker + Docker Compose                      |

---

## Environment Variables (`.env`)

```env
# Autosave interval in milliseconds (default: 5000 = 5 seconds)
AUTOSAVE_INTERVAL_MS=5000

# Ollama configuration
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3

# Ports
FRONTEND_PORT=3006
BACKEND_PORT=3007
```

---

## Database Schema (SQLite)

### `folders`
| Column      | Type    | Notes                        |
|-------------|---------|------------------------------|
| id          | INTEGER | Primary key                  |
| name        | TEXT    | Folder display name          |
| parent_id   | INTEGER | NULL = root; FK → folders.id |
| created_at  | TEXT    | ISO timestamp                |

### `topics`
| Column      | Type    | Notes                                 |
|-------------|---------|---------------------------------------|
| id          | INTEGER | Primary key                           |
| name        | TEXT    | User-defined topic name               |
| folder_id   | INTEGER | FK → folders.id (nullable = root)     |
| file_type   | TEXT    | `html` or `pdf`                       |
| file_path   | TEXT    | Relative path in `data/uploads/`      |
| extracted_text | TEXT | Full text for FTS                  |
| last_opened | TEXT    | ISO timestamp                         |
| created_at  | TEXT    | ISO timestamp                         |
| updated_at  | TEXT    | ISO timestamp                         |

### `comments`
| Column      | Type    | Notes                          |
|-------------|---------|--------------------------------|
| id          | INTEGER | Primary key                    |
| topic_id    | INTEGER | FK → topics.id                 |
| content     | TEXT    | Comment/note text              |
| created_at  | TEXT    | ISO timestamp                  |
| updated_at  | TEXT    | ISO timestamp                  |

### SQLite FTS5 Virtual Table
- `topics_fts` mirrors `topics(id, name, extracted_text)` for full-text search.

---

## Backend API Endpoints (FastAPI)

### Folders
| Method | Path                        | Description                   |
|--------|-----------------------------|-------------------------------|
| GET    | `/folders`                  | List all folders (tree)       |
| POST   | `/folders`                  | Create folder                 |
| PUT    | `/folders/{id}`             | Rename folder                 |
| DELETE | `/folders/{id}`             | Delete folder (cascade)       |

### Topics
| Method | Path                        | Description                   |
|--------|-----------------------------|-------------------------------|
| GET    | `/topics`                   | List all topics               |
| GET    | `/topics/recent`            | Recent opened topics          |
| GET    | `/topics/{id}`              | Get single topic              |
| POST   | `/topics`                   | Upload new topic (multipart)  |
| PUT    | `/topics/{id}`              | Update topic name/folder      |
| DELETE | `/topics/{id}`              | Delete topic + file           |
| PATCH  | `/topics/{id}/file`         | Re-upload / replace file      |
| PATCH  | `/topics/{id}/content`      | Edit HTML content in-place    |
| PATCH  | `/topics/{id}/opened`       | Update last_opened timestamp  |
| GET    | `/topics/{id}/file`         | Serve the file                |

### Comments
| Method | Path                              | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | `/topics/{id}/comments`           | List comments for topic  |
| POST   | `/topics/{id}/comments`           | Add comment              |
| PUT    | `/topics/{id}/comments/{cid}`     | Edit comment             |
| DELETE | `/topics/{id}/comments/{cid}`     | Delete comment           |

### Search
| Method | Path                | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | `/search?q=...`     | Full-text search across topics       |

### Ollama (Optional)
| Method | Path                    | Description                          |
|--------|-------------------------|--------------------------------------|
| POST   | `/ollama/suggest`       | Suggest topic name + folder from file text |

---

## Frontend UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Search bar (full width topbar)              [Upload +]  │
├──────────────────┬──────────────────────────────────────────┤
│ Navigation (left)│  Main Content Area                       │
│                  │                                          │
│ 📁 Root          │  Recent Files (cards row)                │
│  ├ 📁 Folder A   │  ─────────────────────────────────────   │
│  │  ├ 📁 Sub A1  │  All Topics / Search Results (grid)      │
│  │  └ 📄 Topic   │                                          │
│  └ 📁 Folder B   │                                          │
│    └ 📄 Topic    │                                          │
│                  │                                          │
│ [+ New Folder]   │                                          │
└──────────────────┴──────────────────────────────────────────┘
```

### Pages / Views
1. **Home** — Recent files row + all topics grid + search results
2. **Topic Viewer** — Renders HTML (iframe) or PDF (PDF.js), with a collapsible comments panel on the right
3. **Upload Modal** — File picker, topic name input, folder selector, optional Ollama suggest button
4. **Edit HTML Modal** — In-browser code editor (CodeMirror via CDN) for editing uploaded HTML

### Key UI Features
- Left sidebar: collapsible folder tree with right-click context menu (create / rename / delete)
- Top search bar: live search with debounce, highlights matches
- Recent files: horizontal scroll row showing last N opened topics
- Topic cards: thumbnail preview (iframe screenshot or first 200 chars), file type badge
- Comments panel: sticky sidebar inside viewer, autosave every N seconds (from `.env`)
- Upload modal: drag-and-drop zone, Ollama suggest button (optional, gracefully disabled if Ollama unreachable)

---

## Docker Compose

```yaml
services:
  frontend:
    image: nginx:alpine
    ports:
      - "3006:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro

  backend:
    build: ./backend
    ports:
      - "3007:3007"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"   # allows Ollama on host
```

All persistent data (`data/db/` and `data/uploads/`) is mounted from the host directory so it survives container restarts.

---

## Implementation Phases

### Phase 1 — Backend Foundation
- FastAPI app scaffold, SQLite + SQLAlchemy setup
- Folder CRUD endpoints
- Topic upload, serve, delete endpoints
- FTS5 full-text search

### Phase 2 — Frontend Core
- Single `index.html` with sidebar, topbar, home grid
- Folder tree (create / rename / delete)
- Upload modal (HTML + PDF)
- Topic viewer (iframe for HTML, PDF.js for PDF)

### Phase 3 — Comments & Autosave
- Comment panel in viewer
- Autosave loop (interval from `.env` exposed to frontend via `/config` endpoint)
- Backend comment CRUD

### Phase 4 — Search & Recent
- Full-text search wired to topbar
- Recent files endpoint + UI row

### Phase 5 — Advanced Features
- Re-upload / replace file
- In-browser HTML editor (CodeMirror)
- Ollama integration (suggest name + folder)
- `.env` tunables (autosave interval, Ollama URL/model)

### Phase 6 — Docker & Polish
- Dockerfiles + `docker-compose.yml`
- `.env.example`
- Final UI polish and responsive layout

---

## Notes & Decisions

- **No framework dependency on frontend**: The entire frontend is a single `index.html` file loaded by nginx, using vanilla JS + CDN libraries (PDF.js, CodeMirror). This keeps it easy to deploy and modify.
- **Ollama is optional**: All Ollama calls are gracefully degraded. If the server is unreachable, the "Suggest" button is hidden/disabled.
- **Security scope**: This is a self-hosted, single-user tool — no authentication layer is included. Do not expose ports publicly without adding auth.
- **FTS5**: SQLite's built-in full-text search engine is used for fast keyword search across topic names and extracted text content.
- **PDF text extraction**: Extracted on upload server-side using `pypdf` (Python) for FTS indexing. PDF rendering in the browser uses PDF.js.
