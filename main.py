import json
from xml.etree import ElementTree
import eo_scraping, util
from eo_scraping import *

scores = get_scores(4877)
scores_elem = scores_to_xml(scores[:50])
print(util.xml_format(scores_elem))
