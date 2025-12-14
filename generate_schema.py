import numpy as np
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def count_consecutive_benches(schedule):
    """Tel hoeveel spelers consecutive bench periodes hebben"""
    n_players, n_periods = schedule.shape
    count = 0
    for player in range(n_players):
        for period in range(n_periods - 1):
            if schedule[player, period] == 0 and schedule[player, period + 1] == 0:
                count += 1
                break
    return count

def find_consecutive_benches(schedule, player):
    """Vind alle consecutive bench periodes voor een speler"""
    n_periods = schedule.shape[1]
    consecutive_pairs = []
    for period in range(n_periods - 1):
        if schedule[player, period] == 0 and schedule[player, period + 1] == 0:
            consecutive_pairs.append((period, period + 1))
    return consecutive_pairs

def optimize_schedule(schedule, max_swaps=10000):
    """Optimaliseer schedule door spelers te husselen om consecutive benches te minimaliseren"""
    n_players, n_periods = schedule.shape
    best_schedule = schedule.copy()
    best_consec = count_consecutive_benches(best_schedule)

    improvements = 0
    for swap_attempt in range(max_swaps):
        # Strategie: vind speler met consecutive bench en probeer die op te lossen
        players_with_consec = []
        for p in range(n_players):
            if find_consecutive_benches(schedule, p):
                players_with_consec.append(p)

        if players_with_consec:
            # Kies een speler met consecutive bench
            problem_player = random.choice(players_with_consec)
            consec_pairs = find_consecutive_benches(schedule, problem_player)

            if consec_pairs:
                # Kies een consecutive pair om op te lossen
                period1, period2 = random.choice(consec_pairs)

                # Probeer deze speler in period1 OF period2 te laten spelen
                # door te swappen met iemand die WEL speelt in die periode
                target_period = random.choice([period1, period2])

                # Vind spelers die in target_period spelen
                playing_target = [p for p in range(n_players) if schedule[p, target_period] == 1]

                if playing_target:
                    # Probeer te swappen met een speler die GEEN consecutive bench creëert
                    for swap_player in random.sample(playing_target, min(len(playing_target), 5)):
                        # Vind een periode waar problem_player speelt en swap_player niet
                        swap_periods = [t for t in range(n_periods)
                                      if schedule[problem_player, t] == 1
                                      and schedule[swap_player, t] == 0]

                        if swap_periods:
                            other_period = random.choice(swap_periods)

                            # Maak de swap
                            test_schedule = schedule.copy()
                            test_schedule[problem_player, target_period] = 1
                            test_schedule[problem_player, other_period] = 0
                            test_schedule[swap_player, target_period] = 0
                            test_schedule[swap_player, other_period] = 1

                            # Check of dit beter is (of gelijk maar acceptabel)
                            new_consec = count_consecutive_benches(test_schedule)
                            if new_consec <= best_consec:
                                schedule = test_schedule
                                if new_consec < best_consec:
                                    best_schedule = test_schedule.copy()
                                    best_consec = new_consec
                                    improvements += 1

                                    if best_consec == 0:  # Perfecte oplossing!
                                        return best_schedule
                                break

    return best_schedule

def validate_schedule(schedule, verbose=False):
    """Valideer het wisselschema"""
    n_players = schedule.shape[0]
    n_periods = schedule.shape[1]
    errors = []
    
    # Check 1: Elke periode moet precies 5 spelers hebben
    for period in range(n_periods):
        players_in_field = schedule[:, period].sum()
        if players_in_field != 5:
            errors.append(f"Periode {period}: {players_in_field} spelers (moet 5)")
    
    # Check 2: Controleer speeltijd per speler (9 of 10 periodes)
    for player in range(n_players):
        periods_played = schedule[player, :].sum()
        if periods_played not in [9, 10]:
            errors.append(f"Speler {player+1}: {periods_played} periodes (moet 9 of 10)")
    
    # Check 3: GEEN enkele speler mag 2 opeenvolgende bankperiodes hebben
    players_with_consecutive_bench = 0
    for player in range(n_players):
        has_consecutive = False
        for period in range(n_periods - 1):
            if schedule[player, period] == 0 and schedule[player, period + 1] == 0:
                has_consecutive = True
                break
        if has_consecutive:
            players_with_consecutive_bench += 1

    if players_with_consecutive_bench > 0:
        errors.append(f"{players_with_consecutive_bench} spelers met 2 opeenvolgende bankperiodes (0 toegestaan)")

    if verbose and errors:
        for error in errors:
            print(f"FOUT: {error}")

    return len(errors) == 0

