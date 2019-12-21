import requests, time, sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from datetime import datetime, timedelta
from enum import Enum
from bs4 import BeautifulSoup
from joblib import Memory

SKILLSETS = ["Stream", "Jumpstream", "Handstream", "Stamina", "JackSpeed", "Chordjack", "Technical"]
JUDGEMENTS = ["Marvelous", "Perfect", "Great", "Good", "Bad", "Miss"]

REQUEST_WAIT_TIME = timedelta(seconds=1)

memory = Memory("requests_cache", verbose=0)

grade_names = ['Failed', 'Tier07', 'Tier06', 'Tier05', 'Tier04', 'Tier03', 'Tier02', 'Tier01']
class Grade(Enum):
	F = 0
	D = 1
	C = 2
	B = 3
	A = 4
	AA = 5
	AAA = 6
	AAAA = 7
	
	def from_wifescore(percent):
		if percent > 0.9997: return Grade.AAAA
		elif percent > 0.9975: return Grade.AAA
		elif percent > 0.93: return Grade.AA
		elif percent > 0.80: return Grade.A
		elif percent > 0.70: return Grade.B
		elif percent > 0.60: return Grade.C
		else: return Grade.D
	
	def as_xml_name(self):
		return grade_names[self.value]
	
	def from_xml_name(name):
		grade_number = grade_names.index(name)
		if grade_number == -1:
			return None
		else:
			return Grade(grade_number)

def parse_html(code):
	return BeautifulSoup(code, features="html5lib")

def add_xml_text_elements(parent, subelements):
	for tag, content in subelements.items():
		if content is None:
			continue
		elif isinstance(content, float):
			# Round to hide floating point errors
			text = f"{content:.8g}"
		else:
			text = str(content)
		SubElement(parent, tag).text = text

# Source: http://effbot.org/zone/element-lib.htm#prettyprint
def indent(elem, level=0):
    i = "\n" + level*" "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def xml_format(element):
	indent(element)
	return ElementTree.tostring(element).decode("UTF-8")

last_request_time = datetime.fromisoformat("1970-01-01")
def rate_limit():
	global last_request_time
	
	delta = datetime.now() - last_request_time
	if delta < REQUEST_WAIT_TIME:
		wait_seconds = (REQUEST_WAIT_TIME - delta).total_seconds()
		# ~ info_text = f"[rate limiting :) please wait {wait_seconds:.2f}s]"
		# ~ sys.stdout.write(info_text)
		# ~ sys.stdout.flush()
		time.sleep(wait_seconds)
		# ~ sys.stdout.write("\b" * len(info_text))
		# ~ sys.stdout.write(" " * len(info_text))
		# ~ sys.stdout.write("\b" * len(info_text))
		# ~ sys.stdout.flush()
	last_request_time = datetime.now()

# Extracts a substring based on prefix and postfix. Both `before` and
# `after` can be None
def extract_str(string, before, after=None):
	if before is None:
		start = 0
	else:
		before_index = string.find(before)
		if before_index == -1: return None
		start = before_index + len(before)
	
	if after is None:
		end = None
	else:
		end = string.find(after, start)
		if end == -1: end = None # Right behavior?
	
	return string[start:end]

# Like extract_str, but it can find multiple. Returns a list
def extract_strs(string, before, after):
	matches = []
	
	search_start = 0
	while True:
		index = string.find(before, search_start)
		if index == -1: return matches
		start = index + len(before)
		end = string.find(after, start)
		if end == -1: return matches
		
		matches.append(string[start:end])
		search_start = end
		

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
def post_inner(url, data):
	rate_limit()
	url = "https://etternaonline.com/" + url
	response = requests.post(url, data=data)
	response.raise_for_status()
	return response

@memory.cache
def get_inner(url):
	rate_limit()
	url = "https://etternaonline.com/" + url
	response = requests.get(url)
	response.raise_for_status()
	return response

def get(url): return get_inner(url)
def post(url, data): return post_inner(url, data)
