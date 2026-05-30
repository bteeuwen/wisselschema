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

class TestBlockSizingOptimizer(ScheduleOptimizer):
    """Test different block sizing strategies"""

    def calculate_time_blocks_strategy_1(self, shorter_amount=1.0):
        """Strategy 1: Shorter regular blocks, longer end blocks"""
        blocks = []
        bench_players = self.players_on_bench

        if bench_players == 0:
            for section in range(self.sections):
                start_time = section * self.section_length
                end_time = (section + 1) * self.section_length
                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': self.section_length,
                    'section': section + 1
                })
            return blocks

        subs_per_section = max(1, bench_players)
        if self.game.substitution_length == 'short':
            subs_per_section = subs_per_section * 2

        blocks_per_section = subs_per_section + 1
        base_block_duration = self.section_length / blocks_per_section

        # Strategy: Make regular blocks shorter, final block longer
        regular_block_duration = base_block_duration - shorter_amount
        final_block_extra = shorter_amount * (blocks_per_section - 1)

        print(f"Strategy 1 (shorter by {shorter_amount}min):")
        print(f"  Regular blocks: {regular_block_duration:.1f}min")
        print(f"  Final block extra time: +{final_block_extra:.1f}min")

        for section in range(self.sections):
            section_start = section * self.section_length
            current_time = section_start

            for block_idx in range(blocks_per_section):
                start_time = current_time

                if block_idx == blocks_per_section - 1:
                    # Final block gets extra time
                    end_time = section_start + self.section_length
                    duration = end_time - start_time
                else:
                    # Regular block - shorter
                    duration = regular_block_duration
                    end_time = start_time + duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'section': section + 1
                })

                current_time = end_time

        return blocks

    def calculate_time_blocks_strategy_2(self, redistribution_factor=0.3):
        """Strategy 2: Percentage-based redistribution"""
        blocks = []
        bench_players = self.players_on_bench

        if bench_players == 0:
            for section in range(self.sections):
                start_time = section * self.section_length
                end_time = (section + 1) * self.section_length
                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': self.section_length,
                    'section': section + 1
                })
            return blocks

        subs_per_section = max(1, bench_players)
        if self.game.substitution_length == 'short':
            subs_per_section = subs_per_section * 2

        blocks_per_section = subs_per_section + 1
        base_block_duration = self.section_length / blocks_per_section

        # Strategy: Redistribute percentage of time from regular to final
        time_to_redistribute = base_block_duration * redistribution_factor
        regular_blocks = blocks_per_section - 1
        time_per_regular = time_to_redistribute / regular_blocks

        regular_block_duration = base_block_duration - time_per_regular

        print(f"Strategy 2 ({redistribution_factor*100:.0f}% redistribution):")
        print(f"  Regular blocks: {regular_block_duration:.1f}min (reduced by {time_per_regular:.1f}min)")
        print(f"  Final block gets: +{time_to_redistribute:.1f}min")

        for section in range(self.sections):
            section_start = section * self.section_length
            current_time = section_start

            for block_idx in range(blocks_per_section):
                start_time = current_time

                if block_idx == blocks_per_section - 1:
                    # Final block gets remaining time
                    end_time = section_start + self.section_length
                    duration = end_time - start_time
                else:
                    # Regular block - reduced
                    duration = regular_block_duration
                    end_time = start_time + duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'section': section + 1
                })

                current_time = end_time

        return blocks

    def calculate_time_blocks_strategy_3(self, final_multiplier=1.5):
        """Strategy 3: Final block is X times longer than regular blocks"""
        blocks = []
        bench_players = self.players_on_bench

        if bench_players == 0:
            for section in range(self.sections):
                start_time = section * self.section_length
                end_time = (section + 1) * self.section_length
                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': self.section_length,
                    'section': section + 1
                })
            return blocks

        subs_per_section = max(1, bench_players)
        if self.game.substitution_length == 'short':
            subs_per_section = subs_per_section * 2

        blocks_per_section = subs_per_section + 1
        regular_blocks = blocks_per_section - 1

        # Strategy: Final block is final_multiplier times regular block
        # regular_blocks * x + final_multiplier * x = section_length
        # x * (regular_blocks + final_multiplier) = section_length
        regular_block_duration = self.section_length / (regular_blocks + final_multiplier)
        final_block_duration = regular_block_duration * final_multiplier

        print(f"Strategy 3 (final block {final_multiplier}x regular):")
        print(f"  Regular blocks: {regular_block_duration:.1f}min")
        print(f"  Final block: {final_block_duration:.1f}min")

        for section in range(self.sections):
            section_start = section * self.section_length
            current_time = section_start

            for block_idx in range(blocks_per_section):
                start_time = current_time

                if block_idx == blocks_per_section - 1:
                    # Final block - calculated duration
                    duration = final_block_duration
                    end_time = start_time + duration
                    # Adjust for any rounding to hit section boundary exactly
                    end_time = section_start + self.section_length
                    duration = end_time - start_time
                else:
                    # Regular block
                    duration = regular_block_duration
                    end_time = start_time + duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'section': section + 1
                })

                current_time = end_time

        return blocks

