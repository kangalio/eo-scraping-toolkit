from xml.etree.ElementTree import Element, SubElement, ElementTree
from datetime import datetime
import eo_scraping
import util
from util import Grade

JUDGEMENT_IDS = ["W1", "W2", "W3", "W4", "W5", "Miss"]

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

def scores_to_xml(scores, userid):
	root = Element("PlayerScores")
	
	for score in scores:
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
		
		# Wifepoints = Wifescore * NumNotes
		wifepoints = score["wifescore"] * sum(score["judgements"])
		
		score_info = eo_scraping.get_score(score["scorekey"], userid)
		if score_info is not None:
			chart_elem.set("Pack", score_info["packname"])
			datetime_str = score_info["datetime"]
		else: # If score page 404'd
			# Fallback to the score-provided datetime without hours,
			# minutes or seconds
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
		
		# STUB: HoldNoteScores
		
		skillset_ssrs = {}
		for i in range(7):
			skillset_ssrs[util.SKILLSETS[i]] = score["skillsets"][i]
		skillset_ssrs_elem = SubElement(score_elem, "SkillsetSSRs")
		util.add_xml_text_elements(skillset_ssrs_elem, skillset_ssrs)
			
		# STUB: ValidationKeys
		
		servs_elem = SubElement(score_elem, "Servs")
		server_elem = SubElement(servs_elem, "server")
		server_elem.text = "https://api.etternaonline.com/v2"
	
	for scores_at_elem in root.iter("ScoresAt"):
		scores = list(scores_at_elem.iter("Score"))
		best_score = max(scores, key=lambda s: s.get("SSRNormPercent"))
		
		for score in scores:
			top_score_elem = SubElement(score, "TopScore")
			top_score_elem.text = "1" if (score == best_score) else "0"
		
		scores_at_elem.set("BestGrade", best_score.findtext("Grade"))
		scores_at_elem.set("PBKey", best_score.get("Key"))
	
	return root

def gen_xml(userid, score_limit=None):
	root = Element("Stats")
	
	goals = eo_scraping.get_goals(userid)
	root.append(goals_to_xml(goals))
	
	scores = eo_scraping.get_scores(userid)
	if score_limit: scores = scores[:score_limit]
	root.append(scores_to_xml(scores, userid))
	
	# ~ return ElementTree(root)
	return root
