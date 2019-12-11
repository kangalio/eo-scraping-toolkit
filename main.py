import os
from requests.exceptions import HTTPError
import eo_scraping, xml_generation, util

"""
TODO:
- Download replays, at the least to have MaxCombo
- Set default modifiers to last used modifiers
"""

END_USER_MODE = True

DISCLAIMER = """
Note: EtternaOnline provides no way to determine which diff of some song
was played. This program assumes the first diff of any given song for
that very reason.
In practice this means that when you play all diffs of a song, after
this conversion all those scores will be displayed in Etterna as if you
made them on just the first diff.
Also, EtternaOnline discards any non-Personal Best scores. Therefore you
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

print(f"Found user {username}")

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
