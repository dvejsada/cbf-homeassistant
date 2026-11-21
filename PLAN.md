# CBF Home Assistant integration – plan (v2)

v2 incorporates a design review of v1 and research on HA changes up to 2026.11.

## Data source
CBF XML exports (https://cbf.cz.basketball/xml-exporty/p58), served from `https://www.cbf.cz/xml/`
(plain http times out). The page asks clients to use the server sparingly.
- `divs.php?s=<season>` – competitions + phases (config flow only)
- `sched.php?p=<phase>` – games
- `table.php?p=<phase>` – standings

### Data rules (verified against fixtures)
| Rule | Why |
|---|---|
| Played ⇔ `pts` ≠ 0/0 | unplayed games have score 0:0 **and** a placeholder partial 0:0 |
| `gdate = 0000-00-00` → unscheduled | postponed game without new date (game 551856); must not crash the refresh |
| `gtime = 00:00:00` → time unknown | 67/132 games; rounds 12+ are placeholder Mondays – shown as "date TBC" |
| Times are Europe/Prague local | localize with fixed `Europe/Prague`, not HA's timezone |
| Match teams by `<id>` only | names contain double/trailing spaces; normalise with `" ".join(s.split())` for display |
| Partials are cumulative Q1–Q3 | Q4 = final − Q3; overtime indistinguishable; parse 0..n partials defensively |
| Table ranks by points (win 2, loss 1) | expose gp/w/l so position isn't misleading with unequal games played |
| Past-dated game without result | "awaiting result" – never stays as *next game*, doesn't block *last game* |
| No ETag/Last-Modified, content-type text/html | no conditional GETs; don't validate MIME; parse with `defusedxml`, ignore DOCTYPE |

## Configuration
**One config entry per team** (`integration_type: service`), unique_id = CBF team id. The user follows one team; subentries (competition entry + team subentries) were considered but add UI complexity for no real gain here.

Config flow:
1. **Season** (default: current; Aug+ = this year) + **category** (muži, ženy, U13…) + optional search text
2. **Competition** – only those with ≥1 phase, labelled `name · category · league` (region isn't in the data; Prague leagues like "2.třída B" carry no marker)
3. **Phase** – skipped if single
4. **Team** – from table, falling back to schedule teams (playoff phases may have no table)

Escape hatch on step 1: paste a phase id or a cbf.cz URL containing `p=`.

- **Reconfigure flow** – re-point the entry to a new phase (new season / playoffs) keeping entities and history.
- **Options flow** (`OptionsFlowWithReload`) – base polling interval.
- **Repair issue** when every game of the phase is played (season over) → suggests reconfigure.

## Entities (one device per team, `DeviceEntryType.SERVICE`)
| Entity | State | Notes |
|---|---|---|
| `calendar.<team>` | – | all games; UID = game id (reschedules move, not duplicate); location = venue, city; 2 h events, all-day "date TBC" when time unknown; unscheduled games omitted |
| `sensor.<team>_next_game` | timestamp | `unknown` if date TBC (date in attribute); attrs: opponent, home/away, venue, city, round, game id |
| `sensor.<team>_next_opponent` | text | kept for simple dashboards/notifications |
| `sensor.<team>_last_game` | "54:83" (team perspective) | attrs: opponent, date, home/away, quarter scores, venue |
| `sensor.<team>_last_game_outcome` | enum `win`/`loss` | translated states |
| `sensor.<team>_position` | int, measurement | attrs: gp, w, l, points for/against, diff; full table as attribute (≈1.5 kB) excluded from recorder |
| `sensor.<team>_points` | int, measurement | table points |
| `sensor.<team>_games_remaining` | int | |
| `sensor.<team>_last_update` | timestamp, diagnostic | last successful fetch |

Referee names: exposed only in calendar description and excluded from recorder; redacted in diagnostics.
Next/last game sensors are recomputed at tip-off via `async_track_point_in_time`, independent of polling.

## Polling (per entry coordinator, 2 requests max per refresh)
| Situation | Interval |
|---|---|
| Default | 6 h (option, min 1 h) |
| No game within 3 days / season over | 24 h |
| After a game (tip-off + 2 h) until result appears | 30 min for 2 h, then hourly up to 24 h, then default |
| Error | keep last data, `UpdateFailed`, normal retry |

- Fetch `table.php` only when results in the schedule changed (≈ halves traffic).
- Small jitter, descriptive User-Agent, shared aiohttp session.
- Expected load: ~4–8 requests/day, ~15 on game days.

## Implementation notes (HA 2026.11, Python 3.14)
- `entry.runtime_data` with typed `CbfConfigEntry`; `async_forward_entry_setups` / `async_unload_platforms`; setup raises `ConfigEntryNotReady` (translated) instead of returning False.
- `DataUpdateCoordinator(config_entry=entry, always_update=False)`; dynamic `self.update_interval` set in `_async_update_data`.
- `async_get_clientsession(hass)` injected into an HA-free `api.py` (unit-testable parser).
- `has_entity_name` + `translation_key` everywhere; `PARALLEL_UPDATES = 0`; `DeviceInfo(...)` keyword construction only; `icons.json`; translated exceptions.
- `step_id` passed on every form; no `show_advanced_options`; no update listener alongside `OptionsFlowWithReload`.
- `manifest.json`: domain `cbf`, name, version, codeowners, documentation, issue_tracker, `config_flow`, `iot_class: cloud_polling`, `integration_type: service`, `requirements: [defusedxml]` if not bundled, `loggers`, `categories`.
- Brand images in `custom_components/cbf/brand/` (icon.png at minimum).
- `hacs.json` (`name`, `homeassistant: "2026.11.0"`), README (cs + en), CI: hassfest + `hacs/action`, pytest.
- Tests: parser on real fixtures (incl. 0000-00-00, TBC times), config + reconfigure flow, coordinator interval logic.

## Out of scope for v1
Auto-following playoff phases (use reconfigure), head-to-head stats, multiple teams sharing one fetch.
