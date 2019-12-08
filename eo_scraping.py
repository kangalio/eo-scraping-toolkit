import json
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement
from bs4 import BeautifulSoup
import util
from util import extract_str, Grade

skillset_names = ["Stream", "Jumpstream", "Handstream", "Stamina", "JackSpeed", "Chordjack", "Technical"]
judgement_names = ["Marvelous", "Perfect", "Great", "Good", "Bad", "Miss"]
judgement_ids = ["W1", "W2", "W3", "W4", "W5", "Miss"]

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
def get_chartkeys(songid):
	html = util.get(f"song/view/{songid}").text
	chartkeys = util.extract_strs(html, '"data":{"chartkey": "', '"')
	chartkeys = list(dict.fromkeys(chartkeys)) # Remove duplicates
	return chartkeys

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
	response = util.post("user/getGoals", data={"userid": userid})
	return [parse_goal(goal) for goal in response.json()["data"]]

def parse_score(score):
	judgement_amounts = []
	for j in judgement_names:
		number = int(extract_str(score["wifescore"], j, "<")[2:])
		judgement_amounts.append(number)
	
	skillsets = [float(score[s.lower()] or 0) for s in skillset_names]
	
	return {
		"judgements": judgement_amounts,
		"wifescore": float(extract_str(score["wifescore"], "'>", "%")) / 100,
		"songid": int(extract_str(score["songname"], "view/", '"')),
		"songname": extract_str(score["songname"], ">", "<"),
		"skillsets": skillsets,
		"overall": max(skillsets),
		"rate": float(score["user_chart_rate_rate"]),
		"nerf": float(score["Nerf"]),
		"datetime": score["datetime"],
		"chordcohesion": score["nocc"] == "On",
		"scorekey": score["scorekey"],
	}

def get_scores(userid):
	response = util.post(f"score/userScores", data={"userid": userid})
	return [parse_score(score) for score in response.json()["data"]]

# Convert a list of goals into the XML format that's used in the
# Etterna.xml. Written for mondelointain cuz he lost his goals but they
# were still on EO
def goals_to_xml(goals):
	root = Element("ScoreGoals")

	for goal in goals:
		chartkeys = get_chartkeys(goal["songid"])
		chartkey = chartkeys[0] # Hacky, and it will break. :/
		
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

def scores_to_xml(scores):
	root = Element("PlayerScores")
	
	for score in scores:
		chartkeys = get_chartkeys(score["songid"])
		# We don't know which diff/chart it is cuz EO is weird. For
		# development we simply assume the first diff
		chartkey = chartkeys[0]
		
		chart_elem = root.find(f'Chart[@Key="{chartkey}"]')
		if chart_elem is None:
			chart_elem = SubElement(root, "Chart")
			chart_elem.set("Key", chartkey)
			chart_elem.set("Pack", "") # unknown
			chart_elem.set("Song", score["songname"])
			chart_elem.set("Steps", "") # unknown
		
		rate_str = f"{score['rate']:.3f}"
		
		scoresat_elem = chart_elem.find(f'ScoresAt[@Rate="{rate_str}"]')
		if scoresat_elem is None:
			scoresat_elem = SubElement(chart_elem, "ScoresAt")
			scoresat_elem.set("BestGrade", Grade.F.as_xml_name())
			scoresat_elem.set("PBKey", "")
			scoresat_elem.set("Rate", rate_str)
		
		score_elem = SubElement(scoresat_elem, "Score")
		score_elem.set("Key", score["scorekey"])
		
		grade = Grade.from_wifescore(score["wifescore"])
		grade_str = grade.as_xml_name()
		best_grade = Grade.from_xml_name(scoresat_elem.get("BestGrade"))
		if grade.value > best_grade.value:
			scoresat_elem.set("BestGrade", grade_str)
		
		wifepoints = score["wifescore"] * sum(score["judgements"])
		
		dtime = datetime.fromisoformat(score["datetime"])
		datetime_str = util.format_datetime(dtime)
		
		util.add_xml_text_elements(score_elem, {
			"SSRCalcVersion": 263,
			"Grade": grade_str,
			"WifeScore": score["wifescore"],
			"WifePoints": wifepoints,
			"SSRNormPercent": score["wifescore"],
			"JudgeScale": 1, # J4 cuz EO normalizes everything to J4
			"NoChordCohestion": int(not score["chordcohesion"]),
			"EtternaValid": int(not score["chordcohesion"]),
			# unknown: SurviveSeconds
			# STUB: MaxCombo
			# STUB: Modifiers
			# unknown: MachineGuid
			"DateTime": datetime_str,
			# STUB: TopScore
		})
		
		judgements = {}
		for i in range(6):
			judgements[judgement_ids[i]] = score["judgements"][i]
		tap_note_scores_elem = SubElement(score_elem, "TapNoteScores")
		util.add_xml_text_elements(tap_note_scores_elem, judgements)
		
		# STUB: HoldNoteScores
		
		skillset_ssrs = {}
		for i in range(7):
			skillset_ssrs[skillset_names[i]] = score["skillsets"][i]
		skillset_ssrs_elem = SubElement(score_elem, "SkillsetSSRs")
		util.add_xml_text_elements(skillset_ssrs_elem, skillset_ssrs)
			
		# STUB: ValidationKeys
		
		servs_elem = SubElement(score_elem, "Servs")
		server_elem = SubElement(servs_elem, "server")
		server_elem.text = "https://api.etternaonline.com/v2"
	
	return root
		
