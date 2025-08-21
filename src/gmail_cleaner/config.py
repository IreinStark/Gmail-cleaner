import os
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv


@dataclass
class AppConfig:
	gmail_credentials_path: str
	gmail_token_path: str
	gemini_api_key: str
	max_emails_per_session: int = 50
	batch_size: int = 10
	batch_delay_seconds: int = 65
	max_requests_per_minute: int = 14
	dry_run: bool = True
	safe_archive_mode: bool = True
	confidence_threshold: float = 0.6
	gmail_query: str = "category:promotions newer_than:30d"
	keep_label: str = "AI_KEEP"
	archive_label: str = "AI_ARCHIVED"
	review_label: str = "AI_REVIEW"
	verbose: bool = False
	cache_path: str = ".gmail_cleaner_cache.json"
	enable_cache: bool = True
	session_secret: str = "change-me"
	allowed_origins: List[str] = None  # type: ignore[assignment]


def _env_bool(value: Optional[str], default: bool) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "y"}


def load_config() -> AppConfig:
	load_dotenv()
	origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
	return AppConfig(
		gmail_credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"),
		gmail_token_path=os.getenv("GMAIL_TOKEN_PATH", "token.json"),
		gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
		max_emails_per_session=int(os.getenv("MAX_EMAILS_PER_SESSION", "50")),
		batch_size=int(os.getenv("BATCH_SIZE", "10")),
		batch_delay_seconds=int(os.getenv("BATCH_DELAY_SECONDS", "65")),
		max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "14")),
		dry_run=_env_bool(os.getenv("DRY_RUN"), True),
		safe_archive_mode=_env_bool(os.getenv("SAFE_ARCHIVE_MODE"), True),
		confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.6")),
		gmail_query=os.getenv("GMAIL_QUERY", "category:promotions newer_than:30d"),
		keep_label=os.getenv("KEEP_LABEL", "AI_KEEP"),
		archive_label=os.getenv("ARCHIVE_LABEL", "AI_ARCHIVED"),
		review_label=os.getenv("REVIEW_LABEL", "AI_REVIEW"),
		verbose=_env_bool(os.getenv("VERBOSE"), False),
		cache_path=os.getenv("CACHE_PATH", ".gmail_cleaner_cache.json"),
		enable_cache=_env_bool(os.getenv("ENABLE_CACHE"), True),
		session_secret=os.getenv("SESSION_SECRET", "change-me"),
		allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
	)

