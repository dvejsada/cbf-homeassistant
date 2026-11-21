# CBF Home Assistant integration – plan

Data source: CBF XML exports (https://cbf.cz.basketball/xml-exporty/p58), served from `https://www.cbf.cz/xml/`:
- `divs.php?s=<season>` – competitions and phases (used only in the config flow)
- `sched.php?p=<phase>` – games: date/time, venue, teams, referees, score, cumulative partials
- `table.php?p=<phase>` – standings

Quirks: unplayed game = score 0:0; time `00:00:00` = time not set yet; team names contain extra spaces; plain http times out.

## Config flow
Season (+ optional search) → competition → phase (auto-skip if single) → team. One config entry / device per team.

## Entities (per team)
- `calendar.<team>` – all team games (2 h events, all-day when time unknown)
- `sensor.<team>_next_game` (timestamp) – attrs: opponent, home/away, venue, city, round, referees, game id
- `sensor.<team>_next_opponent`
- `sensor.<team>_last_game` – team-perspective score, attrs: opponent, date, partials
- `sensor.<team>_last_game_outcome` (enum win/loss)
- `sensor.<team>_position` – attrs: gp/w/l, points for/against, full table
- `sensor.<team>_points`

## Polling
2 requests per refresh, coordinator shared per phase.
- default every 6 h (option, min 1 h)
- game day: from tip-off + 2 h, every 30 min until result appears (max 6 h)
- on error keep last data

## Open questions
Polling intervals OK? Extra sensors (games remaining, head-to-head)? Auto-follow playoff phases? English code + cs/en translations?
