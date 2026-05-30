#!/usr/bin/env python3

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append('/mnt/shared_data/dev/wisselschema')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HockeySub.settings')
django.setup()

import random
from typing import List, Dict

def analyze_manual_schedule():
    """Analyze the manually created schedule pattern"""

    # Your manual schedule data
    schedule_blocks = [
        {"start": 0, "end": 3.5, "active": [1, 2, 5, 6, 7], "bench": [3, 4]},
        {"start": 3.5, "end": 7, "active": [3, 4, 5, 6, 7], "bench": [1, 2]},
        {"start": 7, "end": 10.5, "active": [1, 2, 3, 6, 7], "bench": [4, 5]},
        {"start": 10.5, "end": 14, "active": [1, 2, 3, 4, 5], "bench": [6, 7]},
        {"start": 14, "end": 17.5, "active": [1, 3, 4, 5, 6], "bench": [2, 7]},
        {"start": 17.5, "end": 21, "active": [2, 4, 5, 6, 7], "bench": [1, 3]},
        {"start": 21, "end": 24.5, "active": [1, 2, 3, 4, 7], "bench": [5, 6]},
        {"start": 24.5, "end": 25, "active": [1, 2, 3, 4, 5, 6, 7], "bench": []},  # Everyone plays final 0.5min
    ]

    print("ANALYSIS OF MANUAL SCHEDULE")
    print("="*60)

    # Calculate playing time for each player
    playing_times = [0] * 7
    bench_blocks = [0] * 7

    for block in schedule_blocks:
        duration = block["end"] - block["start"]
        for player in block["active"]:
            playing_times[player-1] += duration
        for player in block["bench"]:
            bench_blocks[player-1] += 1

    print("Player Analysis:")
    for i in range(7):
        print(f"Player {i+1}: {playing_times[i]:.1f}min playing, {bench_blocks[i]} bench blocks")

    print(f"\nPlaying time range: {min(playing_times):.1f} - {max(playing_times):.1f}min")
    print(f"Difference: {max(playing_times) - min(playing_times):.1f}min")
    print(f"Bench blocks range: {min(bench_blocks)} - {max(bench_blocks)}")

    # Analyze the pattern
    print(f"\nPATTERN ANALYSIS:")
    print(f"- Block durations: {[block['end'] - block['start'] for block in schedule_blocks]}")
    print(f"- Regular blocks: 3.5min each")
    print(f"- Final buffer: 0.5min with everyone playing")
    print(f"- Total section time: 25min")

    # Check rotation pattern
    print(f"\nROTATION PATTERN:")
    for i, block in enumerate(schedule_blocks):
        if i < len(schedule_blocks) - 1:  # Skip the final buffer block
            bench_players = sorted(block["bench"])
            print(f"Block {i+1}: Players {bench_players} on bench")

    return playing_times, bench_blocks

