# 🏀 CBF Basketball pro Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4.svg)](https://www.home-assistant.io/)

**Už nezmeškáte žádné utkání.** Sledujte své družstvo z libovolné soutěže České basketbalové federace (ČBF) – od nejvyšší ligy až po místní *3. třídu* – přímo v Home Assistantu.

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

**Potřebujete:** Home Assistant **2026.10 nebo novější** s komunitním obchodem – od verze 2026.11 se jmenuje **Marketplace** (*Nastavení → Marketplace*), ve starších verzích **HACS**.

### Přes Marketplace / HACS (doporučeno)

[![Otevřít tento repozitář v HACS ve vašem Home Assistantu.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dvejsada&repository=cbf-homeassistant&category=integration)

Nebo krok za krokem:

1. Otevřete **Marketplace** (nebo **HACS**) → menu **⋮** → **Vlastní repozitáře**.
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

> 💡 **Zkratka:** máte-li odkaz na rozpis své soutěže na webu ČBF obsahující `p=…` (např. `…?p=10469`), vložte ho – nebo jen samotné číslo – do pole *ID fáze nebo URL* a přejdete rovnou k výběru družstva.

Chcete sledovat víc družstev (děti, další týmy klubu)? Stačí integraci přidat znovu.

## 📋 Entity

Příklad pro družstvo *TJ ÚVN* v Home Assistantu nastaveném **česky**:

| Entita | Příklad stavu | Užitečné atributy |
|---|---|---|
| `calendar.tj_uvn` | `zapnuto` během utkání | všechna utkání ročníku |
| `sensor.tj_uvn_pristi_utkani` | datum a čas začátku | `date`, `opponent`, `home`, `venue`, `city`, `round`, `head_to_head` |
| `sensor.tj_uvn_pristi_souper` | `Sokol Dolní Počernice C` | `home` |
| `sensor.tj_uvn_posledni_utkani` | `54:83` *(vaše skóre první)* | `opponent`, `date`, `outcome`, `periods` |
| `sensor.tj_uvn_vysledek_posledniho_utkani` | `Prohra` | |
| `sensor.tj_uvn_poradi_v_tabulce` | `7` | `wins`, `losses`, `points_scored`, `points_conceded`, `table` |
| `sensor.tj_uvn_body_v_tabulce` | `9` | |
| `sensor.tj_uvn_zbyvajici_utkani` | `15` | |
| `sensor.tj_uvn_serie` | `L2` *(2 prohry v řadě; W = výhry)* | |
| `sensor.tj_uvn_posledni_aktualizace` | čas posledního stažení dat | |

⚠️ ID entit se odvíjejí od **názvu družstva** a **jazyka Home Assistantu** – v anglicky nastaveném systému jsou anglická (např. `sensor.tj_uvn_next_game`). Svá ID najdete na stránce zařízení družstva; podle nich upravte příklady níže.

## 🖼️ Nápady na dashboard

Přidáte je přes **Dashboard → Upravit → Přidat kartu → Ruční**.

**Karta s příštím utkáním a tabulkou**

```yaml
type: entities
title: 🏀 TJ ÚVN
entities:
  - entity: sensor.tj_uvn_pristi_utkani
    name: Příští utkání
    format: datetime
  - type: attribute
    entity: sensor.tj_uvn_pristi_utkani
    attribute: opponent
    name: Soupeř
  - type: attribute
    entity: sensor.tj_uvn_pristi_utkani
    attribute: venue
    name: Hala
  - entity: sensor.tj_uvn_posledni_utkani
    name: Poslední výsledek
  - entity: sensor.tj_uvn_poradi_v_tabulce
    name: Pořadí
  - entity: sensor.tj_uvn_serie
```

**Tabulka soutěže** (karta Markdown)

```yaml
type: markdown
title: Tabulka
content: |
  | # | Družstvo | V | P | Body |
  |---|---|---|---|---|
  {%- for t in state_attr('sensor.tj_uvn_poradi_v_tabulce', 'table') or [] %}
  | {{ t.position }} | {{ t.team }} | {{ t.wins }} | {{ t.losses }} | **{{ t.points }}** |
  {%- endfor %}
```

**Rozpis** – přidejte kartu **Kalendář** s entitou `calendar.tj_uvn`.

## 🤖 Nápady na automatizace

Vytvoříte je přes **Nastavení → Automatizace a scény → Vytvořit automatizaci → ⋮ → Upravit v YAML**. `notify.mobile_app_vas_telefon` nahraďte vlastní akcí pro oznámení.

**Připomenutí 3 hodiny před utkáním** (vestavěný spouštěč kalendáře):

```yaml
alias: Basketbal – připomenutí utkání
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.tj_uvn
    offset: "-3:00:00"
conditions:
  # přeskočí utkání bez potvrzeného času (celodenní události)
  - condition: template
    value_template: "{{ not trigger.calendar_event.all_day }}"
actions:
  - action: notify.mobile_app_vas_telefon
    data:
      title: 🏀 Dnes se hraje
      message: >
        {{ trigger.calendar_event.summary }}
        {{ trigger.calendar_event.location or '' }}
mode: single
```

**Upozornění na nový výsledek:**

```yaml
alias: Basketbal – nový výsledek
triggers:
  - trigger: state
    entity_id: sensor.tj_uvn_posledni_utkani
    not_from: [unknown, unavailable]
    not_to: [unknown, unavailable]
actions:
  - action: notify.mobile_app_vas_telefon
    data:
      title: 🏀 Konečný výsledek
      message: >
        {{ trigger.to_state.attributes.opponent }}:
        {{ trigger.to_state.state }}
        {{ iif(trigger.to_state.attributes.outcome == 'win', '🏆 Výhra!', '(prohra)') }}
mode: queued
```

## 🔄 Nový ročník nebo play-off

Jakmile mají všechna utkání ročníku výsledek, Home Assistant zobrazí upozornění v **Nastavení → Opravy**. Až ČBF zveřejní nový ročník (nebo play-off), otevřete **Nastavení → Zařízení a služby → CBF Basketball**, v menu **⋮** položky zvolte **Přenastavit** a vyberte novou fázi soutěže. Entity, dashboardy, automatizace i historie zůstanou funkční.

## 🛠️ Možnosti

**Nastavení → Zařízení a služby → CBF Basketball → Konfigurovat**

- **Interval aktualizace** – 1 až 24 hodin (výchozí 3 h). Prosíme, nenastavujte ho zbytečně nízko; server ČBF sdílí všichni.

## ❓ Časté dotazy

**Příští utkání ukazuje „Neznámý“, i když je utkání v rozpisu.**
Soutěž ještě nepotvrdila čas utkání (ČBF taková utkání vede s časem `00:00`). Datum je v atributu `date` senzoru a v kalendáři je utkání jako celodenní s poznámkou *čas neurčen* (kalendář je proto celý ten den `zapnuto`).

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
