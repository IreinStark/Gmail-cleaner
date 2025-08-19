from gmail_cleaner.ai_classifier import EmailClassifier


class DummyModel:
	def __init__(self, text):
		self._text = text
	def generate_content(self, prompt):
		class R:
			def __init__(self, t):
				self.text = t
		return R(self._text)


def test_parse_ai_response_delete_low_confidence(monkeypatch):
	clf = EmailClassifier(api_key="dummy")
	# monkeypatch the model
	clf.model = DummyModel('{"action":"DELETE","confidence":0.4,"reason":"generic promo"}')
	res = clf.classify_email({"from": "a", "subject": "b", "snippet": "c"})
	assert res["action"] == "DELETE"
	assert 0.0 <= res["confidence"] <= 1.0

