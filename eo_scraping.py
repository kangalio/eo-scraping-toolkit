import json
import util
from bs4 import BeautifulSoup

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

def get_chartkey(chartid):
	html = util.get(f"song/view/{chartid}").text
	return util.extract_str(html, '"data":{"chartkey": "', '"')

def get_goals(userid):
	params = {
		"start": 0,
		"length": -1,
		"userid": userid
	}
	r = util.post("user/getGoals", params=params)
	goals = json.loads(r.content)
	return goals
