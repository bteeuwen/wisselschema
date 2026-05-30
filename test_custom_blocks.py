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

from hockeysub.models import Game
from hockeysub.scheduler import ScheduleOptimizer

def print_schedule_summary(schedule_data, time_blocks, players, title):
    """Print a tabular summary of the schedule"""
    print(f"\n=== {title} ===")

    # Calculate stats for each player
    player_stats = []
    for idx in range(len(players)):
        playing_time = 0
        bench_blocks = 0

        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule_data[block_key]

            if idx in block_data['active']:
                playing_time += block_data['duration']
            else:
                bench_blocks += 1

        bench_time = sum(block['duration'] for block in time_blocks) - playing_time
        player_stats.append({
            'name': players[idx],
            'playing_time': playing_time,
            'bench_time': bench_time,
            'bench_blocks': bench_blocks
        })

    # Print header
    print(f"{'Player':<8} {'Playing':<8} {'Bench':<8} {'Bench':<8}")
    print(f"{'Name':<8} {'Time':<8} {'Time':<8} {'Blocks':<8}")
    print("-" * 36)

    # Print player data
    for stat in player_stats:
        print(f"{stat['name']:<8} {stat['playing_time']:.1f}min   {stat['bench_time']:.1f}min   {stat['bench_blocks']}")

    # Print summary stats
    playing_times = [s['playing_time'] for s in player_stats]
    bench_blocks = [s['bench_blocks'] for s in player_stats]

    print("-" * 36)
    print(f"Playing time range: {min(playing_times):.1f} - {max(playing_times):.1f}min (diff: {max(playing_times) - min(playing_times):.1f}min)")
    print(f"Bench blocks range: {min(bench_blocks)} - {max(bench_blocks)} (diff: {max(bench_blocks) - min(bench_blocks)})")

    return player_stats

def test_custom_block_duration():
    """Test the custom block duration functionality"""

    # Test Case 1: 3.5 minute blocks (3:30)
    print("TESTING CUSTOM BLOCK DURATION FUNCTIONALITY")
    print("=" * 60)

    game1 = Game.objects.create(
        name="Custom Block Test - 3:30 blocks",
        players_in_field=5,
        total_players=7,
        game_length=50,
        sections=2,
        custom_block_duration=3.5,  # 3:30
        player_names="Alice, Bob, Charlie, Dave, Eve, Frank, Grace"
    )

    players1 = game1.get_player_list()
    optimizer1 = ScheduleOptimizer(game1)

    print(f"\nTEST 1: Custom 3:30 blocks")
    print(f"Game: {game1.players_in_field} players on field, {game1.total_players} total players")
    print(f"Game length: {game1.game_length}min, Sections: {game1.sections}")
    print(f"Custom block duration: {game1.custom_block_duration:.2f}min (3:30)")

    # Generate time blocks
    blocks1 = optimizer1.calculate_time_blocks()
    print(f"\nGenerated {len(blocks1)} time blocks:")
    for i, block in enumerate(blocks1):
        duration_min = int(block['duration'])
        duration_sec = int((block['duration'] % 1) * 60)
        print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({duration_min}:{duration_sec:02d}) Section {block['section']}")

    # Optimize schedule
    schedule1, time_blocks1, score1 = optimizer1.optimize_schedule(5000)
    stats1 = print_schedule_summary(schedule1, time_blocks1, players1, f"Custom 3:30 blocks")

    # Test Case 2: 4.0 minute blocks (4:00)
    print(f"\n{'='*60}")
    print(f"\nTEST 2: Custom 4:00 blocks")

    game2 = Game.objects.create(
        name="Custom Block Test - 4:00 blocks",
        players_in_field=5,
        total_players=7,
        game_length=50,
        sections=2,
        custom_block_duration=4.0,  # 4:00
        player_names="Alice, Bob, Charlie, Dave, Eve, Frank, Grace"
    )

    optimizer2 = ScheduleOptimizer(game2)
    blocks2 = optimizer2.calculate_time_blocks()

    print(f"Custom block duration: {game2.custom_block_duration:.2f}min (4:00)")
    print(f"\nGenerated {len(blocks2)} time blocks:")
    for i, block in enumerate(blocks2):
        duration_min = int(block['duration'])
        duration_sec = int((block['duration'] % 1) * 60)
        print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({duration_min}:{duration_sec:02d}) Section {block['section']}")

    schedule2, time_blocks2, score2 = optimizer2.optimize_schedule(5000)
    stats2 = print_schedule_summary(schedule2, time_blocks2, game2.get_player_list(), f"Custom 4:00 blocks")

    # Test Case 3: 2.75 minute blocks (2:45)
    print(f"\n{'='*60}")
    print(f"\nTEST 3: Custom 2:45 blocks")

    game3 = Game.objects.create(
        name="Custom Block Test - 2:45 blocks",
        players_in_field=5,
        total_players=7,
        game_length=50,
        sections=2,
        custom_block_duration=2.75,  # 2:45
        player_names="Alice, Bob, Charlie, Dave, Eve, Frank, Grace"
    )

    optimizer3 = ScheduleOptimizer(game3)
    blocks3 = optimizer3.calculate_time_blocks()

    print(f"Custom block duration: {game3.custom_block_duration:.2f}min (2:45)")
    print(f"\nGenerated {len(blocks3)} time blocks:")
    for i, block in enumerate(blocks3):
        duration_min = int(block['duration'])
        duration_sec = int((block['duration'] % 1) * 60)
        print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({duration_min}:{duration_sec:02d}) Section {block['section']}")

    schedule3, time_blocks3, score3 = optimizer3.optimize_schedule(5000)
    stats3 = print_schedule_summary(schedule3, time_blocks3, game3.get_player_list(), f"Custom 2:45 blocks")

    # Comparison
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print("=" * 60)

    test_cases = [
        ("Custom 3:30 blocks", stats1, score1),
        ("Custom 4:00 blocks", stats2, score2),
        ("Custom 2:45 blocks", stats3, score3),
    ]

    for name, stats, score in test_cases:
        if stats:
            bench_blocks = [s['bench_blocks'] for s in stats]
            playing_times = [s['playing_time'] for s in stats]
            print(f"{name:<18}: Score {score:.1f}, Bench blocks {min(bench_blocks)}-{max(bench_blocks)} (diff: {max(bench_blocks)-min(bench_blocks)}), "
                  f"Playing time {min(playing_times):.1f}-{max(playing_times):.1f}min (diff: {max(playing_times)-min(playing_times):.1f}min)")

    # Clean up
    game1.delete()
    game2.delete()
    game3.delete()

if __name__ == "__main__":
    test_custom_block_duration()