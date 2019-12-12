from xml.etree.ElementTree import Element, SubElement, ElementTree
from datetime import datetime
import eo_scraping
import util
from util import Grade

JUDGEMENT_IDS = ["W1", "W2", "W3", "W4", "W5", "Miss"]

verbose = False
def info(msg=""):
	if verbose: print(msg)

# Convert a list of goals into the XML format that's used in the
# Etterna.xml. Written for mondelointain cuz he lost his goals but they
# were still on EO
def goals_to_xml(goals):
	root = Element("ScoreGoals")

	for goal in goals:
		chartkeys = eo_scraping.get_chartkeys(goal["songid"])
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

def playlists_to_xml(playlists):
	root = Element("Playlists")
	
	for playlist in playlists:
		playlist_elem = SubElement(root, "Playlist")
		playlist_elem.set("Name", playlist["name"])
		
		chartlist_elem = SubElement(playlist_elem, "Chartlist")
		for chart in playlist["entries"]:
			chart_elem = SubElement(chartlist_elem, "Chart")
			
			# We don't know if it's index 0, but that's the issue; we
			# don't know.
			chartkey = eo_scraping.get_chartkeys(chart["songid"])[0]
			packname = eo_scraping.get_packs(chart["songid"])[0]["packname"]
			
			chart_elem.set("Key", chartkey)
			chart_elem.set("Pack", packname)
			chart_elem.set("Rate", str(chart["rate"]))
			chart_elem.set("Song", chart["songname"])
	
	return root

def handle_hit_data(data):
	hitlen = len(data[0])
	
	max_combo = 0
	combo = 0
	for hit in data:
		if hitlen == 5:
			time, offset_ms, column, _, row = hit
			# ~ offset = offset_ms / 1000
			# ~ print(f"{row} {offset:.6f} {column}")
		else:
			time, offset_ms, column, _ = hit
		
		if offset_ms <= 90:
			combo += 1
		else:
			if combo > max_combo: max_combo = combo
			combo = 0
	
	return {
		"maxcombo": max_combo,
	}

def scores_to_xml(scores, userid):
	root = Element("PlayerScores")
	
	for score_i, score in enumerate(scores):
		if score["wifescore"] == 0:
			continue # Skip invalid scores
		
		chartkeys = eo_scraping.get_chartkeys(score["songid"])
		# We don't know which diff/chart it is cuz EO is weird. For
		# development we simply assume the first diff
		chartkey = chartkeys[0]
		
		# Get existing or create new Chart element
		chart_elem = root.find(f'Chart[@Key="{chartkey}"]')
		if chart_elem is None:
			chart_elem = SubElement(root, "Chart")
			chart_elem.set("Key", chartkey)
			chart_elem.set("Pack", "") # unknown
			chart_elem.set("Song", score["songname"])
			chart_elem.set("Steps", "") # unknown
		
		rate_str = f"{score['rate']:.3f}"
		
		# Get existing or create new ScoresAt element
		scoresat_elem = chart_elem.find(f'ScoresAt[@Rate="{rate_str}"]')
		if scoresat_elem is None:
			scoresat_elem = SubElement(chart_elem, "ScoresAt")
			scoresat_elem.set("BestGrade", Grade.F.as_xml_name())
			scoresat_elem.set("PBKey", "")
			scoresat_elem.set("Rate", rate_str)
		
		# Create new Score element
		score_elem = SubElement(scoresat_elem, "Score")
		score_elem.set("Key", score["scorekey"])
		
		grade = Grade.from_wifescore(score["wifescore"])
		grade_str = grade.as_xml_name()
		
		# Wifepoints = Wifescore * NumNotes * 2
		wifepoints = score["wifescore"] * sum(score["judgements"]) * 2
		
		max_combo = None
		
		score_info = eo_scraping.get_score(score["scorekey"], userid)
		if score_info is not None:
			chart_elem.set("Pack", score_info["packname"])
			datetime_str = score_info["datetime"]
			
			if score_info["hitdata"] is not None:
				hit_analysis = handle_hit_data(score_info["hitdata"])
				max_combo = hit_analysis["maxcombo"]
		else: # If score page 404'd
			# Fallback to the score-provided datetime without hours,
			# minutes or seconds
			dtime = datetime.fromisoformat(score["datetime"])
			datetime_str = util.format_datetime(dtime)
		
		info()
		info(f'[{score_i+1}/{len(scores)}]')
		info(f'Song: {score["songname"]}')
		info(f'Score: {round(score["wifescore"]*100, 2)}% ({grade.name})')
		info(f'Score rating: {max(score["skillsets"])}')
		info(f'Date: {datetime_str}')
		
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
			"MaxCombo": max_combo,
			"Modifiers": score_info and score_info["modifiers"],
			# unknown: MachineGuid
			"DateTime": datetime_str,
			# TopScore is added later
		})
		
		judgements = {}
		for i in range(6):
			judgements[JUDGEMENT_IDS[i]] = score["judgements"][i]
		tap_note_scores_elem = SubElement(score_elem, "TapNoteScores")
		util.add_xml_text_elements(tap_note_scores_elem, judgements)
		
		# missing: HoldNoteScores
		
		skillset_ssrs = {}
		for i in range(7):
			skillset_ssrs[util.SKILLSETS[i]] = score["skillsets"][i]
		skillset_ssrs["Overall"] = max(score["skillsets"])
		skillset_ssrs_elem = SubElement(score_elem, "SkillsetSSRs")
		util.add_xml_text_elements(skillset_ssrs_elem, skillset_ssrs)
			
		# missing: ValidationKeys
		
		servs_elem = SubElement(score_elem, "Servs")
		server_elem = SubElement(servs_elem, "server")
		server_elem.text = "https://api.etternaonline.com/v2"
	
	for scores_at_elem in root.iter("ScoresAt"):
		scores = list(scores_at_elem.iter("Score"))
		best_score = max(scores, key=lambda s: float(s.findtext("SSRNormPercent")))
		
		for score in scores:
			top_score_elem = SubElement(score, "TopScore")
			top_score_elem.text = "1" if (score == best_score) else "0"
		
		scores_at_elem.set("BestGrade", best_score.findtext("Grade"))
		scores_at_elem.set("PBKey", best_score.get("Key"))
	
	return root

