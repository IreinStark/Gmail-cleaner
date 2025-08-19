## Setup

### Prerequisites
- Python 3.8+
- Google Cloud project with Gmail API enabled
- OAuth 2.0 Client ID (Desktop) JSON downloaded
- Gemini API key

### Steps
1. Create and activate a virtual environment
```bash
python -m venv .venv && source .venv/bin/activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Configure environment
```bash
cp .env.example .env
```
Fill in `GEMINI_API_KEY`. Place your OAuth client JSON at the path in `GMAIL_CREDENTIALS_PATH`.

4. First run (will prompt OAuth consent)
```bash
python -m gmail_cleaner --dry-run true
```
Follow the browser flow; token is stored at `GMAIL_TOKEN_PATH`.

### Troubleshooting
- Ensure Gmail API is enabled for your project
- If consent fails, delete `token.json` and retry
- For headless environments, use the local server flow and copy the code

