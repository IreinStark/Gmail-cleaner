## Usage

### Basic
```bash
python -m gmail_cleaner
```

### Common Options
```bash
python -m gmail_cleaner --max-emails 100 --batch-size 15 --dry-run false
python -m gmail_cleaner --query "category:promotions older_than:7d"
```

### Dry Run
Enabled by default; prints intended actions and labels without modifying emails.

### Labels
- KEEP -> `AI_KEEP`
- ARCHIVE -> `AI_ARCHIVED`
- Low-confidence -> `AI_REVIEW`

### Undo
Use Gmail to filter by labels and revert actions (move from Trash or All Mail back to Inbox).

