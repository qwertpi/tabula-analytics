import json
import yaml
from requests import Response, get
from tqdm import tqdm

URLS = ["https://tabula.warwick.ac.uk/api/v1/member/me",
    "https://tabula.warwick.ac.uk/api/v1/member/me/assignments",
    "https://tabula.warwick.ac.uk/api/v1/member/me/attendance"]

with open("config.yaml", "r", encoding="utf8") as f:
    session_cookie: str = yaml.safe_load(f).get("auth").get("session_cookie")

def save_tabula_endpoint(url: str):
    response: Response = get(url,
        headers={'X-Requested-With': "XMLHttpRequest"},
        cookies={'__Host-SSO-Tabula-SSC': session_cookie},
        timeout=5)

    response.raise_for_status()

    with open(f"data/{url.split('/')[-1]}.json", "w", encoding="utf8") as f:
        json.dump(response.json(), f)

for url in tqdm(URLS):
    save_tabula_endpoint(url)
