# Wisselschema Generator

Genereer eerlijke wisselschema's voor sportteams met automatische rotatie van spelers.

## Features

- **Team-based configuratie**: Definieer teams in `.env` file
- **Flexibele selectie**: Kies keeper en afwezige spelers by-name
- **Eerlijke verdeling**: Automatisch berekende speeltijd verdeling
- **4-spelers-wissel constraint**: Optionele validatie dat precies 4 spelers per wissel veranderen
- **Multiple scenarios**: Launch configurations voor verschillende situaties

## Setup

1. Installeer dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configureer je team in `.env`:
   ```bash
   # Team rosters - format: TEAM_<name>=player1,player2,player3,...
   TEAM_D1=Faber,Sep,Mats,Jurre,Casper,Juliaan,Thije,Noah,Flo,Chester
   ```

## Gebruik

### Quick Start (met defaults)

```bash
./run.sh
```

### Met custom parameters

```bash
python generate_schema.py --team D1 --keeper Casper --absent "Chester"
```

### Alle parameters

```bash
python generate_schema.py \
  --team D1 \
  --keeper Casper \
  --absent "Chester,Faber" \
  --sections 5 \
  --minutes-per-section 15 \
  --period-duration 5 \
  --players-on-field 5
```

## Parameters

| Parameter | Vereist | Default | Beschrijving |
|-----------|---------|---------|--------------|
| `--team` | Ja | - | Team naam (bijv. D1) - gebruikt TEAM_<naam> uit .env |
| `--keeper` | Ja | - | Naam van de keeper (altijd op veld) |
| `--absent` | Nee | "" | Comma-separated lijst van afwezige spelers |
| `--sections` | Nee | 4 | Aantal speelsecties (bijv. kwarten) |
| `--minutes-per-section` | Nee | 15 | Minuten per sectie |
| `--period-duration` | Nee | 5 | Duur van wisselperiode in minuten |
| `--players-on-field` | Nee | 5 | Aantal spelers op veld (excl. keeper) |

## Voorbeelden

### Scenario 1: Chester afwezig, 4 kwarten
```bash
python generate_schema.py --team D1 --keeper Casper --absent Chester
```

### Scenario 2: Iedereen aanwezig, 5 secties (75 min)
```bash
python generate_schema.py --team D1 --keeper Casper --sections 5
```

### Scenario 3: Meerdere afwezigen
```bash
python generate_schema.py --team D1 --keeper Casper --absent "Chester,Faber,Sep"
```

## Output

Het script genereert een schema met:
- Overzicht van speeltijd per speler per periode
- Totale speeltijd in minuten en periodes
- Analyse van spelers die hele secties spelen
- Keeper info (altijd op veld)
- Lijst van afwezige spelers

### Voorbeeld Output
```
             S1    S1    S1   |   S2    S2    S2   | ...
             0- 5  5-10 10-15 |   0- 5  5-10 10-15 | ...
-----------------------------------------------------------
1. Faber      0    1    0  |    1    1    1  | ...  | 40min  8
2. Sep        1    1    0  |    1    0    1  | ...  | 40min  8
...

Keeper: Casper - Altijd op veld (60 minuten, 12 periodes)
Afwezig: Chester
```

## VSCode Launch Configurations

Het project bevat pre-configured launch configurations:
1. **D1 (Casper keeper, Chester absent)** - Default scenario
2. **D1 (everyone present)** - Volledige team
3. **D1 (5 sections, 15 periods)** - Langere wedstrijd

## Technische Details

- **Validatie**: Controleert dat schema eerlijk is en geen speler 2x achter elkaar op de bank zit
- **Optimalisatie**: Gebruikt iteratieve optimalisatie om beste verdeling te vinden
- **4-spelers-wissel**: Optionele constraint dat precies 1 speler blijft staan, 4 wisselen

## Meerdere Teams

Je kunt meerdere teams definiëren in `.env`:

```bash
TEAM_D1=Faber,Sep,Mats,Jurre,Casper,Juliaan,Thije,Noah,Flo,Chester
TEAM_D2=Alice,Bob,Charlie,Dave,Emma,Frank,Grace,Henry,Iris,Jack
```

Gebruik dan `--team D2` voor het tweede team.
