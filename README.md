# Draftligaen — FPL Draft Stats

All-time stats site for our Fantasy Premier League **Draft** league. Static site, no backend — the page fetches two CSV files at load time and computes every table, record, and head-to-head on the fly in the browser.

**Live site:** https://scorelax.github.io/fpl-draft-stats/

## Structure

```
index.html        the app — layout, styling, all stat/record calculations
data/
  draft.csv          one row per manager per season: draft pick + final placement
  matches.csv        one row per manager per round: points scored + opponent + opponent's points
  manager-map.json    FPL Draft API entry_id -> our canonical manager name (see below)
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

## Roadmap: live current-season data from the FPL API

Next step is wiring the current season's `data/matches.csv` rows to update automatically from the official FPL Draft API instead of manual entry, likely via a small scheduled script (e.g. a GitHub Actions workflow) that pulls results after each gameweek and commits the update. Not implemented yet — historic seasons (2020/21–2024/25, plus 2025/26) stay as committed CSV data either way.

The relevant endpoint is public and needs no login: `GET https://draft.premierleague.com/api/league/2485/details`. It returns:
- `league_entries` — one row per manager, including `entry_id` (see `manager-map.json` above) and `id` (the ID `matches`/`standings` reference for that season)
- `matches` — all 152 fixtures for the season, pre-populated with `event`, `league_entry_1`/`league_entry_2`, their points, `started`, `finished`
- `standings` — running W/D/L/points table

2026/27 (league ID 2485) is the first season this would apply to going forward.
