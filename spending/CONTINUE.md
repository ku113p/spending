# spending — AI Project Index

## Overview
- Telegram bot for automating receipt photo ingestion, processing, and management.
- Extracts and normalizes data via LLM-assisted flows (LangGraph/LangChain).
- Stores in MongoDB, provides review and CSV exports.
- **Tech Stack**: LangGraph/LangChain, python-telegram-bot, Redis (cache/pubsub), MongoDB.

## Setup (Dev Env)
- **Python**: >= 3.13
- **Env Vars** (in .env):
  - `BOT_API_TOKEN`: Telegram Bot API token.
  - `OPENAI_API_KEY`: OpenAI key for LLM.
  - `REDIS_URL`: Redis URL (default: redis://127.0.0.1:6479/0).
  - `MONGO_URI`: MongoDB URI.
  - `MONGO_DB_NAME`: DB name.
  - `MONGO_COLLECTION_NAME`: Collection name.
  - `TO_TEXT_URL`: (Optional) OCR microservice URL.
- **Install**: `make setup`
- **Run Bot**: `make start` (or python main.py)
- **Jupyter**: `make jupyter`

## Top-Level Files
- `main.py`: Entry point, sets logging, runs Telegram bot.
- `config.py`: Config class for env vars and defaults.
- `utils.py`: Utils incl. timing decorator, logger, Langfuse, Redis classes, hash calc.
- `readme.md`: Project desc and setup.
- `Makefile`: Commands for setup, start, jupyter via uv.
- `pyproject.toml`: Metadata, deps, dev tools.

## bot/
- Telegram bot logic for user interactions.
- `bot.py`: Initializes python-telegram-bot with handlers, custom context (RedisCache, graph checkpoint/store). In-memory default. `run_bot()` async polls.
- `handlers.py`: Handlers: /start, /receipts (paginated), /export (daily/monthly). Processes photos/docs, corrections, callbacks. Uses RedisCache (TTL 24h). Functions: start, receipts, etc.
- `context.py`: ChatData (redis_cache, checkpointer, store), CustomContext extends default.

## graphs/pipelines/
- Core pipelines using LangGraph for receipt processing.
- `full_pipeline.py`: Main flow: hash, dup check, OCR/normalize subgraphs, DB save, interrupts (ALREADY_EXISTS, IS_IT_OK), delete. Controller: start, on_exists_answer, on_review.
- `image_to_normailized_receipt.py`: Subgraph chains photo_to_receipt + receipt_normalize.
- `photo_to_receipt/`: Image to receipt subgraphs.
  - `openai_only.py`: GPT-4o Vision extracts from base64 image.
  - `local_ocr.py`: OCR microservice to text, then LLM to receipt.
- `receipt_normalize.py`: products_n_shop_normalizer agent for normalize/categorize.
- `correct_receipt.py`: Fetches from DB, correct_receipt agent updates fields.
- `recategorize.py`: Batch recategorize: fetches, tasks for categories, updates DB.
- `nodes.py`: Reusable: save_to_db (CREATE), redis_publish.
- `utils.py`: one_graph_decorator memoizes compiled LangGraph by process.

## graphs/agents/
- LLM agents and Pydantic schemas for data structur."\e
- `agents.py`: Three agents: receipt_extractor (GPT-4o nano), products_n_shop_normalizer (GPT-4o), correct_receipt (GPT-4o mini).
- `calls.py`: Async ChatModel calls with structured output, metadata logging.
- `schemas.py`: Pydantic: enums (Product/Shop), models (Product, Shop, Receipt, NormalizedReceipt), factories.

## db/
- MongoDB interactions.
- `db.py`: Operation registry (OperationType enum), decorators for handlers, run_operation dispatcher.
- `mongo.py`: Async handlers: INIT, CREATE, LIST, DELETE, GET, UPDATE, COUNT, AGGREGATE.

## exports/
- CSV export generation.
- `exporter.py`: ExportConfig for day/month, uses collect/collect_monthly to write CSV.
- `day.py`: collect aggregates per-item day receipts: match range, unwind, project as DayItemRow.
- `month.py`: collect_monthly per-category totals: match, unwind, group sum, sort desc.

## integrations/
- External services.
- `integrations/to_text.py`: ToTextStrategy.MICROSERVICE: POST image to TO_TEXT_URL via aiohttp, get text from JSON.

## State & Persistence
- **Duplicate Detection**: SHA256 hash (utils.calculate_hash) as file_hash in MongoDB. Triggers ALREADY_EXISTS in full_pipeline.
- **Redis Cache**: Stores per-chat {task_id, image_fp} with TTL 24h (Config.REDIS_CACHE_CONFIG_TTL). Manages sessions.
- **MongoDB**: Receipt as NormalizedReceipt, _id=task_id, file_hash, receipt.
- **LangGraph**: In-memory by default; supports Redis (AsyncRedisSaver/Store) for persistence across restarts.

## Development Shortcuts
- `make setup`: uv sync deps.
- `make start`: Run bot with env.
- `make jupyter`: Launch Jupyter Lab.
- `rg "pattern" -n`: Ripgrep search with line numbers.

## Dependencies
Core:
- langgraph>=0.5.1
- langchain-openai>=0.3.27
- pydantic>=2.11.7
- pymongo>=4.13.2
- redis>=6.2.0
- python-telegram-bot>=22.3
- aiohttp>=3.12.13
- langfuse>=3.1.3
- langchain-community>=0.3.27
- python-dateutil>=2.9.0
- traitlets>=5.14.1

Dev (optional):
- notebook>=7.4.4
- ipykernel>=6.29.5

## Roadmap & TODOs
- [ ] Implement Redis-backed LangGraph checkpointing in bot.run_bot for workflow continuity.
- [ ] Optimize image processing: downscale/compress before vision LLM (photo_to_receipt/openai_only.py).
- [ ] Add recursion/attempt limit to correction loop (full_pipeline.post_correcting_route).
- [ ] Enhance LLM error handling: user-friendly msgs, retries.
- [ ] Stricter validation for user inputs (e.g., /export args).
- [ ] Add MongoDB indexes: unique on file_hash, on receipt.created_at.
- [ ] Unit tests for DB ops and LangGraph nodes.
- [ ] Extended exports: weekly, quarterly.
- [ ] Consider Langsmith for observability.

## Reindexed Files
(excl. __init__.py, *.lock, *.pyc, .venv, venv, __pycache__, .ipynb_checkpoints, .git, .env, *.bak*, *.ipynb)
- main.py, config.py, utils.py, readme.md, Makefile, pyproject.toml
- bot/bot.py, bot/handlers.py, bot/context.py
- graphs/pipelines/full_pipeline.py, image_to_normailized_receipt.py, receipt_normalize.py, correct_receipt.py, recategorize.py, nodes.py, utils.py, photo_to_receipt/openai_only.py, photo_to_receipt/local_ocr.py
- graphs/agents/agents.py, calls.py, schemas.py
- db/db.py, mongo.py
- exports/exporter.py, day.py, month.py
- integrations/to_text.py

Author: ku113p@gmail.com
