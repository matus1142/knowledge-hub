# Knowledge Hub

A self-hosted interactive knowledge management application for organizing, reading, and annotating HTML and PDF files.

## Features

- 📁 Hierarchical folder/subfolder organization
- 🌐 Render standalone HTML files in an isolated iframe
- 📕 Read PDF files with page navigation and zoom
- 🔍 Full-text search across all uploaded content (SQLite FTS5)
- 💬 Add notes/comments to any topic with autosave
- ✏️ Edit HTML source directly in the browser (CodeMirror)
- 🔄 Re-upload and replace existing files
- 🕐 Recent files quick access
- ✨ Optional Ollama AI suggestions for topic name and folder

## Quick Start

```bash
# 1. Clone or copy this project
# 2. (Optional) Edit .env to configure ports, Ollama, autosave interval
cp .env.example .env

# 3. Build and start
docker compose up -d --build

# 4. Open browser
open http://localhost:3006
```

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTOSAVE_INTERVAL_MS` | `5000` | Comment autosave interval in milliseconds |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model to use for suggestions |
| `FRONTEND_PORT` | `3006` | Frontend port |
| `BACKEND_PORT` | `3007` | Backend port |

## Architecture

- **Frontend**: Single `index.html` served by nginx on port 3006
- **Backend**: FastAPI + SQLite on port 3007
- **Data**: All data stored in `./data/` directory on the host

## Data Persistence

All data is stored in `./data/` on your host machine:
- `./data/db/knowledge.db` — SQLite database
- `./data/uploads/` — Uploaded HTML and PDF files

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Focus search bar |
| `Ctrl+U` / `Cmd+U` | Open upload modal |
| `Escape` | Close viewer / modal |

## API Reference

The backend API runs at `http://localhost:3007`. Interactive docs available at `http://localhost:3007/docs`.

## Ollama Integration (Optional)

If Ollama is running on your host machine, the app will automatically detect it and show an "✨ Suggest" button in the upload modal. It will suggest a topic name and the most appropriate folder based on the file content.

To use a different model, set `OLLAMA_MODEL` in your `.env` file.
