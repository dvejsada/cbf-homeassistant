# 🏀 CBF Basketball for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4.svg)](https://www.home-assistant.io/)

**Never miss a game again.** Follow your team from any Czech Basketball Federation (ČBF) competition – from the top league down to your local *3. třída* – right in Home Assistant.

🇨🇿 [Česká verze návodu](README.cs.md)

---

## ✨ What you get

- 📅 **Calendar** with all your team's games – venue, round, and results once played
- ⏰ **Next game** – when, where and against whom, plus your head‑to‑head record against that opponent
- 🏁 **Last game** – final score, win/loss and score per quarter
- 📊 **Standings** – table position, points, wins and losses (and the full table for your dashboard)
- 🔥 **Streak** and **games remaining** in the season
- 🇨🇿 Fully translated to Czech and English
- 🤝 Gentle on the ČBF server – data are refreshed every 3 hours by default

## 📦 Installation

**You need:** Home Assistant **2026.10 or newer** with the community store – called **Marketplace** since Home Assistant 2026.11 (*Settings → Marketplace*), **HACS** in older versions.

### Via the Marketplace / HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dvejsada&repository=cbf-homeassistant&category=integration)

Or step by step:

1. Open the **Marketplace** (or **HACS**) → menu **⋮** → **Custom repositories**.
2. Add `https://github.com/dvejsada/cbf-homeassistant` with type **Integration**.
3. Find **CBF Basketball** and click **Download**.
4. **Restart** Home Assistant.

### Manual installation

Copy the `custom_components/cbf` folder into your Home Assistant `config/custom_components/` folder and restart Home Assistant.

## ⚙️ Setup

