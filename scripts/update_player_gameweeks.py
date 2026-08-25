#!/usr/bin/env python3
"""Track each manager's starting-XI player points per finished gameweek.

Feeds the manager-profile stats "most points earned" (from a single FPL
player, counting only gameweeks that player started for that manager) and
"most played" (gameweeks that player started for that manager). Writes
data/player-gameweeks.csv, one row per manager+gameweek+player who started -
the raw fact log this is built on top of, matching how the other CSVs work:
the CSV holds facts, the app derives the "most points"/"most played" stats
from it client-side.

Note: /api/entry/<entry_id>/event/<gw>'s `multiplier` field is NOT reliable
for telling starters from bench - it reports 1 for all 15 picks regardless.
The actual signal is `position`: 1-11 is the starting XI, 12-15 is the bench
(verified against every manager's actual gameweek score, which is exactly
the sum of their position<=11 picks' points).

Re-fetches and replaces the whole current season's block each run, same
idempotent approach as update_matches.py/update_ownership.py, but only for
gameweeks the API reports as finished.
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

LEAGUE_ID = 2485
SEASON = "2026/27"  # update this each new season, alongside the other scripts

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-draft-stats-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    manager_map = json.loads((DATA / "manager-map.json").read_text(encoding="utf-8"))
    entry_to_name = manager_map["managers"]

    bootstrap = fetch_json("https://draft.premierleague.com/api/bootstrap-static")
    player_name = {p["id"]: f"{p['first_name']} {p['second_name']}".strip() for p in bootstrap["elements"]}
    finished_events = [e["id"] for e in bootstrap["events"]["data"] if e["finished"]]

    details = fetch_json(f"https://draft.premierleague.com/api/league/{LEAGUE_ID}/details")
    for e in details["league_entries"]:
        if str(e["entry_id"]) not in entry_to_name:
            sys.exit(
                f"ERROR: entry_id {e['entry_id']} ({e['player_first_name']} {e['player_last_name']}) "
                f"is not in data/manager-map.json. Add it, then re-run."
            )

    rows = []
    for gw in sorted(finished_events):
        live = fetch_json(f"https://draft.premierleague.com/api/event/{gw}/live")["elements"]
        for entry_id, name in entry_to_name.items():
            picks = fetch_json(f"https://draft.premierleague.com/api/entry/{entry_id}/event/{gw}")["picks"]
            for p in picks:
                if p["position"] > 11:
                    continue  # bench - didn't count
                element = p["element"]
                points = live[str(element)]["stats"]["total_points"]
                rows.append([SEASON, gw, name, element, player_name.get(element, f"Unknown ({element})"), points])

    rows.sort(key=lambda r: (r[1], r[2], r[3]))

    out_csv = DATA / "player-gameweeks.csv"
    header = ["season", "event", "manager", "element_id", "player", "points"]
    if out_csv.exists():
        with out_csv.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            existing = [row for row in reader if row and row[0] != SEASON]
    else:
        existing = []

    all_rows = existing + [[str(c) for c in row] for row in rows]

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"{SEASON}: wrote {len(rows)} row(s) across {len(finished_events)} finished gameweek(s).")


if __name__ == "__main__":
    main()
