# Draftligaen — FPL Draft Stats

All-time stats site for our Fantasy Premier League **Draft** league. Static site, no backend — the page fetches two CSV files at load time and computes every table, record, and head-to-head on the fly in the browser.

**Live site:** _(add the GitHub Pages URL here once it's enabled — see below)_

## Structure

```
index.html        the app — layout, styling, all stat/record calculations
data/
  draft.csv       one row per manager per season: draft pick + final placement
  matches.csv     one row per manager per round: points scored + opponent + opponent's points
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

Next step is wiring the current season's `data/matches.csv` rows to update automatically from the official FPL Draft API instead of manual entry, likely via a small scheduled script (e.g. a GitHub Actions workflow) that pulls results after each gameweek and commits the update. Not implemented yet — historic seasons (2020/21–2024/25, plus anything already played in 2025/26) stay as committed CSV data either way.
