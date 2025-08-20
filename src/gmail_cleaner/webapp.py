from __future__ import annotations

import os
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from .config import load_config
from .gmail_client import GmailClient, SCOPES
from .ai_classifier import EmailClassifier
from .rate_limiter import RateLimiter
from .email_processor import EmailProcessor


app = FastAPI(title="Gmail AI Cleaner")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
	config = load_config()
	return templates.TemplateResponse("index.html", {"request": request, "dry_run": config.dry_run})


@app.get("/auth")
def auth_start(request: Request):
	config = load_config()
	flow = Flow.from_client_secrets_file(config.gmail_credentials_path, scopes=SCOPES)
	flow.redirect_uri = request.url_for("auth_callback")
	authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
	request.session = {"oauth_state": state}  # simplistic; replace with proper session store
	return RedirectResponse(authorization_url)


@app.get("/auth/callback")
def auth_callback(request: Request):
	config = load_config()
	state = getattr(request, "session", {}).get("oauth_state")
	flow = Flow.from_client_secrets_file(config.gmail_credentials_path, scopes=SCOPES, state=state)
	flow.redirect_uri = request.url_for("auth_callback")
	flow.fetch_token(authorization_response=str(request.url))
	creds = flow.credentials
	request.session = {"token": creds.to_json()}  # store minimally for demo; replace with DB/session
	return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
	session = getattr(request, "session", {})
	if not session or "token" not in session:
		return RedirectResponse("/")
	return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/clean")
def clean(request: Request, max_emails: int = 50, dry_run: bool = True):
	config = load_config()
	session = getattr(request, "session", {})
	if not session or "token" not in session:
		raise HTTPException(status_code=401, detail="Not authenticated")
	creds = Credentials.from_authorized_user_info(eval(session["token"]))
	gmail = GmailClient(config.gmail_credentials_path, config.gmail_token_path, creds_override=creds)
	classifier = EmailClassifier(config.gemini_api_key)
	rate = RateLimiter(max_requests=config.max_requests_per_minute, time_window=60)
	processor = EmailProcessor(gmail, classifier, rate, config)
	ids = gmail.list_promotional_emails(config.gmail_query, max_emails)
	results = processor.process_batch(ids, dry_run=True if dry_run else False)
	if not dry_run:
		apply_summary = processor.apply_actions(results["decisions"], dry_run=False)
		results["applied"] = apply_summary.get("applied", results.get("applied", {}))
	return {"summary": processor.generate_summary(results), "decisions": results["decisions"], "errors": results["errors"]}

