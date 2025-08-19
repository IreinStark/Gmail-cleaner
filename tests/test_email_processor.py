from types import SimpleNamespace
from gmail_cleaner.email_processor import EmailProcessor
from gmail_cleaner.config import AppConfig


class FakeGmail:
	def __init__(self):
		self.applied = []
	def create_label(self, name):
		return f"lab_{name}"
	def get_email_metadata(self, msg_id):
		return {"id": msg_id, "from": "Sale <promo@x.com>", "subject": "50% OFF", "snippet": "..."}
	def apply_label(self, msg_id, label_id):
		self.applied.append((msg_id, label_id))
		return True
	def archive_email(self, msg_id):
		return True
	def delete_email(self, msg_id):
		return True


class FakeClassifier:
	def classify_email(self, email_data):
		if "OFF" in email_data.get("subject", ""):
			return {"action": "DELETE", "confidence": 0.4, "reason": "promo"}
		return {"action": "KEEP", "confidence": 0.9, "reason": "receipt"}


class FakeRate:
	def wait_if_needed(self):
		return None
	def add_request(self):
		return None


def test_processor_safety_threshold_archives_delete():
	cfg = AppConfig(
		gmail_credentials_path="c.json",
		gmail_token_path="t.json",
		gemini_api_key="k",
		confidence_threshold=0.6,
	)
	gmail = FakeGmail()
	clf = FakeClassifier()
	rate = FakeRate()
	proc = EmailProcessor(gmail, clf, rate, cfg)
	res = proc.process_batch(["1"], dry_run=True)
	assert res["decisions"][0]["action"] == "ARCHIVE"