class PatternBasedScheduler:
    def __init__(self, num_players, players_in_field, section_length):
        self.num_players = num_players
        self.players_in_field = players_in_field
        self.bench_players = num_players - players_in_field
        self.section_length = section_length

    def generate_rotation_cycle(self):
        """Generate a complete rotation cycle where every combination of bench players is used"""
        from itertools import combinations

        # Generate all possible combinations of bench players
        players = list(range(1, self.num_players + 1))
        bench_combinations = list(combinations(players, self.bench_players))

        print(f"Generated {len(bench_combinations)} bench combinations:")
        for i, combo in enumerate(bench_combinations):
            print(f"  {i+1}: Players {list(combo)} on bench")

        return bench_combinations

    def create_optimized_block_durations(self, num_blocks):
        """Create block durations with shorter regular blocks and a buffer"""
        buffer_time = 0.5  # Final buffer where everyone plays
        regular_time = self.section_length - buffer_time
        regular_block_duration = regular_time / (num_blocks - 1)

        durations = [regular_block_duration] * (num_blocks - 1) + [buffer_time]
        return durations

    def generate_section_schedule(self, randomize_order=False):
        """Generate a schedule for one section"""
        bench_combinations = self.generate_rotation_cycle()

        if randomize_order:
            bench_combinations = bench_combinations.copy()
            random.shuffle(bench_combinations)
            print(f"\nRandomized bench order:")
            for i, combo in enumerate(bench_combinations):
                print(f"  {i+1}: Players {list(combo)} on bench")

        # Use all combinations, or repeat if we need more blocks
        num_needed = len(bench_combinations)
        durations = self.create_optimized_block_durations(num_needed + 1)  # +1 for buffer

        schedule_blocks = []
        current_time = 0

        # Regular rotation blocks
        for i, bench_combo in enumerate(bench_combinations):
            duration = durations[i]
            active_players = [p for p in range(1, self.num_players + 1) if p not in bench_combo]

            schedule_blocks.append({
                "start": current_time,
                "end": current_time + duration,
                "active": active_players,
                "bench": list(bench_combo),
                "duration": duration
            })
            current_time += duration

        # Final buffer block - everyone plays
        if current_time < self.section_length:
            buffer_duration = self.section_length - current_time
            schedule_blocks.append({
                "start": current_time,
                "end": self.section_length,
                "active": list(range(1, self.num_players + 1)),
                "bench": [],
                "duration": buffer_duration
            })

        return schedule_blocks

    def generate_full_game_schedule(self, sections=2):
        """Generate schedule for full game with randomized second section"""
        full_schedule = []

        print(f"\nGENERATING SECTION 1 (Standard order)")
        section1 = self.generate_section_schedule(randomize_order=False)

        print(f"\nGENERATING SECTION 2 (Randomized order)")
        section2 = self.generate_section_schedule(randomize_order=True)

        # Adjust section 2 start times
        for block in section2:
            block["start"] += self.section_length
            block["end"] += self.section_length

        full_schedule = section1 + section2
        return full_schedule

    def analyze_schedule(self, schedule):
        """Analyze the generated schedule for fairness"""
        playing_times = [0] * self.num_players
        bench_blocks = [0] * self.num_players

        for block in schedule:
            for player in block["active"]:
                playing_times[player-1] += block["duration"]
            for player in block["bench"]:
                bench_blocks[player-1] += 1

        print(f"\nSCHEDULE ANALYSIS:")
        for i in range(self.num_players):
            print(f"Player {i+1}: {playing_times[i]:.1f}min playing, {bench_blocks[i]} bench blocks")

        print(f"\nPlaying time range: {min(playing_times):.1f} - {max(playing_times):.1f}min")
        print(f"Difference: {max(playing_times) - min(playing_times):.1f}min")
        print(f"Bench blocks range: {min(bench_blocks)} - {max(bench_blocks)}")

        return playing_times, bench_blocks

    def print_schedule(self, schedule):
        """Print schedule in a readable format"""
        print(f"\nSCHEDULE OUTPUT:")
        print(f"{'Time':<12} {'Active Players':<20} {'Bench Players':<15} {'Duration':<8}")
        print("-" * 60)

        for block in schedule:
            active_str = ', '.join(map(str, block["active"]))
            bench_str = ', '.join(map(str, block["bench"])) if block["bench"] else "None"
            time_str = f"{block['start']:.1f}-{block['end']:.1f}"
            print(f"{time_str:<12} {active_str:<20} {bench_str:<15} {block['duration']:.1f}min")

def test_generalized_approach():
    """Test the generalized pattern-based approach"""

    print("TESTING GENERALIZED PATTERN-BASED SCHEDULER")
    print("="*60)

    # Test with the same parameters as your example
    scheduler = PatternBasedScheduler(
        num_players=7,
        players_in_field=5,
        section_length=25
    )

    # Generate schedule
    schedule = scheduler.generate_full_game_schedule(sections=2)

    # Print the schedule
    scheduler.print_schedule(schedule)

    # Analyze fairness
    scheduler.analyze_schedule(schedule)

    return scheduler, schedule

if __name__ == "__main__":
    # First analyze the manual schedule
    analyze_manual_schedule()

    print("\n" + "="*80 + "\n")

    # Then test the generalized approach
    test_generalized_approach()