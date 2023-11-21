import argparse
import datetime
import json
import os
import sys
import time
import urllib.request

BASE_URL = "https://api.football-data.org/v4/teams"
ONE_DAY = 24 * 60 * 60  # seconds
DISPLAY = 5

cur_dir = os.path.dirname(os.path.realpath(__file__))
now_timestamp = time.time()
UTC_OFFSET = datetime.datetime.fromtimestamp(
    now_timestamp
) - datetime.datetime.utcfromtimestamp(now_timestamp)


def get_cache_name(team_id):
    return f"{cur_dir}/cache_{team_id}.json"


def get_image_dir():
    return f"{cur_dir}/images"


def get_from_cache(team_id):
    cache_name = get_cache_name(team_id)
    if (
        not os.path.exists(cache_name)
        or (os.path.getmtime(cache_name) + ONE_DAY) < time.time()
    ):
        return None
    with open(cache_name, "r") as f:
        return f.read()


def get_from_live(team_id, api_key):
    url = f"{BASE_URL}/{team_id}/matches"
    headers = {"X-Auth-Token": api_key}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as f:
        content = f.read().decode("utf-8")
    cache_name = get_cache_name(team_id)
    with open(cache_name, "w") as f:
        f.write(content)
    return content


def parse_matches(content):
    return json.loads(content)["matches"]


def download_icon(url):
    image_dir = get_image_dir()
    os.makedirs(image_dir, exist_ok=True)
    file_name = os.path.join(image_dir, os.path.basename(url))
    if os.path.exists(file_name):
        return
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as url_f:
        with open(file_name, "wb") as out_f:
            out_f.write(url_f.read())


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
    d = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    d += UTC_OFFSET
    return d.strftime("%Y-%m-%d (%A) %H:%M")


def main(team_id, api_key):
    content = get_from_cache(team_id) or get_from_live(team_id, api_key)
    matches = parse_matches(content)
    download_icons(matches)
    today = datetime.datetime.utcnow().date().strftime("%Y-%m-%d")
    matches = filter(lambda m: m["utcDate"] >= today, matches)
    matches = sorted(matches, key=lambda m: m["utcDate"])

    image_dir = get_image_dir()
    output = {
        "items": [
            {
                "title": f"{m['homeTeam']['shortName']} vs {m['awayTeam']['shortName']}",
                "subtitle": f"{m['competition']['name']} - {convert_date(m['utcDate'])}",
                "icon": {"path": f"{image_dir}/{get_opponent_icon(m, team_id)}"},
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
