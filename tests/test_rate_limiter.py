import time
from gmail_cleaner.rate_limiter import RateLimiter


def test_rate_limiter_wait_time():
	rl = RateLimiter(max_requests=2, time_window=2)
	rl.add_request()
	rl.add_request()
	wt = rl.get_wait_time()
	assert 0 <= wt <= 2
	# After waiting, should be zero
	time.sleep(2.1)
	assert rl.get_wait_time() == 0

