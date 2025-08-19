from __future__ import annotations

import time
from typing import Dict, List, Any


class EmailProcessor:
	"""Coordinates fetching metadata, classification, and applying actions."""

	def __init__(self, gmail_client, classifier, rate_limiter, config) -> None:
		self.gmail = gmail_client
		self.classifier = classifier
		self.rate = rate_limiter
		self.config = config
		self._label_ids: Dict[str, str] = {}

	def _ensure_labels(self) -> None:
		for label_name in [self.config.keep_label, self.config.archive_label, self.config.review_label]:
			if label_name not in self._label_ids:
				self._label_ids[label_name] = self.gmail.create_label(label_name)

	def process_batch(self, email_ids: List[str], dry_run: bool = True) -> Dict[str, Any]:
		results = {
			"decisions": [],
			"applied": {"KEEP": 0, "ARCHIVE": 0, "DELETE": 0},
			"errors": [],
		}
		self._ensure_labels()
		for msg_id in email_ids:
			self.rate.wait_if_needed()
			try:
				meta = self.gmail.get_email_metadata(msg_id)
				self.rate.add_request()
			except Exception as e:
				results["errors"].append({"id": msg_id, "step": "metadata", "error": str(e)})
				continue

			try:
				decision = self.classifier.classify_email({
					"from": meta.get("from", ""),
					"subject": meta.get("subject", ""),
					"snippet": meta.get("snippet", ""),
				})
				# Safety rule: downgrade low-confidence DELETE to ARCHIVE
				if decision.get("action") == "DELETE" and decision.get("confidence", 0.0) < self.config.confidence_threshold:
					decision["action"] = "ARCHIVE"
				d = {"id": msg_id, **decision}
				results["decisions"].append(d)
			except Exception as e:
				results["errors"].append({"id": msg_id, "step": "classify", "error": str(e)})
				continue

		if not dry_run:
			apply_summary = self.apply_actions(results["decisions"], dry_run=False)
			results["applied"] = apply_summary.get("applied", results["applied"])
		return results

	def apply_actions(self, decisions: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, Any]:
		applied = {"KEEP": 0, "ARCHIVE": 0, "DELETE": 0}
		errors: List[Dict[str, Any]] = []
		for d in decisions:
			action = d.get("action", "ARCHIVE")
			msg_id = d.get("id")
			label_to_apply = self.config.review_label if action == "ARCHIVE" and d.get("confidence", 1.0) < self.config.confidence_threshold else (
				self.config.keep_label if action == "KEEP" else self.config.archive_label if action == "ARCHIVE" else self.config.archive_label
			)
			try:
				if not dry_run:
					self.rate.wait_if_needed()
					self.gmail.apply_label(msg_id, self._label_ids[label_to_apply])
					self.rate.add_request()
					if action == "ARCHIVE":
						self.rate.wait_if_needed()
						self.gmail.archive_email(msg_id)
						self.rate.add_request()
					elif action == "DELETE":
						if self.config.safe_archive_mode:
							self.rate.wait_if_needed()
							self.gmail.archive_email(msg_id)
							self.rate.add_request()
						else:
							self.rate.wait_if_needed()
							self.gmail.delete_email(msg_id)
							self.rate.add_request()
				applied[action] = applied.get(action, 0) + 1
			except Exception as e:
				errors.append({"id": msg_id, "step": "apply", "error": str(e)})
		return {"applied": applied, "errors": errors}

	def generate_summary(self, results: Dict[str, Any]) -> str:
		num = len(results.get("decisions", []))
		app = results.get("applied", {"KEEP": 0, "ARCHIVE": 0, "DELETE": 0})
		errs = len(results.get("errors", []))
		return (
			f"Decisions: {num} | Applied KEEP={app.get('KEEP',0)} ARCHIVE={app.get('ARCHIVE',0)} DELETE={app.get('DELETE',0)} | Errors: {errs}"
		)

