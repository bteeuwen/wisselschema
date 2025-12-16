import numpy as np
import random
import os
import argparse
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

def validate_schedule(schedule, verbose=False, periods_per_section=3):
    """Valideer het wisselschema"""
    n_players = schedule.shape[0]
    n_periods = schedule.shape[1]
    errors = []

    # Check 1: Elke periode moet precies 4 spelers hebben (voor 4-spelers-wissel variant)
    for period in range(n_periods):
        players_in_field = schedule[:, period].sum()
        if players_in_field != 4:
            errors.append(f"Periode {period}: {players_in_field} spelers (moet 4)")

    # Check 2: Controleer speeltijd per speler (7 of 8 periodes voor 4-spelers-wissel)
    for player in range(n_players):
        periods_played = schedule[player, :].sum()
        if periods_played not in [7, 8]:
            errors.append(f"Speler {player+1}: {periods_played} periodes (moet 7 of 8)")

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

    # Check 4: Per sectie moet er minimaal 1 speler zijn die alle periodes speelt
    n_sections = n_periods // periods_per_section
    for section in range(n_sections):
        start_period = section * periods_per_section
        end_period = start_period + periods_per_section

        # Tel hoeveel spelers alle periodes in deze sectie spelen
        players_full_section = 0
        for player in range(n_players):
            if schedule[player, start_period:end_period].sum() == periods_per_section:
                players_full_section += 1

        if players_full_section < 1:
            errors.append(f"Sectie {section+1}: geen speler speelt alle {periods_per_section} periodes (minimaal 1 vereist)")

    if verbose and errors:
        for error in errors:
            print(f"FOUT: {error}")

    return len(errors) == 0

def generate_schedule(n_players=8, n_periods=15, players_on_field=5, max_attempts=10000, periods_per_section=3):
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
            if validate_schedule(schedule, verbose=False, periods_per_section=periods_per_section):
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

