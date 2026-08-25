# Draftligaen — FPL Draft Stats

All-time stats site for our Fantasy Premier League **Draft** league. Static site, no backend — the page fetches two CSV files at load time and computes every table, record, and head-to-head on the fly in the browser.

**Live site:** https://scorelax.github.io/fpl-draft-stats/

## Structure

```
index.html        the app — layout, styling, all stat/record calculations
data/
  draft.csv          one row per manager per season: draft pick + final placement
  matches.csv        one row per manager per round: points scored + opponent + opponent's points
  ownership.csv       one row per FPL-player ownership stint per manager per season (see below)
  player-gameweeks.csv one row per manager+gameweek+player who started that gameweek (see below)
  manager-map.json    FPL Draft API entry_id -> our canonical manager name (see below)
scripts/
  update_matches.py           pulls finished current-season matches from the FPL API into matches.csv
  update_ownership.py         pulls draft picks + transactions into ownership.csv
  update_player_gameweeks.py  pulls each manager's starting-XI player points per finished gameweek into player-gameweeks.csv
.github/workflows/
  update-matches.yml   runs all three scripts daily and commits any changes
```

`data/` is the database. `index.html` never hardcodes results — it loads `data/matches.csv` and `data/draft.csv` with `fetch()` on page load and derives everything (all-time table, luck/expected-wins, streaks, records, head-to-head) from those two files. To update the site, you edit the CSVs — the app itself shouldn't need to change.

### `data/draft.csv`
| column | meaning |
|---|---|
| `season` | e.g. `2025/26` |
| `manager` | manager name (must match spelling used in `matches.csv`) |
| `draft_pick` | draft position that season (1 = first pick) |
| `placement` | final league position that season (1 = champion) |

### `data/matches.csv`
| column | meaning |
|---|---|
| `season` | e.g. `2025/26` |
| `round` | gameweek/round number |
| `manager` | manager name |
| `points` | that manager's points that round |
| `opponent` | who they played |
| `opponent_points` | opponent's points that round |

