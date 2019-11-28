import json
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement
from bs4 import BeautifulSoup
import util

def parse_packlist_pack(obj):
	x = util.extract_str
	return {
		"name": x(obj["packname"], ">", "</a>"),
		"id": x(obj["packname"], "pack/", "\""),
		"average": float(x(obj["average"], "\" />", "</span>")),
		"date": obj["date"],
		"size": util.parse_filesize(obj["size"]),
		"votes": int(x(obj["r_avg"], "title='", " votes")),
		"rating": float(x(obj["r_avg"], "votes'>", "</div>")),
		"download": x(obj["download"], "href=\"", "\">")
	}

def get_packlist(start=0, length=-1):
	data = {"start": start, "length": length}
	r = util.post("pack/packlist", data=data)
	
	packlist = json.loads(r.content)["data"]
	return [parse_packlist_pack(pack) for pack in packlist]

def parse_song_row(song):
	cells = song.find_all("td")
	link = cells[0].find("a")
	
	difficulties = {}
	for diff_span in cells[3].find_all("span"):
		diff = diff_span["title"].lower()
		difficulties[diff] = float(diff_span.string.strip())
	
	try:
		subtitle = cells[0].contents[-1].strip()
	except:
		subtitle = cells[0].contents[-1].get_text().strip()
	
	return {
		"id": int(util.extract_str(link["href"], "view/")),
		"name": link.get_text().strip(),
		"subtitle": subtitle,
		"artist": cells[1].get_text().strip(),
		"step_artist": cells[2].get_text().strip(),
		"difficulties": difficulties,
		"num_scores": int(cells[4].get_text()),
	}

def get_pack(id_):
	soup = BeautifulSoup(util.get(f"pack/{id_}").content, features="html5lib")
	
	song_row_iterator = soup.find("tbody").find_all("tr")[1:]
	
	return [parse_song_row(s) for s in song_row_iterator]

# Finds the chartkey of a given id by downloading the song's html page
# and extracting the chartkey from there.
def get_chartkey(songid):
	html = util.get(f"song/view/{songid}").text
	return util.extract_str(html, '"data":{"chartkey": "', '"')

# Parse EO-format goal json
def parse_goal(goal):
	x = util.extract_str
	return {
		"songname": x(goal["songname"], '">', "</a>"),
		"songid": int(x(goal["songname"], "view/", '"')),
		"difficulty": float(x(goal["difficulty"], ">", "<")),
		"rate": float(goal["rate"]),
		"percent": float(goal["wife"][:-1]),
		"time_assigned": datetime.fromisoformat(goal["timeAssigned"]),
		"time_achieved": None if goal["timeAchieved"] == "Not yet achieved"
				else datetime.fromisoformat(goal["timeAchieved"])
	}

def get_goals(userid):
	r = util.post("user/getGoals", data={"userid": userid})
	goals_json = json.loads(r.content)["data"]
	return [parse_goal(goal) for goal in goals_json]

# Convert a list of goals into the XML format that's used in the
# Etterna.xml. Written for mondelointain cuz he lost his goals but they
# were still on EO
def goals_to_xml(goals):
	root = Element("ScoreGoals")

	for goal in goals:
		# Not sure if this is correct. *Chart* key is derived from
		# *song* id?
		chartkey = get_chartkey(goal["songid"])
		chart_goals_elem = root.find(f'.//GoalsForChart[@Key="{chartkey}"]')
		
		if chart_goals_elem is None:
			chart_goals_elem = SubElement(root, "GoalsForChart")
			chart_goals_elem.set("Key", chartkey)
		
		goal_elem = SubElement(chart_goals_elem, "ScoreGoal")
		SubElement(goal_elem, "Priority").text = "1"
		SubElement(goal_elem, "Comment").text = ""
		SubElement(goal_elem, "Rate").text = str(goal["rate"])
		SubElement(goal_elem, "Percent").text = str(goal["percent"])
		SubElement(goal_elem, "TimeAssigned").text = util.format_datetime(goal["time_assigned"])
	
	return root

