from __future__ import annotations

from typing import Dict, List


SAMPLE_EMAILS: List[Dict] = [
	{"id": "e1", "from": "Amazon <orders@amazon.com>", "subject": "Your order has shipped", "snippet": "Your order #123-456 has been shipped..."},
	{"id": "e2", "from": "Sale Alerts <promo@randomstore.com>", "subject": "50% OFF EVERYTHING - LIMITED TIME", "snippet": "Don't miss this amazing sale..."},
	{"id": "e3", "from": "GitHub <noreply@github.com>", "subject": "Monthly newsletter", "snippet": "Latest developer news..."},
	{"id": "e4", "from": "Delta <notify@delta.com>", "subject": "Your flight is confirmed", "snippet": "Booking ABC123..."},
	{"id": "e5", "from": "Apple <no-reply@apple.com>", "subject": "Your receipt from Apple", "snippet": "Receipt for purchase..."},
]


class DemoGmailClient:
	def __init__(self) -> None:
		self._labels: Dict[str, str] = {}
		self._applied: List[Dict] = []

	def authenticate(self) -> bool:
		return True

	def list_promotional_emails(self, query: str, max_results: int) -> List[str]:
		return [e["id"] for e in SAMPLE_EMAILS][:max_results]

	def get_email_metadata(self, msg_id: str) -> Dict:
		for e in SAMPLE_EMAILS:
			if e["id"] == msg_id:
				return e
		return {"id": msg_id, "from": "", "subject": "", "snippet": ""}

	def apply_label(self, msg_id: str, label_id: str) -> bool:
		self._applied.append({"id": msg_id, "label": label_id})
		return True

	def archive_email(self, msg_id: str) -> bool:
		self._applied.append({"id": msg_id, "action": "ARCHIVE"})
		return True

	def delete_email(self, msg_id: str) -> bool:
		self._applied.append({"id": msg_id, "action": "DELETE"})
		return True

	def create_label(self, label_name: str) -> str:
		if label_name not in self._labels:
			self._labels[label_name] = f"demo_{label_name}"
		return self._labels[label_name]


class DemoClassifier:
	def classify_email(self, email_data: Dict) -> Dict:
		subject = (email_data.get("subject") or "").lower()
		if any(k in subject for k in ["receipt", "order", "shipped", "invoice", "confirmed", "flight"]):
			return {"action": "KEEP", "confidence": 0.95, "reason": "transactional"}
		if any(k in subject for k in ["% off", "sale", "discount", "limited time", "deal"]):
			return {"action": "DELETE", "confidence": 0.9, "reason": "promotion"}
		return {"action": "ARCHIVE", "confidence": 0.75, "reason": "newsletter/brand"}


class DemoRateLimiter:
	def add_request(self) -> None:
		return None
	def get_wait_time(self) -> float:
		return 0.0
	def wait_if_needed(self) -> None:
		return None