def favorites_to_xml(favorites):
	root = Element("Favorites")
	
	for favorited in favorites:
		# We don't know which chart was favorited, so we assume index 0.
		chartkey = eo_scraping.get_chartkeys(favorited["songid"])[0]
		SubElement(root, chartkey)
	
	return root

def gen_general_data(username, scores):
	last_score = max(scores, key=lambda score: score["datetime"])
	
	root = Element("GeneralData")
	util.add_xml_text_elements(root, {
		"DisplayName": username,
		# Man there's a bunch of stuff in GeneralData but almost every-
		# thing is not accessible with EO data. Hopefully Etterna/SM
		# can make up for all the missing fields in the XML
	})
	
	return root

def gen_xml(username, userid, score_limit=None):
	root = Element("Stats")
	
	info()
	info("Downloading favorite charts...")
	favorites = eo_scraping.get_favorites(username)
	info(f"Converting {len(favorites)} favorited charts to XML format...")
	favorites_xml = favorites_to_xml(favorites)
	
	info()
	info("Downloading playlists...")
	playlists = eo_scraping.get_playlists(username)
	
	for playlist in playlists:
		info(f"- {playlist['name']}: {len(playlist['entries'])} charts")
	
	info(f"Converting {len(playlists)} playlists to XML format...")
	playlists_xml = playlists_to_xml(playlists)
	
	info()
	info("Downloading goals...")
	goals = eo_scraping.get_goals(userid)
	info(f"Converting {len(goals)} goals to XML format...")
	goals_xml = goals_to_xml(goals)
	
	info()
	info("Downloading scores...")
	scores = eo_scraping.get_scores(userid)
	if score_limit: scores = scores[:score_limit]
	info(f"Converting {len(scores)} scores to XML format...")
	scores_xml = scores_to_xml(scores, userid)
	
	general_data_xml = gen_general_data(username, scores)
	
	root.append(general_data_xml)
	root.append(favorites_xml)
	root.append(playlists_xml)
	root.append(goals_xml)
	root.append(scores_xml)
	
	return root
