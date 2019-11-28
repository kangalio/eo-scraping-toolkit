import json
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import eo_scraping, util
from eo_scraping import *

# ~ goals = get_goals(11968)
with open("goals.json") as f:
	goals = json.load(f)

root = Element("ScoreGoals")

for goal_json in goals["data"]:
	chartid = util.extract_str(goal_json["songname"], "view/", '"')
	chartkey = get_chartkey(chartid)
	chart_goals = root.find(f'.//GoalsForChart[@Key="{chartkey}"]')
	
	if chart_goals is None:
		chart_goals = SubElement(root, "GoalsForChart")
		chart_goals.set("Key", chartkey)
	
	goal = SubElement(chart_goals, "ScoreGoal")
	SubElement(goal, "Priority").text = "1"
	SubElement(goal, "Comment").text = ""
	SubElement(goal, "Rate").text = str(goal_json["rate"])
	percent = float(goal_json["wife"][:-1]) / 100
	SubElement(goal, "Percent").text = str(percent)
	SubElement(goal, "TimeAssigned").text = goal_json["timeAssigned"]

print(tostring(root).decode("UTF-8"))