[![Open your Home Assistant instance and start setting up CBF Basketball.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cbf)

Or go to **Settings → Devices & services → Add integration → CBF Basketball**, then:

1. **Season** – pre-filled with the current one (`2026` = season 2026/27).
   Type part of the competition name to narrow the list, e.g. `2.třída`.
2. **Category** – men, women, U13… (skipped if your search matches only one).
3. **Competition** – and its **phase** if there is more than one (e.g. regular season / play-off).
4. **Team** – pick yours. Done! 🎉

> 💡 **Shortcut:** if you have a link to your competition's schedule on the ČBF website that contains `p=…` (for example `…?p=10469`), paste it – or just the number – into the *Phase id or URL* field and jump straight to picking the team.

Want to follow more teams (your kids', your club's other squads)? Just add the integration again.

## 📋 Entities

Example for team *TJ ÚVN* on a Home Assistant set to **English**:

| Entity | Example state | Useful attributes |
|---|---|---|
| `calendar.tj_uvn` | `on` while a game is on | all games of the season |
| `sensor.tj_uvn_next_game` | date and time of tip-off | `date`, `opponent`, `home`, `venue`, `city`, `round`, `head_to_head` |
| `sensor.tj_uvn_next_opponent` | `Sokol Dolní Počernice C` | `home` |
| `sensor.tj_uvn_last_game` | `54:83` *(your score first)* | `opponent`, `date`, `outcome`, `periods` |
| `sensor.tj_uvn_last_game_outcome` | `Loss` | |
| `sensor.tj_uvn_table_position` | `7` | `wins`, `losses`, `points_scored`, `points_conceded`, `table` |
| `sensor.tj_uvn_table_points` | `9` | |
| `sensor.tj_uvn_games_remaining` | `15` | |
| `sensor.tj_uvn_streak` | `L2` *(2 losses in a row; W = wins)* | |
| `sensor.tj_uvn_last_update` | when data were last fetched | |

⚠️ Entity IDs depend on your **team's name** and your **Home Assistant language** – on a Czech system they are Czech (e.g. `sensor.tj_uvn_pristi_utkani`, see the [Czech README](README.cs.md#-entity)). Check yours on the team's device page and adjust the examples below.

## 🖼️ Dashboard ideas

Add these via **Dashboard → Edit → Add card → Manual**.

**Next game & standings card**

```yaml
type: entities
title: 🏀 TJ ÚVN
entities:
  - entity: sensor.tj_uvn_next_game
    name: Next game
    format: datetime
  - type: attribute
    entity: sensor.tj_uvn_next_game
    attribute: opponent
    name: Opponent
  - type: attribute
    entity: sensor.tj_uvn_next_game
    attribute: venue
    name: Venue
  - entity: sensor.tj_uvn_last_game
    name: Last result
  - entity: sensor.tj_uvn_table_position
    name: Position
  - entity: sensor.tj_uvn_streak
```

**League table** (Markdown card)

```yaml
type: markdown
title: Table
content: |
  | # | Team | W | L | Pts |
  |---|---|---|---|---|
  {%- for t in state_attr('sensor.tj_uvn_table_position', 'table') or [] %}
  | {{ t.position }} | {{ t.team }} | {{ t.wins }} | {{ t.losses }} | **{{ t.points }}** |
  {%- endfor %}
```

**Schedule** – add a **Calendar** card with `calendar.tj_uvn`.

## 🤖 Automation ideas

Create them via **Settings → Automations & scenes → Create automation → ⋮ → Edit in YAML**, and replace `notify.mobile_app_your_phone` with your own notification action.

**Reminder 3 hours before tip-off** (uses the built-in calendar trigger):

```yaml
alias: Basketball – game reminder
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.tj_uvn
    offset: "-3:00:00"
conditions:
  # skip games whose tip-off time is not confirmed yet (all-day events)
  - condition: template
    value_template: "{{ not trigger.calendar_event.all_day }}"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: 🏀 Game today
      message: >
        {{ trigger.calendar_event.summary }}
        {{ trigger.calendar_event.location or '' }}
mode: single
```

**Notify when a new result is in:**

```yaml
alias: Basketball – new result
triggers:
  - trigger: state
    entity_id: sensor.tj_uvn_last_game
    not_from: [unknown, unavailable]
    not_to: [unknown, unavailable]
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: 🏀 Final score
      message: >
        vs {{ trigger.to_state.attributes.opponent }}:
        {{ trigger.to_state.state }}
        {{ iif(trigger.to_state.attributes.outcome == 'win', '🏆 Win!', '(loss)') }}
mode: queued
```

## 🔄 New season or play-off

When every game of the season has a result, Home Assistant shows a notice under **Settings → Repairs**. Once the new season (or the play-off) is published by ČBF, go to **Settings → Devices & services → CBF Basketball**, open the entry's **⋮** menu → **Reconfigure** and pick the new competition phase. Your entities, dashboards, automations and history keep working.

## 🛠️ Options

**Settings → Devices & services → CBF Basketball → Configure**

- **Update interval** – 1 to 24 hours (default 3 h). Please don't set it lower than you need; the ČBF server is shared by everyone.

## ❓ FAQ

**The next game shows "Unknown", although the game is in the schedule.**
The league hasn't confirmed the tip-off time yet (ČBF publishes such games with time `00:00`). The date is in the sensor's `date` attribute, and the calendar shows the game as an all-day event marked *time TBC* (so the calendar is `on` that whole day).

**A postponed game is missing from the calendar.**
Postponed games without a new date are left out until ČBF publishes the new date.

**My team is lower in the table than its record suggests.**
ČBF ranks by table points (2 for a win, 1 for a loss), so teams that have played fewer games can rank lower for now.

**The result of tonight's game isn't there yet.**
Results appear once they are entered into the ČBF system – often the same evening, sometimes the next day – and are picked up at the next update.

**Something isn't working.**
Open an [issue](https://github.com/dvejsada/cbf-homeassistant/issues) and attach the diagnostics (integration entry → **⋮** → **Download diagnostics**; referee names are left out).

## ℹ️ About the data

Data come from the public [ČBF XML exports](https://cbf.cz.basketball/xml-exporty/p58). This project is not affiliated with or endorsed by Česká basketbalová federace.