def test_block_sizing_strategies():
    """Test different block sizing approaches"""
    # Create a test game (same as your problematic example)
    game = Game.objects.create(
        name="Block Sizing Test",
        players_in_field=5,
        total_players=7,
        game_length=50,
        sections=2,
        substitution_length='short',
        player_names="Alice, Bob, Charlie, Dave, Eve, Frank, Grace"
    )

    players = game.get_player_list()
    optimizer = TestBlockSizingOptimizer(game)

    print("TESTING DIFFERENT BLOCK SIZING STRATEGIES")
    print("="*60)
    print(f"Game: {game.players_in_field} players on field, {game.total_players} total players")
    print(f"Game length: {game.game_length}min, Sections: {game.sections}")

    # Test current/baseline approach
    print(f"\n{'='*60}")
    print("BASELINE (Current Equal Blocks)")
    baseline_blocks = optimizer.calculate_time_blocks()
    print(f"Block count: {len(baseline_blocks)}")
    for i, block in enumerate(baseline_blocks):
        print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({block['duration']:.1f}min) Section {block['section']}")

    baseline_schedule, _, _ = optimizer.optimize_schedule(10000)
    baseline_stats = print_schedule_summary(baseline_schedule, baseline_blocks, players, "Baseline")

    # Test Strategy 1: Fixed reduction
    for reduction in [0.5, 1.0, 1.5]:
        print(f"\n{'='*60}")
        print(f"STRATEGY 1: Reduce regular blocks by {reduction}min")
        strategy1_blocks = optimizer.calculate_time_blocks_strategy_1(reduction)
        print(f"Block count: {len(strategy1_blocks)}")
        for i, block in enumerate(strategy1_blocks):
            print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({block['duration']:.1f}min) Section {block['section']}")

        # Test with small optimization run
        strategy1_schedule = optimizer.generate_random_schedule(strategy1_blocks)
        if optimizer.validate_schedule(strategy1_schedule, strategy1_blocks):
            strategy1_stats = print_schedule_summary(strategy1_schedule, strategy1_blocks, players, f"Strategy 1 (-{reduction}min)")
        else:
            print("Invalid schedule generated")

    # Test Strategy 2: Percentage redistribution
    for factor in [0.2, 0.3, 0.4]:
        print(f"\n{'='*60}")
        print(f"STRATEGY 2: {factor*100:.0f}% redistribution")
        strategy2_blocks = optimizer.calculate_time_blocks_strategy_2(factor)
        print(f"Block count: {len(strategy2_blocks)}")
        for i, block in enumerate(strategy2_blocks):
            print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({block['duration']:.1f}min) Section {block['section']}")

        strategy2_schedule = optimizer.generate_random_schedule(strategy2_blocks)
        if optimizer.validate_schedule(strategy2_schedule, strategy2_blocks):
            strategy2_stats = print_schedule_summary(strategy2_schedule, strategy2_blocks, players, f"Strategy 2 ({factor*100:.0f}%)")
        else:
            print("Invalid schedule generated")

    # Test Strategy 3: Multiplier approach
    for multiplier in [1.3, 1.5, 2.0]:
        print(f"\n{'='*60}")
        print(f"STRATEGY 3: Final block {multiplier}x regular")
        strategy3_blocks = optimizer.calculate_time_blocks_strategy_3(multiplier)
        print(f"Block count: {len(strategy3_blocks)}")
        for i, block in enumerate(strategy3_blocks):
            print(f"  Block {i+1}: {block['start_time']:.1f}-{block['end_time']:.1f} ({block['duration']:.1f}min) Section {block['section']}")

        strategy3_schedule = optimizer.generate_random_schedule(strategy3_blocks)
        if optimizer.validate_schedule(strategy3_schedule, strategy3_blocks):
            strategy3_stats = print_schedule_summary(strategy3_schedule, strategy3_blocks, players, f"Strategy 3 ({multiplier}x)")
        else:
            print("Invalid schedule generated")

    # Clean up
    game.delete()

if __name__ == "__main__":
    test_block_sizing_strategies()