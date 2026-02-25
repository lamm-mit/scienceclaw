# Open Notebook

Self-hosted research platform (MIT license) — organizes PDFs, videos, audio, web pages, and text into searchable notebooks with AI-powered chat. NotebookLM alternative with full data ownership.

## Features

- **Multi-format ingestion**: PDFs, URLs, YouTube videos, audio files, raw text
- **AI chat**: Query notebooks in natural language with source citations
- **Podcast generation**: Multi-speaker audio synthesis from notebook content
- **Full-text + vector search**: Semantic and keyword search across all sources
- **16+ AI providers**: OpenAI, Anthropic, Ollama, Gemini, and more
- **REST API**: Full API on port 5055 for programmatic access

## Deployment

```bash
# Docker Compose (recommended)
git clone https://github.com/open-notebook/open-notebook
cd open-notebook
cp .env.example .env
# Edit .env: set AI provider API keys
docker compose up -d

# API available at: http://localhost:5055
```

## Scripts

Three scripts are available for programmatic interaction:

| Script | Purpose |
|--------|---------|
| `scripts/notebook_management.py` | Create, list, update, delete notebooks |
| `scripts/source_ingestion.py` | Add URLs, text, or file uploads |
| `scripts/chat_interaction.py` | Chat, search, and query notebooks |

## Quick Start

```bash
# Create a notebook
python3 scripts/notebook_management.py \
    --url http://localhost:5055 \
    --action create \
    --name "Alzheimer's Research"

# Add sources
python3 scripts/source_ingestion.py \
    --url http://localhost:5055 \
    --notebook-id <id> \
    --action add-url \
    --source "https://pubmed.ncbi.nlm.nih.gov/12345678/"

# Chat with notebook
python3 scripts/chat_interaction.py \
    --url http://localhost:5055 \
    --notebook-id <id> \
    --question "What are the main amyloid beta mechanisms described?"
```

## API Overview

Base URL: `http://localhost:5055/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notebooks` | List all notebooks |
| POST | `/notebooks` | Create notebook |
| GET | `/notebooks/{id}` | Get notebook details |
| PUT | `/notebooks/{id}` | Update notebook |
| DELETE | `/notebooks/{id}` | Delete notebook |
| POST | `/notebooks/{id}/sources` | Add source |
| GET | `/notebooks/{id}/sources` | List sources |
| DELETE | `/notebooks/{id}/sources/{source_id}` | Remove source |
| POST | `/notebooks/{id}/chat` | Chat with notebook |
| POST | `/notebooks/{id}/search` | Search sources |
| POST | `/notebooks/{id}/podcast` | Generate podcast |

## Use Cases for Scientific Research

- **Literature organization**: Ingest papers by topic, chat to synthesize findings
- **Protocol documentation**: Store lab protocols with AI-powered Q&A
- **Grant writing**: Organize references and query for supporting evidence
- **Multi-paper synthesis**: "What do these 50 papers say about mechanism X?"
- **Podcast summaries**: Generate audio summaries of research notebooks
