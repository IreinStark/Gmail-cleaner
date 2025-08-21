from __future__ import annotations

import json
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from .config import load_config
from .gmail_client import GmailClient, SCOPES
from .ai_classifier import EmailClassifier
from .rate_limiter import RateLimiter
from .email_processor import EmailProcessor


app = FastAPI(title="Gmail AI Cleaner")
config = load_config()
app.add_middleware(
	SessionMiddleware,
	secret_key=config.session_secret,
	https_only=False,
	max_age=60 * 60 * 2,
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=config.allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
	return templates.TemplateResponse("index.html", {"request": request})


@app.get("/auth")
async def auth_start(request: Request):
	flow = Flow.from_client_secrets_file(config.gmail_credentials_path, scopes=SCOPES)
	flow.redirect_uri = request.url_for("auth_callback")
	authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
	request.session["oauth_state"] = state
	return RedirectResponse(authorization_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
	state = request.session.get("oauth_state")
	flow = Flow.from_client_secrets_file(config.gmail_credentials_path, scopes=SCOPES, state=state)
	flow.redirect_uri = request.url_for("auth_callback")
	flow.fetch_token(authorization_response=str(request.url))
	creds = flow.credentials
	request.session["token"] = creds.to_json()
	return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
	if "token" not in request.session:
		return RedirectResponse("/")
	return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/session")
async def api_session(request: Request):
	return {"authenticated": bool(request.session.get("token"))}


@app.post("/api/clean")
async def api_clean(request: Request):
	if "token" not in request.session:
		raise HTTPException(status_code=401, detail="Not authenticated")
	payload = await request.json()
	max_emails = int(payload.get("max_emails", config.max_emails_per_session))
	dry_run = bool(payload.get("dry_run", True))
	confidence_threshold = float(payload.get("confidence_threshold", config.confidence_threshold))
	safe_archive = bool(payload.get("safe_archive", config.safe_archive_mode))

	creds = Credentials.from_authorized_user_info(json.loads(request.session["token"]))
	local_config = load_config()
	local_config.confidence_threshold = confidence_threshold
	local_config.safe_archive_mode = safe_archive

	gmail = GmailClient(local_config.gmail_credentials_path, local_config.gmail_token_path, creds_override=creds)
	classifier = EmailClassifier(local_config.gemini_api_key)
	rate = RateLimiter(max_requests=local_config.max_requests_per_minute, time_window=60)
	processor = EmailProcessor(gmail, classifier, rate, local_config)
	ids = gmail.list_promotional_emails(local_config.gmail_query, max_emails)
	results = processor.process_batch(ids, dry_run=True if dry_run else False)
	if not dry_run:
		apply_summary = processor.apply_actions(results["decisions"], dry_run=False)
		results["applied"] = apply_summary.get("applied", results.get("applied", {}))
	return {"summary": processor.generate_summary(results), "decisions": results["decisions"], "errors": results["errors"]}

