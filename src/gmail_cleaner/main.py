from __future__ import annotations

import time
from typing import Optional
import typer
from rich import print
from rich.progress import track

from .config import load_config, AppConfig
from .gmail_client import GmailClient
from .ai_classifier import EmailClassifier
from .rate_limiter import RateLimiter
from .email_processor import EmailProcessor


app = typer.Typer(add_completion=False)


@app.callback()
def _callback() -> None:
	"""Gmail AI Cleaner CLI."""


@app.command()
def run(
	max_emails: Optional[int] = typer.Option(None, help="Max emails per session"),
	batch_size: Optional[int] = typer.Option(None, help="Batch size"),
	query: Optional[str] = typer.Option(None, help="Gmail search query"),
	dry_run: Optional[bool] = typer.Option(None, help="Dry run mode"),
):
	config: AppConfig = load_config()
	if max_emails is not None:
		config.max_emails_per_session = max_emails
	if batch_size is not None:
		config.batch_size = batch_size
	if query is not None:
		config.gmail_query = query
	if dry_run is not None:
		config.dry_run = dry_run

	if not config.gemini_api_key:
		print("[red]GEMINI_API_KEY is not set. Please set it in .env[/red]")
		raise typer.Exit(code=1)

	gmail = GmailClient(config.gmail_credentials_path, config.gmail_token_path)
	print("Authenticating with Gmail...")
	gmail.authenticate()

	classifier = EmailClassifier(config.gemini_api_key)
	rate = RateLimiter(max_requests=config.max_requests_per_minute, time_window=60)
	processor = EmailProcessor(gmail, classifier, rate, config)

	print(f"Querying emails with: [cyan]{config.gmail_query}[/cyan]")
	ids = gmail.list_promotional_emails(config.gmail_query, config.max_emails_per_session)
	print(f"Found {len(ids)} emails to process")

	batches = [ids[i : i + config.batch_size] for i in range(0, len(ids), config.batch_size)]
	for batch_index, batch in enumerate(batches, start=1):
		print(f"\n[bold]Batch {batch_index}/{len(batches)}[/bold] (size {len(batch)})")
		results = processor.process_batch(batch, dry_run=config.dry_run)
		if not config.dry_run:
			apply_summary = processor.apply_actions(results["decisions"], dry_run=False)
			results["applied"] = apply_summary.get("applied", results.get("applied", {}))
		print(processor.generate_summary(results))
		if batch_index < len(batches):
			print(f"Waiting {config.batch_delay_seconds}s before next batch (rate limiting)...")
			time.sleep(config.batch_delay_seconds)

	print("\n[green]Done.[/green]")


if __name__ == "__main__":
	app()

