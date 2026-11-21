# CBF Basketball for Home Assistant

[Česky níže](#česky)

Follow a team from Czech Basketball Federation (ČBF) competitions in Home Assistant: schedule as a calendar, next game, last result, table position and more. Data come from the public [CBF XML exports](https://cbf.cz.basketball/xml-exporty/p58).

## Installation

**HACS** – add this repository as a custom repository (type *Integration*), install **CBF Basketball**, restart Home Assistant.

**Manual** – copy `custom_components/cbf` into your `config/custom_components` and restart.

Then go to *Settings → Devices & services → Add integration → CBF Basketball*.

## Setup

1. **Season** (2026 = 2026/27) and optionally part of the competition name (e.g. `2.třída`). Alternatively paste a phase id or a cbf.cz URL containing `p=…`.
2. **Category** (men, women, U13, …) – skipped when the search matches one category.
3. **Competition** and **phase** (skipped when there is only one).
4. **Team**.

Each followed team is one entry/device. To follow a new season or the play-off, use **Reconfigure** on the entry – entities and their history are kept. A repair notice reminds you when all games of the phase have a result.

**Options:** update interval (default 3 h, 1–24 h). Please keep it gentle – the CBF server is shared.

## Entities

| Entity | State | Notable attributes |
|---|---|---|
| `calendar.<team>` | current/next game | all games of the phase; games without confirmed time are all-day events marked *time TBC* |
| Next game | tip-off (timestamp); `unknown` when the time is not confirmed | `date`, `opponent`, `home`, `venue`, `city`, `round`, `head_to_head` |
| Next opponent | name | `home` |
| Last game | score from the team's view, e.g. `54:83` | `opponent`, `date`, `outcome`, `periods` |
| Last game outcome | `win` / `loss` | |
| Table position | e.g. `7` | `games_played`, `wins`, `losses`, `points_scored`, `points_conceded`, `table` |
| Table points | e.g. `9` | |
| Games remaining | count | |
| Streak | e.g. `W2`, `L3` | |
| Last update (diagnostic) | timestamp | |

Next-game sensors move on at tip-off without an extra download. The table is downloaded only when a new result appears.

### Example automation

```yaml
triggers:
  - trigger: state
    entity_id: sensor.tj_uvn_last_game
conditions:
  - condition: template
    value_template: "{{ trigger.from_state.state not in ['unknown', 'unavailable'] }}"
actions:
  - action: notify.mobile_app_phone
    data:
      message: >
        {{ state_attr('sensor.tj_uvn_last_game', 'opponent') }}:
        {{ states('sensor.tj_uvn_last_game') }}
        ({{ states('sensor.tj_uvn_last_game_outcome') }})
```

## Notes on the data

- Games with time `00:00` in the export have no confirmed time yet; postponed games without a new date are left out of the calendar.
- The table ranks by points (win 2, loss 1), so teams with fewer games played may rank lower.
- Not affiliated with ČBF.

---

## Česky

Sledujte družstvo ze soutěží České basketbalové federace v Home Assistantu: rozpis jako kalendář, příští utkání, poslední výsledek, pořadí v tabulce a další. Data pocházejí z veřejných [XML exportů ČBF](https://cbf.cz.basketball/xml-exporty/p58).

### Instalace

**HACS** – přidejte tento repozitář jako vlastní repozitář (typ *Integrace*), nainstalujte **CBF Basketball** a restartujte Home Assistant.
**Ručně** – zkopírujte `custom_components/cbf` do `config/custom_components` a restartujte.

Poté *Nastavení → Zařízení a služby → Přidat integraci → CBF Basketball*.

### Nastavení

1. **Ročník** (2026 = 2026/27) a volitelně část názvu soutěže (např. `2.třída`), nebo vložte ID fáze či URL z cbf.cz obsahující `p=…`.
2. **Kategorie** – přeskočí se, pokud hledání odpovídá jediné kategorii.
3. **Soutěž** a **fáze** (přeskočí se, je-li jen jedna).
4. **Družstvo**.

Každé sledované družstvo je samostatná položka/zařízení. Pro nový ročník nebo play-off použijte **Přenastavit** – entity i jejich historie zůstanou. Až budou mít všechna utkání výsledek, upozorní vás oprava (repair).

**Možnosti:** interval aktualizace (výchozí 3 h, 1–24 h). Prosíme, šetřete server ČBF.

### Entity

Kalendář utkání, příští utkání, příští soupeř, poslední utkání (skóre z pohledu družstva), výsledek posledního utkání (výhra/prohra), pořadí v tabulce (včetně celé tabulky v atributu), body v tabulce, zbývající utkání, série (např. `W2` = 2 výhry v řadě) a čas poslední aktualizace.

Utkání s časem `00:00` nemají potvrzený čas – v kalendáři jsou celodenní s poznámkou *čas neurčen*. Integrace není spojena s ČBF.
