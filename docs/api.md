## API Documentation

### `gmail_cleaner.config`
- `AppConfig`: Loads env and CLI options
- `load_config() -> AppConfig`

### `gmail_cleaner.gmail_client`
- `GmailClient.authenticate() -> bool`
- `GmailClient.list_promotional_emails(query: str, max_results: int) -> List[str]`
- `GmailClient.get_email_metadata(msg_id: str) -> Dict`
- `GmailClient.apply_label(msg_id: str, label_id: str) -> bool`
- `GmailClient.archive_email(msg_id: str) -> bool`
- `GmailClient.delete_email(msg_id: str) -> bool`
- `GmailClient.create_label(label_name: str) -> str`

### `gmail_cleaner.ai_classifier`
- `EmailClassifier.classify_email(email_data: Dict) -> Dict`

### `gmail_cleaner.rate_limiter`
- `RateLimiter.wait_if_needed()`
- `RateLimiter.add_request()`
- `RateLimiter.get_wait_time() -> float`

### `gmail_cleaner.email_processor`
- `EmailProcessor.process_batch(email_ids: List[str], dry_run: bool = True) -> Dict`
- `EmailProcessor.apply_actions(decisions: List[Dict], dry_run: bool = True) -> Dict`
- `EmailProcessor.generate_summary(results: Dict) -> str`