Each fixture appears twice (once as each manager's row), which is what the existing files already do — keep that pattern.

### `data/ownership.csv`
| column | meaning |
|---|---|
| `season` | e.g. `2026/27` |
| `manager` | manager name |
| `element_id` | FPL's internal player ID |
| `player` | player's full name at the time of fetching |
| `event_in` | gameweek this ownership stint began (drafted, or picked up via waiver/trade) |
| `event_out` | gameweek this stint ended (dropped); blank if still owned |

One row per **ownership stint**, not per player — if a manager drafts a player, drops them, then re-adds them later, that's two rows. This is deliberately a raw fact log (same philosophy as the other two CSVs): `index.html` derives stats like "most selected player" from it client-side rather than the script pre-computing an aggregate. Only covers 2026/27 onward — the FPL API doesn't expose this for seasons before we started tracking it, and we don't have the past seasons' league IDs even if it did.

### `data/player-gameweeks.csv`
| column | meaning |
|---|---|
| `season` | e.g. `2026/27` |
| `manager` | manager name |
| `event` | gameweek number |
| `element_id` | FPL's internal player ID |
| `player` | player's full name at the time of fetching |
| `points` | that player's FPL points that gameweek |

One row per manager+gameweek+player **who started that gameweek** for that manager (bench players are omitted entirely — they contributed nothing). Feeds "most points earned" (sum of `points` grouped by player, per manager) and "most played" (count of rows grouped by player, per manager) on the manager profiles. Only covers 2026/27 onward, same reason as `ownership.csv`.

Note on the underlying API: `GET /api/entry/<entry_id>/event/<gw>` returns 15 `picks` per manager per gameweek, each with a `multiplier` field — but that field is **not reliable** for telling starters from bench; it reports `1` for all 15 picks regardless of bench status. The real signal is `position`: `1`-`11` is the starting XI, `12`-`15` is the bench (verified against every manager's actual gameweek score, which is exactly the sum of their `position<=11` picks' points from `GET /api/event/<gw>/live`).

### `data/manager-map.json`

The FPL Draft API's league endpoint (`GET /api/league/<id>/details`) identifies managers by `entry_id` (a stable per-account ID) and gives their fantasy team name (`entry_name`, e.g. "Trobels FC") — which changes season to season and doesn't match the `manager` names used in our CSVs. This file is the translation layer: `entry_id -> our canonical manager name`, keyed off the person (`player_first_name`/`player_last_name`), not their team name, so re-fetching the league never creates duplicate managers just because someone renamed their team. Our league ID (2485) is recorded here too. Update this file only when someone new joins the league.

## Adding a new season

1. Append rows to `data/matches.csv` for every round played (both sides of each fixture).
2. Append one row per manager to `data/draft.csv` once the draft order is known (placement can be updated later, once the season finishes).
3. Add the new season string (e.g. `"2026/27"`) to the `SEASON_ORDER` array near the top of the `<script>` block in `index.html` — this controls season ordering everywhere (tabs, career streak chronology, etc.).
4. Commit and push — GitHub Pages redeploys automatically.

## Running locally

Because the page loads the CSVs via `fetch()`, opening `index.html` directly from disk (a `file://` URL) won't work — browsers block local file fetches for security. Serve the folder instead:

```bash
python -m http.server 8000
```

then open `http://localhost:8000/`.

## Deploying (GitHub Pages)

1. Push this repo to GitHub.
2. Repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main`, folder: `/ (root)`.
3. GitHub gives you a `https://<user>.github.io/<repo>/` URL a minute or two later.

No build step, no dependencies — it's a static site.

## Live current-season data from the FPL API

`scripts/update_matches.py` pulls the current season's finished matches from the public FPL Draft API (`GET /api/league/2485/details` — no login needed) and rewrites that season's block in `data/matches.csv`. It re-fetches and replaces the whole season's block every run (not an incremental append), so a late score correction from FPL is picked up automatically rather than left stale. If someone joins the league whose `entry_id` isn't in `manager-map.json` yet, the script exits with an error instead of guessing — add them to the map and re-run.

`.github/workflows/update-matches.yml` runs that script once a day (00:00 UTC — adjust the cron if you want it closer to Oslo midnight, which drifts between UTC+1/+2 with DST) and commits+pushes `data/matches.csv` only if it actually changed. It can also be triggered manually from the repo's **Actions** tab (`workflow_dispatch`). Once a season is fully finished, just stop caring about the workflow's runs — a "no changes" run is a harmless no-op — or disable it from the Actions tab.

To run either by hand instead:
```bash
python scripts/update_matches.py
python scripts/update_ownership.py
python scripts/update_player_gameweeks.py
```

`scripts/update_ownership.py` combines `GET /api/draft/2485/choices` (initial draft squads — note the URL says "draft" but the path parameter is actually the **league ID**, not the draft's own `id` field from `league.drafts[]`, despite what the endpoint name implies) with `GET /api/draft/league/2485/transactions` (every accepted waiver/free-agent move) to reconstruct each manager's full ownership history and write it to `ownership.csv`.

`scripts/update_player_gameweeks.py` fetches, for every finished gameweek, each manager's starting XI (`GET /api/entry/<entry_id>/event/<gw>`, `position<=11`) and those players' points that gameweek (`GET /api/event/<gw>/live`), and writes it to `player-gameweeks.csv`. This feeds the manager profiles' **most points earned** (only counting gameweeks where the player wasn't benched) and **most played** (contributed gameweeks) stats. See the `player-gameweeks.csv` section above for the `multiplier`-vs-`position` gotcha this ran into.

Not yet automated: `data/draft.csv` itself — draft pick order (fetched manually via `/api/draft/<league_id>/choices` once the draft completes) and final placement (once the season ends) both still need adding by hand (see "Adding a new season" above).
