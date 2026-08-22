#!/usr/bin/env python3
"""Track FPL player ownership stints per manager for the current season.

Combines the initial draft squads with every accepted waiver/free-agent
transaction to reconstruct, for each manager, every distinct period they
owned each player (drafted, dropped, re-added later = two stints). Writes
data/ownership.csv, one row per stint - the raw fact log this is built on
top of, matching how matches.csv/draft.csv work: the CSV holds facts, the
app derives stats (like "most selected player") from it client-side.

Re-fetches and replaces the whole current season's block each run, same
idempotent approach as update_matches.py.
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

LEAGUE_ID = 2485
SEASON = "2026/27"  # update this each new season, alongside update_matches.py

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
    player_name = {p["id"]: p["web_name"] for p in bootstrap["elements"]}

    details = fetch_json(f"https://draft.premierleague.com/api/league/{LEAGUE_ID}/details")
    start_event = details["league"]["start_event"]

    for e in details["league_entries"]:
        if str(e["entry_id"]) not in entry_to_name:
            sys.exit(
                f"ERROR: entry_id {e['entry_id']} ({e['player_first_name']} {e['player_last_name']}) "
                f"is not in data/manager-map.json. Add it, then re-run."
            )

    choices = fetch_json(f"https://draft.premierleague.com/api/draft/{LEAGUE_ID}/choices")["choices"]
    transactions = fetch_json(f"https://draft.premierleague.com/api/draft/league/{LEAGUE_ID}/transactions")["transactions"]
    transactions = [t for t in transactions if t["result"] == "a"]
    transactions.sort(key=lambda t: t["added"])

    by_entry_choices = {}
    for c in choices:
        by_entry_choices.setdefault(c["entry"], []).append(c["element"])

    by_entry_txns = {}
    for t in transactions:
        by_entry_txns.setdefault(t["entry"], []).append(t)

    stints = []  # (entry_id, element, event_in, event_out)
    for entry_id in entry_to_name:
        entry_id = int(entry_id)
        open_stints = {}  # element -> event_in
        for element in by_entry_choices.get(entry_id, []):
            open_stints[element] = start_event
        for t in by_entry_txns.get(entry_id, []):
            if t["element_out"] in open_stints:
                stints.append((entry_id, t["element_out"], open_stints.pop(t["element_out"]), t["event"]))
            open_stints[t["element_in"]] = t["event"]
        for element, event_in in open_stints.items():
            stints.append((entry_id, element, event_in, None))

    rows = []
    for entry_id, element, event_in, event_out in stints:
        name = entry_to_name[str(entry_id)]
        rows.append([
            SEASON, name, element, player_name.get(element, f"Unknown ({element})"),
            event_in, event_out if event_out is not None else "",
        ])
    rows.sort(key=lambda r: (r[1], r[4], r[2]))

    ownership_csv = DATA / "ownership.csv"
    header = ["season", "manager", "element_id", "player", "event_in", "event_out"]
    if ownership_csv.exists():
        with ownership_csv.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            existing = [row for row in reader if row and row[0] != SEASON]
    else:
        existing = []

    all_rows = existing + [[str(c) for c in row] for row in rows]

    with ownership_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"{SEASON}: wrote {len(rows)} ownership stint(s) across {len(entry_to_name)} manager(s).")


if __name__ == "__main__":
    main()