def generate_schedule(n_players=8, n_periods=15, players_on_field=5, max_attempts=10000):
    """Genereer een geldig wisselschema met slimmere selectie"""

    # Bereken totaal aantal speelperiodes
    total_periods_needed = n_periods * players_on_field

    # Verdeel zo eerlijk mogelijk over spelers
    base_periods = total_periods_needed // n_players
    extra_periods = total_periods_needed % n_players

    target_periods = [base_periods + (1 if i < extra_periods else 0) for i in range(n_players)]

    # Track top 3 best schedules
    top_schedules = []  # List of tuples: (consec_count, schedule)

    for attempt in range(max_attempts):
        schedule = np.zeros((n_players, n_periods), dtype=int)
        players_with_consec_bench = set()  # Track welke spelers al consecutive bench hebben gehad

        # Voor elke periode, selecteer slim 5 spelers
        success = True
        failed_period = -1
        for period in range(n_periods):
            # Spelers die nog kunnen spelen (niet over target)
            available = [p for p in range(n_players) if schedule[p, :period+1].sum() < target_periods[p]]

            if len(available) < players_on_field:
                success = False
                failed_period = period
                break

            # Prefer avoiding consecutive bench, maar wees flexibel
            candidates = available

            # Slim selecteren: balanceer tussen nu spelen en ruimte laten voor later
            def get_priority(p):
                played = schedule[p, :period+1].sum()
                needed = target_periods[p] - played
                periods_remaining = n_periods - period

                # Base priority op needed
                priority = needed * 10  # Schaal omhoog voor betere balans

                # Als een speler MOET spelen (niet genoeg periodes over), zeer hoge prioriteit
                if needed >= periods_remaining:
                    priority += 100

                # Sterke voorkeur: vermijd consecutive bench
                if period > 0:
                    if schedule[p, period-1] == 1:
                        priority += 25  # Sterke voorkeur voor spelers die vorige periode speelden
                    elif len(players_with_consec_bench) >= 3:
                        # Al 3 spelers met consecutive bench, penalty tegen nieuwe
                        priority -= 30

                # Als deze speler al consecutive bench heeft gehad, extra voorkeur om te spelen
                if p in players_with_consec_bench:
                    priority += 15

                return priority + random.random() * 5.0

            candidates.sort(key=get_priority, reverse=True)
            selected = candidates[:players_on_field]

            # Vul schema in
            for player in selected:
                schedule[player, period] = 1

            # Update tracking van consecutive bench
            if period > 0:
                for p in range(n_players):
                    if schedule[p, period-1] == 0 and schedule[p, period] == 0:
                        players_with_consec_bench.add(p)

        if success:
            # Alle periodes ingevuld, valideer
            if validate_schedule(schedule, verbose=False):
                return schedule
            else:
                # Tel hoeveel spelers consecutive bench hebben
                consec_count = 0
                for player in range(n_players):
                    for period in range(n_periods - 1):
                        if schedule[player, period] == 0 and schedule[player, period + 1] == 0:
                            consec_count += 1
                            break

                # Bewaar top 3 beste pogingen
                top_schedules.append((consec_count, schedule.copy()))
                top_schedules.sort(key=lambda x: x[0])  # Sort by consec_count
                if len(top_schedules) > 3:
                    top_schedules = top_schedules[:3]  # Keep only top 3

                # Debug disabled voor snelheid
                pass
        else:
            # Debug disabled
            pass

    if top_schedules:
        return top_schedules  # Return list of (count, schedule) tuples
    return None

