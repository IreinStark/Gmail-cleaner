## Usage

### Basic
```bash
python -m gmail_cleaner
```

### Common Options
```bash
python -m gmail_cleaner --max-emails 100 --batch-size 15 --dry-run false
python -m gmail_cleaner --query "category:promotions older_than:7d"
python -m gmail_cleaner --demo true  # Simulated run without Gmail/Gemini
python -m gmail_cleaner --confidence-threshold 0.6 --safe-archive false  # AI DELETE moves to Trash when confidence>=0.6
```

### Purge all promotions (no AI)
```bash
# Dry run (default): show how many would be deleted
python -m gmail_cleaner purge --query "category:promotions older_than:7d"

# Move to Trash (apply changes)
python -m gmail_cleaner purge --dry-run false --max-emails 200

# Permanently delete (irreversible)
python -m gmail_cleaner purge --dry-run false --hard-delete true
```

### Dry Run
Enabled by default; prints intended actions and labels without modifying emails.

### Labels
- KEEP -> `AI_KEEP`
- ARCHIVE -> `AI_ARCHIVED`
- Low-confidence -> `AI_REVIEW`

### Undo
Use Gmail to filter by labels and revert actions (move from Trash or All Mail back to Inbox).

