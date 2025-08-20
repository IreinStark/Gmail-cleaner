from __future__ import annotations

from typing import Dict, List, Optional
from dataclasses import dataclass
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


@dataclass
class GmailLabel:
	id: str
	name: str


class GmailClient:
	"""Wrapper for Gmail API operations with OAuth handling."""

	def __init__(self, credentials_path: str, token_path: str, creds_override: Optional[Credentials] = None) -> None:
		self.credentials_path = credentials_path
		self.token_path = token_path
		self.creds: Optional[Credentials] = creds_override
		self.service = None
		self._label_cache_by_name: Dict[str, GmailLabel] = {}

	def authenticate(self) -> bool:
		"""Authenticate with OAuth 2.0 and build the Gmail service client."""
		creds = self.creds
		try:
			if creds is None:
				creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
		except Exception:
			creds = None

		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
				creds = flow.run_local_server(port=0)
			with open(self.token_path, "w") as token:
				token.write(creds.to_json())

		self.creds = creds
		self.service = build("gmail", "v1", credentials=self.creds)
		self._warm_label_cache()
		return True

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def list_promotional_emails(self, query: str, max_results: int) -> List[str]:
		"""Fetch promotional email IDs using a Gmail search query."""
		ids: List[str] = []
		page_token: Optional[str] = None
		while True:
			resp = self.service.users().messages().list(
				userId="me",
				q=query,
				pageToken=page_token,
				maxResults=min(100, max_results - len(ids)),
			).execute()
			for item in resp.get("messages", []) or []:
				ids.append(item["id"])  # type: ignore[index]
				if len(ids) >= max_results:
					return ids
			page_token = resp.get("nextPageToken")
			if not page_token:
				break
		return ids

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def get_email_metadata(self, msg_id: str) -> Dict:
		"""Fetch email headers (From, Subject) and snippet."""
		resp = self.service.users().messages().get(
			userId="me",
			id=msg_id,
			format="metadata",
			metadataHeaders=["From", "Subject"],
		).execute()
		headers = {h["name"].lower(): h["value"] for h in resp.get("payload", {}).get("headers", [])}
		return {
			"id": msg_id,
			"from": headers.get("from", ""),
			"subject": headers.get("subject", ""),
			"snippet": resp.get("snippet", ""),
		}

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def apply_label(self, msg_id: str, label_id: str) -> bool:
		body = {"addLabelIds": [label_id]}
		self.service.users().messages().modify(userId="me", id=msg_id, body=body).execute()
		return True

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def archive_email(self, msg_id: str) -> bool:
		body = {"removeLabelIds": ["INBOX"]}
		self.service.users().messages().modify(userId="me", id=msg_id, body=body).execute()
		return True

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def delete_email(self, msg_id: str) -> bool:
		# Move to Trash (not permanent delete)
		self.service.users().messages().trash(userId="me", id=msg_id).execute()
		return True

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def hard_delete_email(self, msg_id: str) -> bool:
		"""Permanently delete a message (cannot be undone)."""
		self.service.users().messages().delete(userId="me", id=msg_id).execute()
		return True

	@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True,
	       retry=retry_if_exception_type(HttpError))
	def create_label(self, label_name: str) -> str:
		"""Create a Gmail label and return its ID (or existing one)."""
		# Return cached id if available
		if label_name in self._label_cache_by_name:
			return self._label_cache_by_name[label_name].id
		# Attempt to find existing
		labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
		for lab in labels:
			if lab.get("name") == label_name:
				label = GmailLabel(id=lab["id"], name=lab["name"])  # type: ignore[index]
				self._label_cache_by_name[label_name] = label
				return label.id
		# Create new
		created = self.service.users().labels().create(
			userId="me",
			body={
				"name": label_name,
				"labelListVisibility": "labelShow",
				"messageListVisibility": "show",
			},
		).execute()
		label = GmailLabel(id=created["id"], name=created["name"])  # type: ignore[index]
		self._label_cache_by_name[label_name] = label
		return label.id

	def _warm_label_cache(self) -> None:
		try:
			labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
			for lab in labels:
				self._label_cache_by_name[lab.get("name")] = GmailLabel(id=lab.get("id"), name=lab.get("name"))
		except Exception:
			# Cache warming is best-effort
			self._label_cache_by_name = {}

