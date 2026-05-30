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
import copy
import random

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
    print(f"{'Player':<10} {'Playing':<8} {'Bench':<8} {'Bench':<8}")
    print(f"{'Name':<10} {'Time':<8} {'Time':<8} {'Blocks':<8}")
    print("-" * 40)

    # Print player data
    for stat in player_stats:
        print(f"{stat['name']:<10} {stat['playing_time']:.1f}min   {stat['bench_time']:.1f}min   {stat['bench_blocks']}")

    # Print summary stats
    playing_times = [s['playing_time'] for s in player_stats]
    bench_blocks = [s['bench_blocks'] for s in player_stats]

    print("-" * 40)
    print(f"Playing time range: {min(playing_times):.1f} - {max(playing_times):.1f}min (diff: {max(playing_times) - min(playing_times):.1f}min)")
    print(f"Bench blocks range: {min(bench_blocks)} - {max(bench_blocks)} (diff: {max(bench_blocks) - min(bench_blocks)})")

    return player_stats

class EnhancedScheduleOptimizer(ScheduleOptimizer):
    """Enhanced scheduler with different fairness approaches"""

    def calculate_schedule_score_weighted(self, schedule, time_blocks):
        """Approach 1: Heavily weight bench block fairness"""
        # Calculate playing time for each player
        playing_times = [0.0] * self.num_players
        bench_blocks = [0] * self.num_players

        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]
            active_players = block_data['active']
            duration = block_data['duration']

            # Add playing time
            for player_idx in active_players:
                playing_times[player_idx] += duration

            # Count bench blocks
            for player_idx in range(self.num_players):
                if player_idx not in active_players:
                    bench_blocks[player_idx] += 1

        # HARD CONSTRAINT: Reject schedules that are too unfair in playing time
        min_time = min(playing_times)
        max_time = max(playing_times)
        time_difference = max_time - min_time
        avg_playing_time = sum(playing_times) / len(playing_times)
        max_allowed_difference = max(avg_playing_time * 0.20, 3.0)

        if time_difference > max_allowed_difference:
            return 10000 + time_difference * 1000

        # Score components
        score = 0.0

        # 1. Playing time variance (reduced weight)
        time_variance = sum((pt - avg_playing_time) ** 2 for pt in playing_times) / len(playing_times)
        score += time_variance * 100

        # 2. HEAVILY weight bench block fairness (new)
        min_bench = min(bench_blocks)
        max_bench = max(bench_blocks)
        bench_difference = max_bench - min_bench
        score += bench_difference * 2000  # Heavy penalty for uneven bench blocks

        # 3. Bench block variance
        avg_bench = sum(bench_blocks) / len(bench_blocks)
        bench_variance = sum((bb - avg_bench) ** 2 for bb in bench_blocks) / len(bench_blocks)
        score += bench_variance * 1000

        return score

    def optimize_with_weighted_scoring(self, max_iterations=10000):
        """Approach 1: Weighted scoring approach"""
        time_blocks = self.calculate_time_blocks()
        best_schedule = None
        best_score = float('inf')

        for iteration in range(max_iterations):
            candidate_schedule = self.generate_random_schedule(time_blocks)
            if not self.validate_schedule(candidate_schedule, time_blocks):
                continue

            score = self.calculate_schedule_score_weighted(candidate_schedule, time_blocks)

            if score < best_score:
                best_score = score
                best_schedule = candidate_schedule.copy()

        return best_schedule, time_blocks, best_score

    def optimize_with_constraints(self, max_iterations=10000):
        """Approach 2: Hard constraint on bench block difference"""
        time_blocks = self.calculate_time_blocks()
        best_schedule = None
        best_score = float('inf')

        for iteration in range(max_iterations):
            candidate_schedule = self.generate_random_schedule(time_blocks)
            if not self.validate_schedule(candidate_schedule, time_blocks):
                continue

            # Check bench block constraint
            bench_blocks = [0] * self.num_players
            for block in time_blocks:
                block_key = f"{block['start_time']}-{block['end_time']}"
                block_data = candidate_schedule[block_key]
                for player_idx in range(self.num_players):
                    if player_idx not in block_data['active']:
                        bench_blocks[player_idx] += 1

            # Hard constraint: max 1 bench block difference
            if max(bench_blocks) - min(bench_blocks) > 1:
                continue

            score = self.calculate_schedule_score(candidate_schedule, time_blocks)

            if score < best_score:
                best_score = score
                best_schedule = candidate_schedule.copy()

        return best_schedule, time_blocks, best_score

    def swap_players_for_fairness(self, schedule, time_blocks):
        """Approach 3: Post-processing optimization"""
        # Calculate current bench blocks
        bench_blocks = [0] * self.num_players
        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]
            for player_idx in range(self.num_players):
                if player_idx not in block_data['active']:
                    bench_blocks[player_idx] += 1

        # Try to balance bench blocks by swapping players between blocks
        max_swaps = 100
        for _ in range(max_swaps):
            # Find players with different bench block counts
            min_bench = min(bench_blocks)
            max_bench = max(bench_blocks)

            if max_bench - min_bench <= 1:
                break  # Already balanced enough

            # Find a player with too many bench blocks and one with too few
            high_player = bench_blocks.index(max_bench)
            low_player = bench_blocks.index(min_bench)

            # Try to swap them in a random block
            block = random.choice(time_blocks)
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]

            high_is_active = high_player in block_data['active']
            low_is_active = low_player in block_data['active']

            # If high_player is benched and low_player is active, swap them
            if not high_is_active and low_is_active:
                # Remove low_player from active, add high_player
                block_data['active'].remove(low_player)
                block_data['active'].append(high_player)

                # Update bench players
                block_data['bench'].remove(high_player)
                block_data['bench'].append(low_player)

                # Update bench block counts
                bench_blocks[high_player] -= 1
                bench_blocks[low_player] += 1

        return schedule

    def optimize_with_postprocessing(self, max_iterations=5000):
        """Approach 3: Post-processing optimization"""
        # First get a good base schedule
        schedule, time_blocks, score = self.optimize_schedule(max_iterations)

        # Then improve it with post-processing
        improved_schedule = self.swap_players_for_fairness(schedule, time_blocks)
        improved_score = self.calculate_schedule_score(improved_schedule, time_blocks)

        return improved_schedule, time_blocks, improved_score

