## Setup

### Dependencies
- Python 3.8+
- pip
- On Debian/Ubuntu: python3-venv (to create virtual environments)
- Google Cloud project with Gmail API enabled
- OAuth 2.0 Client ID (Desktop) JSON
- Gemini API key
- For the web app: FastAPI and Uvicorn (installed via requirements.txt)

Optional (for future React UI):
- Node.js 18+ and npm (or pnpm/yarn)

#### Install system packages (Debian/Ubuntu)
```bash
sudo apt-get update -y
sudo apt-get install -y python3-venv
```

### Steps
1. Create and activate a virtual environment
```bash
python -m venv .venv || python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```
This installs:
- google-generativeai, google-api-python-client, google-auth, google-auth-oauthlib
- python-dotenv, tenacity, typer, rich, dataclasses-json
- fastapi, uvicorn
- pytest and related testing tools

3. Configure environment
```bash
cp .env.example .env
```
Fill in `GEMINI_API_KEY`. Place your OAuth client JSON at the path in `GMAIL_CREDENTIALS_PATH`.

4. First run (CLI, dry run by default; will prompt OAuth consent)
```bash
python -m gmail_cleaner run
```
Follow the browser flow; token is stored at `GMAIL_TOKEN_PATH`.

### Web App (optional)
Start the API server:
```bash
uvicorn gmail_cleaner.webapp:app --reload
```
Open http://127.0.0.1:8000 and click "Continue with Google".

### Troubleshooting
- If pip is blocked (externally managed), create a venv as shown above
- Ensure Gmail API is enabled for your project
- If consent fails, delete `token.json` and retry
- For headless environments, use the local server flow and copy the code

