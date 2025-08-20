import time
from collections import deque
from typing import Deque


class RateLimiter:
	"""Simple sliding-window rate limiter."""

	def __init__(self, max_requests: int = 14, time_window: int = 60) -> None:
		self.max_requests = max_requests
		self.time_window = time_window
		self._timestamps: Deque[float] = deque()

	def add_request(self) -> None:
		self._prune()
		self._timestamps.append(time.time())

	def get_wait_time(self) -> float:
		self._prune()
		if len(self._timestamps) < self.max_requests:
			return 0.0
		oldest = self._timestamps[0]
		elapsed = time.time() - oldest
		return max(0.0, self.time_window - elapsed)

	def wait_if_needed(self, min_delay: float = 0.0) -> None:
		"""Wait long enough to respect the window and ensure a minimum spacing."""
		wait_seconds = max(self.get_wait_time(), min_delay)
		if wait_seconds > 0:
			time.sleep(wait_seconds)

	def _prune(self) -> None:
		cutoff = time.time() - self.time_window
		while self._timestamps and self._timestamps[0] < cutoff:
			self._timestamps.popleft()