def print_schedule(schedule, player_names=None, period_duration=5, n_sections=4, minutes_per_section=15, keeper=None):
    """Print het schema in ASCII tabel formaat"""
    n_players, n_periods = schedule.shape

    if player_names is None:
        player_names = [f"Speler {i+1}" for i in range(n_players)]

    # Mark keeper in player names
    display_names = []
    for i, name in enumerate(player_names):
        if keeper is not None and i == keeper - 1:  # keeper is 1-based
            display_names.append(f"{name} (K)")
        else:
            display_names.append(name)

    # Kolombreedte voor spelersnamen
    name_width = max(len(name) for name in display_names) + 1

    # Bereken periodes per sectie
    periods_per_section = minutes_per_section // period_duration

    # Header lijn 1: Section labels
    section_header = " " * name_width
    for i in range(n_periods):
        section = (i // periods_per_section) + 1
        section_header += f"  S{section}  "
        # Add separator after each section (except the last period)
        if (i + 1) % periods_per_section == 0 and i < n_periods - 1:
            section_header += " | "
    section_header += " | Totaal Periodes"
    print(section_header)

    # Header lijn 2: periode tijden binnen elke sectie
    header = " " * name_width
    for i in range(n_periods):
        # Tijd binnen de sectie (reset elke minutes_per_section minuten)
        time_in_section = (i % periods_per_section) * period_duration
        end_time_in_section = min(time_in_section + period_duration, minutes_per_section)
        header += f" {time_in_section:2d}-{end_time_in_section:2d}"
        # Add separator after each section (except the last period)
        if (i + 1) % periods_per_section == 0 and i < n_periods - 1:
            header += " | "
    header += " |               "
    print(header)

    # Separator
    print("-" * len(section_header))

    # Rijen per speler
    for i, name in enumerate(display_names):
        row = schedule[i, :]
        total_minutes = row.sum() * period_duration
        total_periods = row.sum()
        row_str = f"{name:<{name_width}}"
        for j, val in enumerate(row):
            row_str += f"   {int(val)} "
            # Add separator after each section (except the last period)
            if (j + 1) % periods_per_section == 0 and j < n_periods - 1:
                row_str += " | "
        row_str += f" |  {int(total_minutes):2d}      {int(total_periods):2d}"
        print(row_str)

    # Separator
    print("-" * len(header))

    # Totaal lijn (spelers per periode)
    totals = " " * name_width
    for period in range(n_periods):
        count = schedule[:, period].sum()
        totals += f"   {int(count)} "
        # Add separator after each section (except the last period)
        if (period + 1) % periods_per_section == 0 and period < n_periods - 1:
            totals += " | "
    totals += " |"
    print(totals)

def print_section_analysis(schedule, player_names, periods_per_section=3):
    """Print analyse van spelers die volledige secties spelen"""
    n_players, n_periods = schedule.shape
    n_sections = n_periods // periods_per_section

    print("\nSpelers die alle periodes per sectie spelen:")
    for section in range(n_sections):
        start_period = section * periods_per_section
        end_period = start_period + periods_per_section

        full_section_players = []
        for player in range(n_players):
            if schedule[player, start_period:end_period].sum() == periods_per_section:
                # Extract just the name without the number prefix
                player_name = player_names[player]
                if '. ' in player_name:
                    player_name = player_name.split('. ', 1)[1]
                full_section_players.append(player_name)

        if full_section_players:
            print(f"  Sectie {section+1}: {', '.join(full_section_players)}")
        else:
            print(f"  Sectie {section+1}: GEEN ✗")

def print_validation_summary(schedule, period_duration=5):
    """Print een validatie samenvatting"""
    n_players, n_periods = schedule.shape

    print("\n--- Validatie Samenvatting ---")

    # Check per periode
    print("Spelers per periode:")
    for period in range(n_periods):
        count = schedule[:, period].sum()
        status = "✓" if count == 4 else "✗"
        print(f"  {period*period_duration}-{(period+1)*period_duration} min: {count} spelers {status}")

    # Check per speler
    print("\nSpeeltijd per speler:")
    for player in range(n_players):
        periods = schedule[player, :].sum()
        minutes = periods * period_duration
        status = "✓" if periods in [7, 8] else "✗"
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

def main():
    """Main function met argument parsing"""
    parser = argparse.ArgumentParser(
        description='Genereer een wisselschema voor een sportteam',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--sections',
        type=int,
        default=4,
        help='Aantal speelsecties (bijv. kwarten)'
    )

    parser.add_argument(
        '--minutes-per-section',
        type=int,
        default=15,
        help='Minuten per sectie'
    )

    parser.add_argument(
        '--period-duration',
        type=int,
        default=5,
        help='Duur van wisselperiode in minuten'
    )

    parser.add_argument(
        '--players',
        type=int,
        default=9,
        help='Aantal spelers in het team'
    )

    parser.add_argument(
        '--players-on-field',
        type=int,
        default=4,
        help='Aantal spelers op het veld tegelijk (4 voor 4-spelers-wissel variant)'
    )

    parser.add_argument(
        '--keeper',
        type=int,
        default=5,
        help='Speler nummer die keeper is (1-based index)'
    )

    args = parser.parse_args()

    # Bereken aantal periodes gebaseerd op de parameters
    n_periods = (args.sections * args.minutes_per_section) // args.period_duration
    periods_per_section = args.minutes_per_section // args.period_duration

    print(f"Genereren van wisselschema met volgende parameters:")
    print(f"  - Aantal secties: {args.sections}")
    print(f"  - Minuten per sectie: {args.minutes_per_section}")
    print(f"  - Duur wisselperiode: {args.period_duration} minuten")
    print(f"  - Aantal periodes: {n_periods}")
    print(f"  - Periodes per sectie: {periods_per_section}")
    print(f"  - Aantal spelers: {args.players}")
    print(f"  - Veldspelers (excl. keeper): {args.players_on_field}")
    print(f"  - Keeper: speler {args.keeper} (altijd op veld)")
    print(f"  - Totaal op veld: {args.players_on_field + 1} ({args.players_on_field} veldspelers + 1 keeper)")
    print()

    # Genereer basis schema (zonder consecutive bench constraint)
    # Keeper is altijd op veld, dus we schedulen alleen de andere spelers
    # We hebben args.players_on_field veldspelers NAAST de keeper
    result = generate_schedule(
        n_players=args.players - 1,  # Exclude keeper from rotation
        n_periods=n_periods,
        players_on_field=args.players_on_field,  # Keep full field count (keeper is separate)
        max_attempts=5000,
        periods_per_section=periods_per_section
    )

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
        # Load player names from environment variables (excluding keeper)
        all_player_names = []
        for i in range(args.players):
            all_player_names.append(os.getenv(f'PLAYER_{i+1}', f'Player {i+1}'))

        # Check for absent players (players defined in env but not in args.players)
        absent_players = []
        i = args.players + 1
        while True:
            player_name = os.getenv(f'PLAYER_{i}')
            if player_name is None:
                break
            absent_players.append(f"{player_name} (speler {i})")
            i += 1

        # Get keeper name and create list without keeper, with numbering
        keeper_name = all_player_names[args.keeper - 1]
        keeper_number = args.keeper

        # Create numbered player names list (excluding keeper)
        player_names = []
        player_numbers = []
        for i, name in enumerate(all_player_names):
            if i != args.keeper - 1:
                player_number = i + 1
                player_names.append(f"{player_number}. {name}")
                player_numbers.append(player_number)

        # Print de beste oplossing
        if isinstance(result, list) and len(result) > 0:
            consec_count, schedule = result[0]
            print_schedule(
                schedule,
                player_names,
                period_duration=args.period_duration,
                n_sections=args.sections,
                minutes_per_section=args.minutes_per_section,
                keeper=None  # Don't mark keeper in schedule since they're not in it
            )
            # Print section analysis
            print_section_analysis(schedule, player_names, periods_per_section=periods_per_section)
        else:
            # Single valid schedule (direct gevonden, niet geoptimaliseerd)
            print_schedule(
                result,
                player_names,
                period_duration=args.period_duration,
                n_sections=args.sections,
                minutes_per_section=args.minutes_per_section,
                keeper=None  # Don't mark keeper in schedule since they're not in it
            )
            # Print section analysis
            print_section_analysis(result, player_names, periods_per_section=periods_per_section)

        # Print keeper info
        total_minutes = n_periods * args.period_duration
        print()
        print(f"Keeper: {keeper_number}. {keeper_name} - Altijd op veld ({total_minutes} minuten, {n_periods} periodes)")

        # Print absent players if any
        if absent_players:
            print()
            print("Afwezig:")
            for absent in absent_players:
                print(f"  - {absent}")
    else:
        print("Kon geen geldig schema genereren. Probeer het opnieuw of pas de parameters aan.")

if __name__ == '__main__':
    main()