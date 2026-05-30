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
from test_scheduler_approaches import EnhancedScheduleOptimizer, print_schedule_summary

def test_difficult_scenario():
    """Test with a more challenging scenario"""
    # Create a more difficult test case
    game = Game.objects.create(
        name="Difficult Test Game",
        players_in_field=6,
        total_players=11,
        game_length=60,
        sections=3,
        substitution_length='short',
        player_names="P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11"
    )

    players = game.get_player_list()
    optimizer = EnhancedScheduleOptimizer(game)

    print("Testing MORE DIFFICULT scenario...")
    print(f"Game: {game.players_in_field} players on field, {game.total_players} total players")
    print(f"Game length: {game.game_length}min, Sections: {game.sections}")

    # Test original approach
    print("\n" + "="*60)
    print("TESTING ORIGINAL APPROACH")
    schedule1, blocks1, score1 = optimizer.optimize_schedule(10000)
    stats1 = print_schedule_summary(schedule1, blocks1, players, "Original Approach")

    # Test weighted scoring
    print("\n" + "="*60)
    print("TESTING WEIGHTED SCORING APPROACH")
    schedule2, blocks2, score2 = optimizer.optimize_with_weighted_scoring(10000)
    stats2 = print_schedule_summary(schedule2, blocks2, players, "Weighted Scoring")

    # Summary comparison
    print("\n" + "="*60)
    print("SUMMARY COMPARISON")
    print("="*60)

    approaches = [
        ("Original", stats1),
        ("Weighted Scoring", stats2),
    ]

    for name, stats in approaches:
        if stats:
            bench_blocks = [s['bench_blocks'] for s in stats]
            playing_times = [s['playing_time'] for s in stats]
            print(f"{name:<18}: Bench blocks {min(bench_blocks)}-{max(bench_blocks)} (diff: {max(bench_blocks)-min(bench_blocks)}), "
                  f"Playing time {min(playing_times):.1f}-{max(playing_times):.1f}min (diff: {max(playing_times)-min(playing_times):.1f}min)")

    # Clean up
    game.delete()

if __name__ == "__main__":
    test_difficult_scenario()