def test_approaches():
    """Test all three approaches"""
    # Create a test game
    game = Game.objects.create(
        name="Test Game",
        players_in_field=5,
        total_players=8,
        game_length=50,
        sections=2,
        substitution_length='short',
        player_names="P1, P2, P3, P4, P5, P6, P7, P8"
    )

    players = game.get_player_list()
    optimizer = EnhancedScheduleOptimizer(game)

    print("Testing different scheduling approaches...")
    print(f"Game: {game.players_in_field} players on field, {game.total_players} total players")
    print(f"Game length: {game.game_length}min, Sections: {game.sections}")

    # Test original approach
    print("\n" + "="*60)
    print("TESTING ORIGINAL APPROACH")
    schedule1, blocks1, score1 = optimizer.optimize_schedule(5000)
    stats1 = print_schedule_summary(schedule1, blocks1, players, "Original Approach")

    # Test weighted scoring
    print("\n" + "="*60)
    print("TESTING WEIGHTED SCORING APPROACH")
    schedule2, blocks2, score2 = optimizer.optimize_with_weighted_scoring(5000)
    stats2 = print_schedule_summary(schedule2, blocks2, players, "Weighted Scoring")

    # Test constraint-based
    print("\n" + "="*60)
    print("TESTING CONSTRAINT-BASED APPROACH")
    schedule3, blocks3, score3 = optimizer.optimize_with_constraints(5000)
    if schedule3:
        stats3 = print_schedule_summary(schedule3, blocks3, players, "Constraint-Based")
    else:
        print("No valid schedule found with constraint-based approach")
        stats3 = None

    # Test post-processing
    print("\n" + "="*60)
    print("TESTING POST-PROCESSING APPROACH")
    schedule4, blocks4, score4 = optimizer.optimize_with_postprocessing(5000)
    stats4 = print_schedule_summary(schedule4, blocks4, players, "Post-Processing")

    # Summary comparison
    print("\n" + "="*60)
    print("SUMMARY COMPARISON")
    print("="*60)

    approaches = [
        ("Original", stats1),
        ("Weighted Scoring", stats2),
        ("Constraint-Based", stats3),
        ("Post-Processing", stats4)
    ]

    for name, stats in approaches:
        if stats:
            bench_blocks = [s['bench_blocks'] for s in stats]
            playing_times = [s['playing_time'] for s in stats]
            print(f"{name:<18}: Bench blocks {min(bench_blocks)}-{max(bench_blocks)} (diff: {max(bench_blocks)-min(bench_blocks)}), "
                  f"Playing time {min(playing_times):.1f}-{max(playing_times):.1f}min (diff: {max(playing_times)-min(playing_times):.1f}min)")
        else:
            print(f"{name:<18}: No valid solution found")

    # Clean up
    game.delete()

if __name__ == "__main__":
    test_approaches()