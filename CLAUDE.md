# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Wisselschema** is a hockey team substitution schedule generator. It has two components:
1. A CLI tool (`generate_schema.py`) for quick schedule generation
2. A Django web application for managing and visualizing schedules

The domain is Dutch hockey: "wisselschema" = substitution schedule, "spelers" = players, "keeper" = goalkeeper.

## Commands

### CLI Tool
```bash
./run.sh  # Default: Team D1, Keeper Casper, Absent Chester, 4 sections

python generate_schema.py --team D1 --keeper Casper --absent "Chester,Faber" --sections 5
```

CLI parameters: `--team`, `--keeper`, `--absent`, `--sections` (default 4), `--minutes-per-section` (default 15), `--period-duration` (default 5), `--players-on-field` (default 5).

### Django Web App
```bash
python manage.py runserver       # Start dev server at http://localhost:8000
python manage.py migrate         # Initialize/migrate database (SQLite at db.sqlite3)
```

### Tests
```bash
python test_block_sizing.py
python test_custom_blocks.py
python test_full_feature.py
python test_web_form.py
python test_scheduler_approaches.py
python test_difficult_scenario.py
```

### Dependencies
```bash
pip install -r requirements.txt  # numpy, python-dotenv
pip install django                # Not in requirements.txt but required for web app
```

### Configuration
Team rosters are defined in `.env`:
```
TEAM_D1=Faber,Sep,Mats,Jurre,Casper,Juliaan,Thije,Noah,Flo,Chester
```

## Architecture

### CLI Tool (`generate_schema.py`)
Standalone script with the full scheduling algorithm. Key functions:
- `generate_schedule()` — core algorithm: iterative random selection with fairness constraints
- `optimize_schedule()` — post-generation optimizer using random swapping
- `validate_schedule()` — enforces the 4-spelers-wissel rules
- `print_schedule()` — formatted output

### Django App Structure
```
HockeySub/          — Django project settings, urls, wsgi, asgi
hockeysub/          — Main Django app
  models.py         — Game, Schedule, Player, TimeBlock
  views.py          — CRUD + schedule generation/viewing
  forms.py          — GameConfigForm with validation
  scheduler.py      — ScheduleOptimizer class (main optimization engine, ~53KB)
  urls.py           — 8 URL patterns
  templates/        — 8 HTML templates
  static/           — CSS, JS, images
```

### Scheduling Algorithm (the "4-spelers-wissel" variant)
- Keeper always plays; 5 outfield players on field per period
- Between periods: exactly 1 player stays on field, 4 rotate off, 4 rotate on
- Fairness constraints: no player sits bench for 2 consecutive periods; all players get balanced play time (9-10 periods each for a 10-player team)
- `ScheduleOptimizer` in `hockeysub/scheduler.py` implements the full optimization with fairness metrics and supports custom block durations

### Data Flow (Web App)
1. User creates a `Game` via `GameConfigForm`
2. `/generate/` view calls `ScheduleOptimizer` from `scheduler.py`
3. Result stored as `Schedule` + `Player` stats + `TimeBlock` records in SQLite
4. Multiple schedule versions can be generated and compared; one is "active"
