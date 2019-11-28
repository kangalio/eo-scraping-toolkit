import requests, time
from joblib import Memory
from datetime import datetime, timedelta

REQUEST_WAIT_TIME = timedelta(seconds=10)

memory = Memory("requests_cache", verbose=0)

last_request_time = datetime.fromisoformat("1970-01-01")
def rate_limit():
	global last_request_time
	
	delta = datetime.now() - last_request_time
	if delta < REQUEST_WAIT_TIME:
		wait_seconds = (REQUEST_WAIT_TIME - delta).total_seconds()
		# ~ print(f"rate limiting :) gonna wait {wait_seconds:.2f}s...")
		time.sleep(wait_seconds)
	last_request_time = datetime.now()

# Extracts a substring based on prefix and postfix
def extract_str(string, before, after=None):
	start = 0 if before is None else string.find(before) + len(before)
	end = None if after is None else string.find(after, start)
	return string[start:end]

# Convert a filesize string like "566 B" or "2.5 GB" into a MBs float
MULTIPLIERS = [" b", "kb", "mb", "gb", "tb", "pb"]
def parse_filesize(string):
	if string == "0 B": return 0
	multiplier = 1000 ** (MULTIPLIERS.index(string[-2:].lower()) - 2)
	return float(string[:-2]) * multiplier

def format_datetime(date):
	return datetime.strftime(date, "%Y-%m-%d %H:%M:%S")

def parse_datetime(date_str):
	return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

@memory.cache
def post(url, *args, **kw_args):
	rate_limit()
	url = "https://etternaonline.com/" + url
	return requests.post(url, *args, **kw_args)

@memory.cache
def get(url, *args, **kw_args):
	rate_limit()
	url = "https://etternaonline.com/" + url
	return requests.get(url, *args, **kw_args)
