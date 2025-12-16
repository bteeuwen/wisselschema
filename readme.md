# Wisselschema Generator

Generator voor wisselschema's voor sportteams.

## Parameters

Het script ondersteunt de volgende configureerbare parameters:

- `--sections` - Aantal speelsecties (bijv. kwarten) (standaard: 4)
- `--minutes-per-section` - Minuten per sectie (standaard: 15)
- `--period-duration` - Duur van wisselperiode in minuten (standaard: 5)
- `--players` - Aantal spelers in het team (standaard: 9)
- `--players-on-field` - Aantal spelers op het veld tegelijk (standaard: 5)
- `--keeper` - Speler nummer die keeper is, 1-based index (standaard: 5)

## Gebruik

### Standaard parameters
```bash
python generate_schema.py
```

### Met aangepaste parameters
```bash
python generate_schema.py --sections 4 --minutes-per-section 15 --period-duration 5
```

### Met aangepaste keeper en aantal spelers
```bash
python generate_schema.py --players 8 --keeper 3
```

### Help tonen
```bash
python generate_schema.py --help
```

## Spelersnamen

Spelersnamen kunnen worden ingesteld via environment variabelen in het `.env` bestand:
- PLAYER_1=Naam1
- PLAYER_2=Naam2
- etc.