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
from .demo import DemoGmailClient, DemoClassifier, DemoRateLimiter


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
	demo: bool = typer.Option(False, help="Run a simulated demo without real APIs"),
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

	if demo:
		print("[yellow]Demo mode: using simulated Gmail and classifier[/yellow]")
		gmail = DemoGmailClient()
		classifier = DemoClassifier()
		rate = DemoRateLimiter()
		ids = gmail.list_promotional_emails(config.gmail_query, config.max_emails_per_session)
	else:
		if not config.gemini_api_key:
			print("[red]GEMINI_API_KEY is not set. Please set it in .env[/red]")
			raise typer.Exit(code=1)
		gmail = GmailClient(config.gmail_credentials_path, config.gmail_token_path)
		print("Authenticating with Gmail...")
		gmail.authenticate()
		classifier = EmailClassifier(config.gemini_api_key)
		rate = RateLimiter(max_requests=config.max_requests_per_minute, time_window=60)
		print(f"Querying emails with: [cyan]{config.gmail_query}[/cyan]")
		ids = gmail.list_promotional_emails(config.gmail_query, config.max_emails_per_session)

	processor = EmailProcessor(gmail, classifier, rate, config)
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


@app.command()
def purge(
	max_emails: Optional[int] = typer.Option(None, help="Max emails to purge in this session"),
	batch_size: Optional[int] = typer.Option(None, help="Batch size"),
	query: Optional[str] = typer.Option("category:promotions", help="Gmail search query to select emails to purge"),
	dry_run: bool = typer.Option(True, help="Dry run mode (no changes)"),
	hard_delete: bool = typer.Option(False, help="Permanently delete instead of moving to Trash"),
):
	"""Delete all promotional emails matching the query (bypasses AI)."""
	config: AppConfig = load_config()
	if max_emails is not None:
		config.max_emails_per_session = max_emails
	if batch_size is not None:
		config.batch_size = batch_size
	if query is not None:
		config.gmail_query = query
	config.dry_run = dry_run

	gmail = GmailClient(config.gmail_credentials_path, config.gmail_token_path)
	print("Authenticating with Gmail...")
	gmail.authenticate()
	print(f"Querying emails with: [cyan]{config.gmail_query}[/cyan]")
	ids = gmail.list_promotional_emails(config.gmail_query, config.max_emails_per_session)
	print(f"Found {len(ids)} emails to purge")

	rate = RateLimiter(max_requests=config.max_requests_per_minute, time_window=60)

	batches = [ids[i : i + config.batch_size] for i in range(0, len(ids), config.batch_size)]
	deleted = 0
	errors = 0
	for batch_index, batch in enumerate(batches, start=1):
		print(f"\n[bold]Batch {batch_index}/{len(batches)}[/bold] (size {len(batch)})")
		for msg_id in batch:
			try:
				if not dry_run:
					rate.wait_if_needed()
					if hard_delete:
						gmail.hard_delete_email(msg_id)
					else:
						gmail.delete_email(msg_id)
					rate.add_request()
				deleted += 1
			except Exception as e:
				errors += 1
				print(f"[red]Error purging {msg_id}: {e}[/red]")
		print(f"Batch summary: deleted={deleted} errors={errors} (cumulative)")
		if batch_index < len(batches):
			print(f"Waiting {config.batch_delay_seconds}s before next batch (rate limiting)...")
			time.sleep(config.batch_delay_seconds)

	action = "would delete" if dry_run else ("hard-deleted" if hard_delete else "moved to Trash")
	print(f"\n[green]Done.[/green] {deleted} emails {action}. Errors: {errors}")


if __name__ == "__main__":
	app()