## Gmail AI Cleaner

An intelligent Python application that uses AI to classify, organize, and clean promotional emails in Gmail, with safety-first features, rate limiting, and clear reporting.

### Features (MVP)
- AI email classification via Gemini (`KEEP`/`ARCHIVE`/`DELETE`) with confidence scores
- Gmail API integration with OAuth 2.0
- Batch processing with configurable rate limiting and backoff
- Dry run mode and safety thresholds (auto-archive low-confidence deletes)
- Smart labeling (`AI_KEEP`, `AI_ARCHIVED`, `AI_REVIEW`) and easy undo

### Quick Start
1. Install Python 3.8+
2. Clone repo and install deps:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
3. Copy `.env.example` to `.env` and fill values
4. Place your Google OAuth client file at path set by `GMAIL_CREDENTIALS_PATH` (e.g., `credentials.json`)
5. Run dry run:
```bash
python -m gmail_cleaner --dry-run true
```

### Web App (experimental)
- Start server
```bash
uvicorn gmail_cleaner.webapp:app --reload
```
- Navigate to http://127.0.0.1:8000/ and click "Continue with Google"
- Run a dry run on the dashboard, review decisions, then apply

See `docs/setup.md` and `docs/usage.md` for full details.

### Repository Layout
```
gmail-ai-cleaner/
├── src/
│   └── gmail_cleaner/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py
│       ├── gmail_client.py
│       ├── ai_classifier.py
│       ├── rate_limiter.py
│       ├── email_processor.py
│       └── config.py
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_gmail_client.py
│   ├── test_rate_limiter.py
│   └── test_email_processor.py
├── docs/
│   ├── setup.md
│   ├── usage.md
│   └── api.md
├── .env.example
├── requirements.txt
├── setup.py
└── README.md
```

### Safety Notes
- Never logs email content; only anonymized IDs and counts
- Dry run by default; use `--dry-run false` to apply changes
- Low-confidence deletes are auto-archived unless explicitly disabled

### License
MIT

