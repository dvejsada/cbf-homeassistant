# 🏀 CBF Basketball pro Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4.svg)](https://www.home-assistant.io/)

**Už nezmeškáte žádné utkání.** Sledujte své družstvo z libovolné soutěže České basketbalové federace (ČBF) – od nejvyšší ligy až po pražskou *3. třídu* – přímo v Home Assistantu.

🇬🇧 [English version](README.md)

---

## ✨ Co integrace umí

- 📅 **Kalendář** všech utkání družstva – hala, kolo a po odehrání i výsledek
- ⏰ **Příští utkání** – kdy, kde a s kým, včetně vzájemné bilance s tímto soupeřem
- 🏁 **Poslední utkání** – konečné skóre, výhra/prohra a skóre po čtvrtinách
- 📊 **Tabulka** – pořadí, body, výhry a prohry (a celá tabulka pro dashboard)
- 🔥 **Série** a **počet zbývajících utkání**
- 🇨🇿 Kompletně česky i anglicky
- 🤝 Šetrná k serveru ČBF – data se ve výchozím nastavení stahují jednou za 3 hodiny

## 📦 Instalace

### Přes HACS / Marketplace (doporučeno)

[![Otevřít tento repozitář v HACS ve vašem Home Assistantu.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dvejsada&repository=cbf-homeassistant&category=integration)

Nebo ručně:

1. Otevřete **Marketplace** (HACS) → menu **⋮** → **Vlastní repozitáře**.
2. Přidejte `https://github.com/dvejsada/cbf-homeassistant` s typem **Integrace**.
3. Najděte **CBF Basketball** a klikněte na **Stáhnout**.
4. **Restartujte** Home Assistant.

### Ruční instalace

Zkopírujte složku `custom_components/cbf` do `config/custom_components/` ve vašem Home Assistantu a restartujte ho.

## ⚙️ Nastavení

[![Spustit nastavení CBF Basketball ve vašem Home Assistantu.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cbf)

Nebo **Nastavení → Zařízení a služby → Přidat integraci → CBF Basketball** a dále:

1. **Ročník** – předvyplněn aktuální (`2026` = ročník 2026/27).
   Pro zúžení seznamu napište část názvu soutěže, např. `2.třída`.
2. **Kategorie** – muži, ženy, U13… (přeskočí se, pokud hledání odpovídá jediné).
3. **Soutěž** – a její **fáze**, pokud jich je víc (např. základní část / play-off).
4. **Družstvo** – vyberte svoje. Hotovo! 🎉

> 💡 **Zkratka:** máte soutěž otevřenou na cz.basketball nebo cbf.cz? Vložte odkaz obsahující `p=…` (nebo jen číslo fáze) do pole *ID fáze nebo URL* a přejdete rovnou k výběru družstva.

Chcete sledovat víc družstev (děti, další týmy klubu)? Stačí integraci přidat znovu.

## 📋 Entity

Příklad pro družstvo *TJ ÚVN*:

| Entita | Příklad stavu | Užitečné atributy |
|---|---|---|
| `calendar.tj_uvn` | `zapnuto` během utkání | všechna utkání ročníku |
| `sensor.tj_uvn_next_game` | `26. 11. 2026 19:40` | `opponent`, `home`, `venue`, `city`, `round`, `head_to_head` |
| `sensor.tj_uvn_next_opponent` | `Sokol Dolní Počernice C` | `home` |
| `sensor.tj_uvn_last_game` | `54:83` *(vaše skóre první)* | `opponent`, `date`, `outcome`, `periods` |
| `sensor.tj_uvn_last_game_outcome` | `Prohra` | |
| `sensor.tj_uvn_table_position` | `7` | `wins`, `losses`, `points_scored`, `points_conceded`, `table` |
| `sensor.tj_uvn_table_points` | `9` | |
| `sensor.tj_uvn_games_remaining` | `15` | |
| `sensor.tj_uvn_streak` | `L2` *(2 prohry v řadě; W = výhry)* | |
| `sensor.tj_uvn_last_update` | čas posledního stažení dat | |

ID entit se odvíjí od názvu vašeho družstva – najdete je na stránce zařízení družstva.

## 🖼️ Nápady na dashboard

**Karta s příštím utkáním a tabulkou**

```yaml
type: entities
title: 🏀 TJ ÚVN
entities:
  - entity: sensor.tj_uvn_next_game
    name: Příští utkání
  - type: attribute
    entity: sensor.tj_uvn_next_game
    attribute: opponent
    name: Soupeř
  - type: attribute
    entity: sensor.tj_uvn_next_game
    attribute: venue
    name: Hala
  - entity: sensor.tj_uvn_last_game
    name: Poslední výsledek
  - entity: sensor.tj_uvn_table_position
    name: Pořadí
  - entity: sensor.tj_uvn_streak
```

**Tabulka soutěže** (karta Markdown)

```yaml
type: markdown
title: Tabulka
content: |
  | # | Družstvo | V | P | Body |
  |---|---|---|---|---|
  {%- for t in state_attr('sensor.tj_uvn_table_position', 'table') or [] %}
  | {{ t.position }} | {{ t.team }} | {{ t.wins }} | {{ t.losses }} | **{{ t.points }}** |
  {%- endfor %}
```

**Rozpis** – přidejte kartu **Kalendář** s entitou `calendar.tj_uvn`.

## 🤖 Nápady na automatizace

**Připomenutí 3 hodiny před utkáním** (vestavěný spouštěč kalendáře):

```yaml
alias: Basketbal – připomenutí utkání
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.tj_uvn
    offset: "-3:00:00"
actions:
  - action: notify.mobile_app_vas_telefon
    data:
      title: 🏀 Dnes se hraje
      message: "{{ trigger.calendar_event.summary }} – {{ trigger.calendar_event.location }}"
mode: single
```

**Upozornění na nový výsledek:**

```yaml
alias: Basketbal – nový výsledek
triggers:
  - trigger: state
    entity_id: sensor.tj_uvn_last_game
conditions:
  - condition: template
    value_template: >
      {{ trigger.from_state.state not in ['unknown', 'unavailable']
         and trigger.to_state.state not in ['unknown', 'unavailable'] }}
actions:
  - action: notify.mobile_app_vas_telefon
    data:
      title: 🏀 Konečný výsledek
      message: >
        {{ state_attr('sensor.tj_uvn_last_game', 'opponent') }}:
        {{ states('sensor.tj_uvn_last_game') }}
        ({{ states('sensor.tj_uvn_last_game_outcome') }})
mode: queued
```

`notify.mobile_app_vas_telefon` nahraďte vlastní akcí pro oznámení.

## 🔄 Nový ročník nebo play-off

Jakmile mají všechna utkání ročníku výsledek, Home Assistant zobrazí **upozornění v Opravách**. Až ČBF zveřejní nový ročník (nebo play-off), otevřete položku integrace, zvolte **Přenastavit** a vyberte novou fázi soutěže. Entity, dashboardy, automatizace i historie zůstanou funkční.

## 🛠️ Možnosti

**Nastavení → Zařízení a služby → CBF Basketball → Konfigurovat**

- **Interval aktualizace** – 1 až 24 hodin (výchozí 3 h). Prosíme, nenastavujte ho zbytečně nízko; server ČBF sdílí všichni.

## ❓ Časté dotazy

**Příští utkání ukazuje `neznámé`, ale datum znám.**
Čas utkání soutěž ještě nepotvrdila (ČBF taková utkání vede s časem `00:00`). Datum je v atributu `date` a v kalendáři je utkání jako celodenní s poznámkou *čas neurčen*.

**V kalendáři chybí odložené utkání.**
Odložená utkání bez nového termínu se nezobrazují, dokud ČBF nový termín nezveřejní.

**Družstvo je v tabulce níž, než by odpovídalo bilanci.**
ČBF řadí podle bodů (2 za výhru, 1 za prohru), takže družstva s menším počtem odehraných utkání mohou být zatím níž.

**Výsledek dnešního utkání tam ještě není.**
Výsledky se objeví po zapsání do systému ČBF – často týž večer, někdy až druhý den – a integrace je načte při další aktualizaci.

**Něco nefunguje.**
Založte [issue](https://github.com/dvejsada/cbf-homeassistant/issues) a přiložte diagnostiku (položka integrace → **⋮** → **Stáhnout diagnostiku**; jména rozhodčích se nezahrnují).

## ℹ️ O datech

Data pocházejí z veřejných [XML exportů ČBF](https://cbf.cz.basketball/xml-exporty/p58). Projekt není spojen s Českou basketbalovou federací ani jí podporován.