def print_schedule(schedule, player_names=None):
    """Print het schema in ASCII tabel formaat"""
    n_players, n_periods = schedule.shape

    if player_names is None:
        player_names = [f"Speler {i+1}" for i in range(n_players)]

    # Kolombreedte voor spelersnamen
    name_width = max(len(name) for name in player_names) + 1

    # Header lijn 1: Quarter labels
    quarter_header = " " * name_width
    for i in range(n_periods):
        quarter = (i // 4) + 1
        quarter_header += f"  Q{quarter}  "
    quarter_header += " Totaal Periodes"
    print(quarter_header)

    # Header lijn 2: periode tijden binnen elk kwart
    header = " " * name_width
    for i in range(n_periods):
        # Tijd binnen het kwart (reset elke 15 minuten)
        time_in_quarter = (i % 4) * 4
        end_time_in_quarter = min(time_in_quarter + 4, 15)
        header += f" {time_in_quarter:2d}-{end_time_in_quarter:2d}"
    header += "               "
    print(header)

    # Separator
    print("-" * len(quarter_header))

    # Rijen per speler
    for i, name in enumerate(player_names):
        row = schedule[i, :]
        total_minutes = row.sum() * 4
        total_periods = row.sum()
        row_str = f"{name:<{name_width}}"
        for val in row:
            row_str += f"   {int(val)} "
        row_str += f"    {int(total_minutes):2d}      {int(total_periods):2d}"
        print(row_str)

    # Separator
    print("-" * len(header))

    # Totaal lijn (spelers per periode)
    totals = " " * name_width
    for period in range(n_periods):
        count = schedule[:, period].sum()
        totals += f"   {int(count)} "
    print(totals)

def print_validation_summary(schedule):
    """Print een validatie samenvatting"""
    n_players, n_periods = schedule.shape
    
    print("\n--- Validatie Samenvatting ---")
    
    # Check per periode
    print("Spelers per periode:")
    for period in range(n_periods):
        count = schedule[:, period].sum()
        status = "✓" if count == 5 else "✗"
        print(f"  {period*4}-{(period+1)*4} min: {count} spelers {status}")
    
    # Check per speler
    print("\nSpeeltijd per speler:")
    for player in range(n_players):
        periods = schedule[player, :].sum()
        minutes = periods * 4
        status = "✓" if periods in [9, 10] else "✗"
        print(f"  Speler {player+1}: {periods} periodes ({minutes} min) {status}")
    
    # Check opeenvolgende bankperiodes
    print("\nOpeenvolgende bankperiodes:")
    players_with_consecutive = []
    for player in range(n_players):
        consecutive_count = 0
        for period in range(n_periods - 1):
            if schedule[player, period] == 0 and schedule[player, period + 1] == 0:
                consecutive_count += 1
        if consecutive_count > 0:
            players_with_consecutive.append(player + 1)
            print(f"  Speler {player+1}: {consecutive_count}x twee periodes achter elkaar")

    if len(players_with_consecutive) == 0:
        print("  Geen opeenvolgende bankperiodes ✓✓✓ PERFECT!")
    else:
        print(f"  {len(players_with_consecutive)} spelers met opeenvolgende bankperiodes (0 toegestaan) ✗")

# Genereer basis schema (zonder consecutive bench constraint)
result = generate_schedule(n_players=8, n_periods=15, players_on_field=5, max_attempts=5000)

# Als we een geldig schema hebben, optimaliseer het
if result is not None and isinstance(result, list):
    optimized_schedules = []

    # Zoek naar perfecte oplossing
    perfect_schedule = None
    for i, (consec_count, schedule) in enumerate(result[:3], 1):
        optimized = optimize_schedule(schedule, max_swaps=200000)
        new_count = count_consecutive_benches(optimized)

        if new_count == 0:
            perfect_schedule = (new_count, optimized)
            break
        else:
            optimized_schedules.append((new_count, optimized))

    # Als we een perfecte oplossing hebben, gebruik die
    if perfect_schedule:
        result = [perfect_schedule]
    elif optimized_schedules:
        # Anders, sorteer en neem de beste
        optimized_schedules.sort(key=lambda x: x[0])
        result = [optimized_schedules[0]]  # Alleen de beste
    else:
        result = None

if result is not None:
    # Load player names from environment variables
    player_names = [
        os.getenv('PLAYER_1', 'Player 1'),
        os.getenv('PLAYER_2', 'Player 2'),
        os.getenv('PLAYER_3', 'Player 3'),
        os.getenv('PLAYER_4', 'Player 4'),
        os.getenv('PLAYER_5', 'Player 5'),
        os.getenv('PLAYER_6', 'Player 6'),
        os.getenv('PLAYER_7', 'Player 7'),
        os.getenv('PLAYER_8', 'Player 8'),
    ]

    # Print de beste oplossing
    if isinstance(result, list) and len(result) > 0:
        consec_count, schedule = result[0]
        print_schedule(schedule, player_names)
    else:
        # Single valid schedule (direct gevonden, niet geoptimaliseerd)
        print_schedule(result, player_names)