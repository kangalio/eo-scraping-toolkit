import json, ast
from datetime import datetime
import util
from util import extract_str, extract_strs, Grade, JUDGEMENTS, SKILLSETS

def get_userid(username):
	user_page = util.get(f"user/{username}").text
	userid = extract_str(user_page, "'userid': '", "'")
	return int(userid)

def get_score(scoreid, userid):
	score_page = util.get(f"score/view/{scoreid}{userid}").text
	html = util.parse_html(score_page)
	
	data_div = html.find(id="songtitledatak")
	h5s = data_div.find_all("h5")
	
	judge = None
	if len(h5s) > 4:
		judge_str = h5s[4].string.strip()[6:]
		if judge_str != "":
			judge = int(judge_str)
	
	data_str = extract_str(score_page, "data: [[", "]]")
	if data_str is None:
		hit_data = None
	else:
		data_str = "[[" + data_str + "]]"
		hit_data = ast.literal_eval(data_str)
	
	return {
		"packname": h5s[0].find("a").get_text().strip(),
		"datetime": h5s[2].contents[-1].string.strip(),
		"modifiers": h5s[3].contents[-1].string.strip(),
		"judge": judge,
		"hitdata": hit_data,
	}

def get_playlists(username):
	html = util.parse_html(util.get(f"user/{username}").content)
	playlists = []
	for panel in html.select("#playlists>.panel"):
		title = panel.find(class_="panel-title").string.strip()
		
		entries = []
		for row in panel.find("tbody").find_all("tr"):
			cells = row.find_all("td")
			entries.append({
				"songname": cells[0].find("a").string.strip(),
				"songid": int(row.find("a")["href"][36:]),
				"rate": float(cells[1].string.strip()),
				"difficulty": float(cells[2].string.strip()),
			})
		
		playlists.append({
			"name": title,
			"entries": entries,
		})
	
	return playlists	

def get_favorites(username):
	html = util.parse_html(util.get(f"user/{username}").content)
	
	favorites = []
	for favorited in html.select("#favorites>.favorite"):
		stepper = favorited.find("span").get_text()
		if stepper == "": stepper = None
		
		favorites.append({
			"songname": favorited.find("a").string.strip(),
			"songid": int(favorited.find("a")["href"][36:]),
			"artist": favorited.find(class_="favorite-artist").string.strip(),
			"stepper": stepper,
		})
	
	return favorites

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

def get_pack(packid):
	soup = util.parse_html(util.get(f"pack/{packid}").content)
	
	song_row_iterator = soup.find("tbody").find_all("tr")[1:]
	
	return [parse_song_row(s) for s in song_row_iterator]

def parse_song_score(score):
	songscorekey = extract_str(score["score"], "view/", '"')
	return {
		"scorekey": songscorekey[:-4],
		"songid": songscorekey[:-4:]
		# TODO:
		# ~ "score": 
		# ~ "nerf": 
		# ~ "username": 
		# ~ "rate": 
		# ~ "wifescore": 
		# ~ "date": 
		# ~ "judgements": 
		# ~ "combo": 
	}

def get_song_scores(chartkey):
	response = util.post("score/chartOverallScores", {
		# ~ "order[0][column]": 2,
		# ~ "order[0][dir]": "desc",
		# ~ "search[value]": "",
		# ~ "search[regex]": "false",
		"draw": 1,
		"chartkey": chartkey,
		# ~ "start": 0,
		# ~ "length": -1,
		# ~ "top": "false",
	})
	
	data = response.json()["data"]
	return [parse_song_score(r) for r in data]

# Finds the chartkey of a given id by downloading the song's html page
# and extracting the chartkey from there.
def get_chartkeys(songid):
	html = util.get(f"song/view/{songid}").text
	chartkeys = util.extract_strs(html, '"data":{"chartkey": "', '"')
	chartkeys = list(dict.fromkeys(chartkeys)) # Remove duplicates
	return chartkeys

# Returns mapping (dict) from scorekey -> chartkey
def find_matching_diffs(songid, scorekeys):
	# Zero initialize mapping
	mapping = {scorekey: None for scorekey in scorekeys}
	
	chartkeys = get_chartkeys(songid)
	
	for chartkey in get_chartkeys(songid):
		print(f"Searching chartkey {chartkey}")
		for score in get_song_scores(chartkey):
			for scorekey in scorekeys:
				print(f"Comparing '{score['scorekey']}' and '{scorekey}'")
				if score["scorekey"] == scorekey:
					mapping[scorekey] = chartkey
					
					# If every scorekey is done mapped, return
					if not any(mapping[key] is None for key in scorekeys):
						return mapping
	
	msg = "Could not find "
	msg += ", ".join([key for key in scorekeys if mapping[key] is None])
	msg += f" in {songid}."
	raise Exception(msg)

def get_packs(songid):
	html = util.parse_html(util.get(f"song/view/{songid}").content)
	
	packs = []
	for pack_link in html.find(class_="in-packs-test").find_all("a"):
		packs.append({
			"packid": pack_link["href"],
			"packname": pack_link.get_text().strip(),
		})
	return packs

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
	for j in JUDGEMENTS:
		number = int(extract_str(score["wifescore"], j, "<")[2:])
		judgement_amounts.append(number)
	
	skillsets = [float(score[s.lower()] or 0) for s in SKILLSETS]
	
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

# if force_refresh parameter is set, the song list will be redownloaded to prevent missing scores
# that weren't present when this function result was last cached.
def get_scores(userid, force_refresh=False):
	response = util.post(f"score/userScores", data={"userid": userid}, cache=not force_refresh)
	return [parse_score(score) for score in response.json()["data"]]
