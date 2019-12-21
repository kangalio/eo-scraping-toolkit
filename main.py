import os
from requests.exceptions import HTTPError
import eo_scraping, xml_generation, util

"""
TODO:
- Download replays, at the least to have MaxCombo
"""

END_USER_MODE = True

DISCLAIMER = """
Note: EtternaOnline discards any non-Personal Best scores. Therefore you
will see at most one score per rate for each song, but blame that issue
on EO please.
""".strip()

print(DISCLAIMER)
print()

userid = None
while userid is None:
	username = input("Enter username: ")
	try:
		userid = eo_scraping.get_userid(username)
	except HTTPError:
		print("That user doesn't exist!")

print(f"Found user {username} with userid {userid}")
print()

xml_generation.verbose = True
xml_root = xml_generation.gen_xml(username, userid, score_limit=None)
xml_string = util.xml_format(xml_root)

print()
output_path = "Etterna.xml"
if os.path.exists(output_path):
	output_path = input("Etterna.xml already exists. Enter a new filename: ")
with open(output_path, "w") as f:
	f.write(xml_string)

input(f"Successfully saved {output_path}. Press enter to quit")
