#!/usr/bin/env python3
"""Pull finished FPL Draft matches for the current season into data/matches.csv.

Re-fetches the whole league each run and replaces the current season's block
in matches.csv wholesale (idempotent) rather than appending incrementally, so
a late score correction from FPL is picked up automatically on the next run.
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

LEAGUE_ID = 2485
SEASON = "2026/27"  # update this each new season, alongside SEASON_ORDER in index.html

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-draft-stats-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    manager_map = json.loads((DATA / "manager-map.json").read_text(encoding="utf-8"))
    if manager_map.get("league_id") != LEAGUE_ID:
        print(f"warning: manager-map.json league_id {manager_map.get('league_id')} != {LEAGUE_ID}", file=sys.stderr)
    entry_to_name = manager_map["managers"]

    details = fetch_json(f"https://draft.premierleague.com/api/league/{LEAGUE_ID}/details")
    league_entries = details["league_entries"]

    id_to_name = {}
    for e in league_entries:
        name = entry_to_name.get(str(e["entry_id"]))
        if not name:
            sys.exit(
                f"ERROR: entry_id {e['entry_id']} ({e['player_first_name']} {e['player_last_name']}) "
                f"is not in data/manager-map.json. Add it, then re-run."
            )
        id_to_name[e["id"]] = name
    entry_order = [e["id"] for e in league_entries]  # fixed row order within each round

    finished = [m for m in details["matches"] if m["finished"]]
    by_round = {}
    for m in finished:
        by_round.setdefault(m["event"], []).append(m)

    new_rows = []
    for rnd in sorted(by_round):
        by_entry = {}
        for m in by_round[rnd]:
            by_entry[m["league_entry_1"]] = (m["league_entry_1_points"], m["league_entry_2"], m["league_entry_2_points"])
            by_entry[m["league_entry_2"]] = (m["league_entry_2_points"], m["league_entry_1"], m["league_entry_1_points"])
        for eid in entry_order:
            if eid not in by_entry:
                continue
            pts, opp_id, opp_pts = by_entry[eid]
            new_rows.append([SEASON, rnd, id_to_name[eid], pts, id_to_name[opp_id], opp_pts])

    matches_csv = DATA / "matches.csv"
    with matches_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        existing = [row for row in reader if row and row[0] != SEASON]

    all_rows = existing + [[str(c) for c in row] for row in new_rows]

    with matches_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"{SEASON}: wrote {len(new_rows)} rows across {len(by_round)} finished round(s).")


if __name__ == "__main__":
    main()
