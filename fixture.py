import argparse
import datetime
from dateutil import tz
import json
import os
import requests
import sys
import time

BASE_URL = "https://api.football-data.org/v4/teams"
ONE_DAY = 24 * 60 * 60  # seconds
DISPLAY = 5


def get_cache_fn(team_id):
    dir_name = os.path.dirname(os.path.realpath(__file__))
    return f"{dir_name}/cache_{team_id}.json"


def get_image_dir():
    dir_name = os.path.dirname(os.path.realpath(__file__))
    return f"{dir_name}/images"


def get_from_cache(team_id):
    cache_fn = get_cache_fn(team_id)
    if (
        not os.path.exists(cache_fn)
        or (os.path.getmtime(cache_fn) + ONE_DAY) < time.time()
    ):
        return None
    with open(cache_fn, "r") as f:
        return f.read()


def get_from_live(team_id, api_key):
    url = f"{BASE_URL}/{team_id}/matches"
    headers = {"X-Auth-Token": api_key}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(resp.status_codee)
    content = resp.text
    cache_fn = get_cache_fn(team_id)
    with open(cache_fn, "w") as f:
        f.write(content)
    return content


def parse_matches(content):
    return json.loads(content)["matches"]


def download_icon(url):
    file_name = os.path.join("images", os.path.basename(url))
    if os.path.exists(file_name):
        return
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        return
    with open(file_name, "wb") as f:
        for chunk in resp:
            f.write(chunk)


def download_icons(matches):
    for m in matches:
        download_icon(m["homeTeam"]["crest"])
        download_icon(m["awayTeam"]["crest"])


def get_opponent_icon(match, team_id):
    if match["homeTeam"]["id"] == team_id:
        opp_icon = match["awayTeam"]["crest"]
    else:
        opp_icon = match["homeTeam"]["crest"]
    return os.path.basename(opp_icon)


def convert_date(date_str):
    utc = tz.gettz("UTC")
    localtz = tz.tzlocal()
    d = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=utc)
    return d.astimezone(localtz).strftime("%Y-%m-%d (%A) %H:%M")


def main(team_id, api_key):
    content = get_from_cache(team_id) or get_from_live(team_id, api_key)
    matches = parse_matches(content)
    download_icons(matches)
    today = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")
    matches = filter(lambda m: m["utcDate"] > today, matches)
    matches = sorted(matches, key=lambda m: m["utcDate"])

    image_dir = get_image_dir()
    output = {
        "items": [
            {
                "title": f"{m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}",
                "subtitle": f"{m['competition']['name']} - {convert_date(m['utcDate'])}",
                "icon": {
                    "path": f"{image_dir}/{get_opponent_icon(m, team_id)}"
                },
            }
            for m in matches[:DISPLAY]
        ]
    }
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, required=True)
    parser.add_argument("--team-id", type=int, required=True)
    args = parser.parse_args()
    main(args.team_id, args.api_key)
