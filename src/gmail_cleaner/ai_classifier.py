from typing import Dict, Any
import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type


class EmailClassifier:
	"""Gemini-based email classifier with structured JSON output."""

	def __init__(self, api_key: str) -> None:
		genai.configure(api_key=api_key)
		self.model = genai.GenerativeModel("gemini-1.5-flash")

	@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(exp_base=2, max=20), reraise=True)
	def classify_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
		prompt = self._prepare_prompt(email_data)
		response = self.model.generate_content(prompt)
		text = response.text or "{}"
		return self._parse_ai_response(text)

	def _prepare_prompt(self, email_data: Dict[str, Any]) -> str:
		from_address = email_data.get("from", "")
		subject = email_data.get("subject", "")
		snippet = email_data.get("snippet", "")
		instruction = (
			"You are an email triage assistant. Classify a promotional/marketing email into one of: "
			"KEEP, ARCHIVE, DELETE.\n"
			"KEEP: receipts, invoices, order confirmations, shipping notices, account/security alerts, travel bookings, billing statements.\n"
			"ARCHIVE: newsletters, educational content, known brand communications, potentially useful promotions.\n"
			"DELETE: spam, repeated or generic discounts, unknown sender promos, irrelevant blasts.\n"
			"Output STRICT JSON with keys action (KEEP|ARCHIVE|DELETE), confidence (0.0-1.0), reason (short). No extra text."
		)
		payload = {
			"from": from_address,
			"subject": subject,
			"snippet": snippet,
		}
		return f"{instruction}\nEmail JSON:\n{json.dumps(payload)}"

	def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
		# Normalize common LLM response wrappers and extract JSON
		candidates = []
		text = response_text.strip()
		candidates.append(text)
		if text.startswith("```"):
			# strip ```json ... ``` or ``` ... ```
			body = text.strip("`\n")
			if "\n" in body:
				body = body.split("\n", 1)[1]
			candidates.append(body.strip())
		# Try to locate a JSON object substring
		start = text.find("{")
		end = text.rfind("}")
		if start != -1 and end != -1 and end > start:
			candidates.append(text[start:end+1])

		data = {}
		for cand in candidates:
			try:
				data = json.loads(cand)
				break
			except Exception:
				continue

		action = str(data.get("action", "ARCHIVE")).upper()
		if action not in {"KEEP", "ARCHIVE", "DELETE"}:
			action = "ARCHIVE"
		confidence = data.get("confidence", 0.5)
		try:
			confidence = float(confidence)
		except Exception:
			confidence = 0.5
		reason = str(data.get("reason", ""))
		return {"action": action, "confidence": confidence, "reason": reason}

