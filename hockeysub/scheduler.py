import random
import math
import logging
from typing import List, Dict, Tuple
from django.db import models
from .models import Game, Schedule, Player, TimeBlock

logger = logging.getLogger(__name__)


class ScheduleOptimizer:
    def __init__(self, game: Game):
        self.game = game
        self.players = game.get_player_list()
        self.num_players = len(self.players)
        self.players_in_field = game.players_in_field
        self.players_on_bench = self.num_players - self.players_in_field
        self.game_length = game.game_length
        self.sections = game.sections
        self.paired_subbing = game.paired_subbing

        self.section_length = self.game_length / self.sections
        self.ideal_playing_time = game.calculate_playing_time_per_player()
        self.substitution_mode = game.substitution_mode

    def round_to_interval(self, time_value: float, interval_seconds: int = 15) -> float:
        """Round time to specified second interval."""
        # Convert to seconds, round to nearest interval, convert back to minutes
        seconds = time_value * 60
        rounded_seconds = round(seconds / interval_seconds) * interval_seconds
        return rounded_seconds / 60

    def round_to_15_seconds(self, time_value: float) -> float:
        """Round time to nearest 15-second interval."""
        return self.round_to_interval(time_value, 15)


    def test_rounding_strategies(self, base_schedule: Dict, base_time_blocks: List[Dict]) -> Tuple[Dict, List[Dict], float]:
        """Test different time rounding strategies and return the best one."""
        logger.info("Testing different time rounding strategies for optimal fairness...")

        # Different rounding intervals to test (in seconds)
        rounding_strategies = [15]  # 10s, 15s, 20s, 30s, 45s, 1min

        best_strategy_schedule = base_schedule
        best_strategy_blocks = base_time_blocks
        best_strategy_score = float('inf')
        best_interval = 15

        for interval_seconds in rounding_strategies:
            logger.info(f"Testing {interval_seconds}-second rounding interval...")

            # Create time blocks with this rounding strategy
            test_blocks = self.calculate_time_blocks_with_rounding(interval_seconds)

            # Optimize with this block structure
            test_schedule = None
            test_score = float('inf')

            # Run optimization with this rounding strategy
            for iteration in range(20000):  # Reasonable number for testing
                candidate_schedule = self.generate_random_schedule(test_blocks)

                if not self.validate_schedule(candidate_schedule, test_blocks):
                    continue

                score = self.calculate_schedule_score(candidate_schedule, test_blocks)

                if score < test_score:
                    test_score = score
                    test_schedule = candidate_schedule.copy()

                # Early stopping for good solutions
                if score < 500:
                    break

            if test_schedule and test_score < best_strategy_score:
                best_strategy_score = test_score
                best_strategy_schedule = test_schedule
                best_strategy_blocks = test_blocks
                best_interval = interval_seconds

                # Calculate fairness metrics for logging
                playing_times = [0.0] * self.num_players
                for block in test_blocks:
                    block_key = f"{block['start_time']}-{block['end_time']}"
                    block_data = test_schedule[block_key]
                    for player_idx in block_data['active']:
                        playing_times[player_idx] += block_data['duration']

                min_time = min(playing_times)
                max_time = max(playing_times)
                time_diff = max_time - min_time

                logger.info(f"{interval_seconds}s rounding: Score {test_score:.2f}, Time range: {min_time:.1f}-{max_time:.1f}min (diff: {time_diff:.1f}min)")

        logger.info(f"Best rounding strategy: {best_interval}-second intervals (score: {best_strategy_score:.2f})")
        return best_strategy_schedule, best_strategy_blocks, best_strategy_score

    def calculate_time_blocks_with_rounding(self, interval_seconds: int = 15) -> List[Dict]:
        """Calculate time blocks with specified rounding interval."""
        blocks = []

        # Zen mode: rounding irrelevant, return fixed section blocks
        if self.substitution_mode == 'zen':
            return self.calculate_zen_time_blocks()

        # Calculate how many substitutions are needed per section
        bench_players = self.players_on_bench

        if bench_players == 0:
            # No substitutions needed - all players play the whole game
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

        # Estimate optimal number of substitutions per section
        total_playing_time = self.players_in_field * self.game_length
        subs_per_section = max(1, bench_players)

        # Adjust number of substitutions based on substitution length setting
        if self.game.substitution_length == 'short':
            subs_per_section = subs_per_section * 2

        # Calculate block duration for each section
        blocks_per_section = subs_per_section + 1  # +1 for the final block
        base_block_duration = self.section_length / blocks_per_section

        # Round the base block duration to specified interval
        rounded_base_duration = self.round_to_interval(base_block_duration, interval_seconds)

        for section in range(self.sections):
            section_start = section * self.section_length
            current_time = section_start

            for block_idx in range(blocks_per_section):
                start_time = current_time

                if block_idx == blocks_per_section - 1:
                    # Last block gets remaining time to reach section boundary
                    end_time = section_start + self.section_length
                else:
                    # Regular block - use rounded duration but ensure continuity
                    end_time = start_time + rounded_base_duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'section': section + 1
                })

                current_time = end_time

        return blocks

    def calculate_zen_time_blocks(self) -> List[Dict]:
        """Calculate time blocks for zen mode: exactly 4 blocks (one per quarter).

        Always divides the game into 4 equal quarters regardless of the sections
        setting. Substitutions only happen at quarter breaks.
        """
        zen_quarters = 4
        quarter_length = self.game_length / zen_quarters
        blocks = []
        for i in range(zen_quarters):
            start_time = i * quarter_length
            end_time = (i + 1) * quarter_length
            blocks.append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': quarter_length,
                'section': i + 1
            })
        return blocks

    def calculate_time_blocks(self) -> List[Dict]:
        """Calculate optimal time block structure for substitutions."""
        blocks = []

        # Zen mode: one block per section, subs only at quarter breaks
        if self.substitution_mode == 'zen':
            return self.calculate_zen_time_blocks()

        # Check if custom block duration is specified
        if self.game.custom_block_duration is not None:
            return self.calculate_custom_time_blocks()

        # Calculate how many substitutions are needed per section
        bench_players = self.players_on_bench

        if bench_players == 0:
            # No substitutions needed - all players play the whole game
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

        # Estimate optimal number of substitutions per section
        # Each player should get roughly equal playing time
        total_playing_time = self.players_in_field * self.game_length
        subs_per_section = max(1, bench_players)

        # Adjust number of substitutions based on substitution length setting
        if self.game.substitution_length == 'short':
            # For short substitutions, double the number of substitutions per section
            # This creates more blocks, making each bench period shorter
            subs_per_section = subs_per_section * 2

        # Calculate block duration for each section
        blocks_per_section = subs_per_section + 1  # +1 for the final block
        base_block_duration = self.section_length / blocks_per_section

        # Round the base block duration to 15-second intervals
        rounded_base_duration = self.round_to_15_seconds(base_block_duration)

        for section in range(self.sections):
            section_start = section * self.section_length
            current_time = section_start

            for block_idx in range(blocks_per_section):
                start_time = current_time

                if block_idx == blocks_per_section - 1:
                    # Last block gets remaining time to reach section boundary
                    end_time = section_start + self.section_length
                else:
                    # Regular block - use rounded duration but ensure continuity
                    end_time = start_time + rounded_base_duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'section': section + 1
                })

                current_time = end_time

        return blocks

    def calculate_custom_time_blocks(self) -> List[Dict]:
        """Calculate time blocks using user-defined custom block duration."""
        blocks = []
        custom_duration = self.game.custom_block_duration

        logger.info(f"Using custom block duration: {custom_duration:.2f} minutes ({int(custom_duration)}:{int((custom_duration % 1) * 60):02d})")

        for section in range(self.sections):
            section_start = section * self.section_length
            section_end = (section + 1) * self.section_length
            current_time = section_start

            # Create as many full custom blocks as possible
            block_count = 0
            while current_time + custom_duration <= section_end:
                start_time = current_time
                end_time = current_time + custom_duration

                blocks.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': custom_duration,
                    'section': section + 1
                })

                current_time = end_time
                block_count += 1

            # Create left-over block if there's remaining time
            remaining_time = section_end - current_time
            if remaining_time > 0.1:  # Only create if meaningful time remains (> 6 seconds)
                blocks.append({
                    'start_time': current_time,
                    'end_time': section_end,
                    'duration': remaining_time,
                    'section': section + 1
                })
                block_count += 1

            logger.info(f"Section {section + 1}: Created {block_count} blocks ({block_count - 1} custom blocks of {custom_duration:.2f}min + 1 left-over block of {remaining_time:.2f}min)" if remaining_time > 0.1 else f"Section {section + 1}: Created {block_count} custom blocks of {custom_duration:.2f}min")

        return blocks


    def postprocess_for_playing_time_balance(self, schedule: Dict, time_blocks: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """Postprocess schedule to balance playing time using buffer blocks."""
        # Calculate current playing times
        playing_times = [0.0] * self.num_players
        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]
            for player_idx in block_data['active']:
                playing_times[player_idx] += block['duration']

        # Check if adjustment is needed
        avg_playing_time = sum(playing_times) / len(playing_times)
        max_time = max(playing_times)
        min_time = min(playing_times)
        max_diff_percentage = (max_time - min_time) / avg_playing_time

        logger.info(f"Playing time analysis: {min_time:.1f}-{max_time:.1f}min, diff: {(max_diff_percentage*100):.1f}%")

        # Only adjust if difference is more than 12%
        if max_diff_percentage <= 0.12:
            logger.info("Playing time difference ≤12%, no postprocessing needed")
            return schedule, time_blocks

        logger.info(f"Playing time difference {(max_diff_percentage*100):.1f}% > 12%, applying postprocessing")

        # Calculate adjustment percentage (use the difference percentage)
        shrink_percentage = max_diff_percentage

        # Find players who need more time (those below average)
        players_needing_time = []
        for i, time in enumerate(playing_times):
            if time < avg_playing_time:
                deficit = avg_playing_time - time
                players_needing_time.append((i, deficit))

        # Sort by deficit (largest first)
        players_needing_time.sort(key=lambda x: x[1], reverse=True)

        if not players_needing_time:
            logger.info("No players significantly below average, no adjustment needed")
            return schedule, time_blocks

        logger.info(f"Players needing more time: {[f'Player {p[0]} (deficit: {p[1]:.1f}min)' for p in players_needing_time]}")

        # Create new time blocks and schedule with adjustments
        new_time_blocks = []
        new_schedule = {}

        # Process each section
        for section in range(self.sections):
            section_blocks = [block for block in time_blocks if block['section'] == section + 1]
            section_start = section * self.section_length
            section_end = (section + 1) * self.section_length

            # Shrink all blocks in this section
            total_shrinkage = 0
            current_time = section_start

            for block in section_blocks:
                old_key = f"{block['start_time']}-{block['end_time']}"
                original_duration = block['duration']

                # Shrink this block
                new_duration = original_duration * (1 - shrink_percentage)

                # Round the new duration to 15-second intervals for intuitive timing
                rounded_new_duration = self.round_to_15_seconds(new_duration)
                total_shrinkage += original_duration - rounded_new_duration

                # Create new block with rounded adjusted duration
                new_block = {
                    'start_time': current_time,
                    'end_time': current_time + rounded_new_duration,
                    'duration': rounded_new_duration,
                    'section': block['section']
                }
                new_time_blocks.append(new_block)

                # Copy schedule data to new key
                new_key = f"{new_block['start_time']}-{new_block['end_time']}"
                new_schedule[new_key] = schedule[old_key].copy()
                new_schedule[new_key]['duration'] = rounded_new_duration
                new_schedule[new_key]['end_time'] = new_block['end_time']

                current_time += rounded_new_duration

            # Create buffer block with the shrinkage time
            if total_shrinkage > 0.1:  # Only create if meaningful time
                buffer_start = current_time
                buffer_end = section_end  # Go to section boundary
                buffer_duration = buffer_end - buffer_start

                # Determine who plays in buffer block
                if section == self.sections - 1:  # Last section
                    # For last section, ignore pair subs rule - just add the player(s) who need time most
                    if players_needing_time:
                        player_to_add = players_needing_time[0][0]  # Player with most deficit

                        # Start with current active players and try to add the deficit player
                        last_block_key = list(new_schedule.keys())[-1]
                        current_active = set(new_schedule[last_block_key]['active'])

                        if player_to_add not in current_active and len(current_active) < self.num_players:
                            # Add the deficit player, remove someone else to maintain field size
                            current_active.add(player_to_add)
                            if len(current_active) > self.players_in_field:
                                # Remove the player with most playing time who's currently active
                                active_times = [(p, playing_times[p]) for p in current_active if p != player_to_add]
                                active_times.sort(key=lambda x: x[1], reverse=True)
                                current_active.remove(active_times[0][0])

                            buffer_active = list(current_active)
                        else:
                            # Fallback to existing active players
                            buffer_active = new_schedule[last_block_key]['active'].copy()
                    else:
                        # Fallback to existing active players
                        last_block_key = list(new_schedule.keys())[-1]
                        buffer_active = new_schedule[last_block_key]['active'].copy()
                else:
                    # For non-last sections, maintain pair subs rule
                    # Add players who need time most while respecting field size
                    last_block_key = list(new_schedule.keys())[-1]
                    current_active = set(new_schedule[last_block_key]['active'])

                    # Try to swap in players who need more time
                    for player_idx, deficit in players_needing_time:
                        if player_idx not in current_active:
                            # Find someone to swap out (prefer player with most time)
                            active_times = [(p, playing_times[p]) for p in current_active]
                            active_times.sort(key=lambda x: x[1], reverse=True)

                            current_active.remove(active_times[0][0])
                            current_active.add(player_idx)
                            break

                    buffer_active = list(current_active)

                buffer_bench = [p for p in range(self.num_players) if p not in buffer_active]

                # Create buffer block
                buffer_block = {
                    'start_time': buffer_start,
                    'end_time': buffer_end,
                    'duration': buffer_duration,
                    'section': section + 1
                }
                new_time_blocks.append(buffer_block)

                # Create buffer schedule entry
                buffer_key = f"{buffer_start}-{buffer_end}"
                new_schedule[buffer_key] = {
                    'active': buffer_active,
                    'bench': buffer_bench,
                    'start_time': buffer_start,
                    'end_time': buffer_end,
                    'duration': buffer_duration,
                    'section': section + 1
                }

                logger.info(f"Section {section + 1}: Created buffer block {buffer_duration:.1f}min with players {buffer_active}")

        logger.info(f"Postprocessing complete: {len(new_time_blocks)} blocks created")
        return new_schedule, new_time_blocks

    def postprocess_for_playing_time_balance_with_multiplier(self, schedule: Dict, time_blocks: List[Dict], buffer_multiplier: float = 1.0) -> Tuple[Dict, List[Dict]]:
        """Postprocess schedule to balance playing time using buffer blocks with configurable buffer size."""
        # Calculate current playing times
        playing_times = [0.0] * self.num_players
        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]
            for player_idx in block_data['active']:
                playing_times[player_idx] += block['duration']

        # Check if adjustment is needed
        avg_playing_time = sum(playing_times) / len(playing_times)
        max_time = max(playing_times)
        min_time = min(playing_times)
        max_diff_percentage = (max_time - min_time) / avg_playing_time

        logger.info(f"Playing time analysis (multiplier {buffer_multiplier}x): {min_time:.1f}-{max_time:.1f}min, diff: {(max_diff_percentage*100):.1f}%")

        # Only adjust if difference is more than 12%
        if max_diff_percentage <= 0.12:
            logger.info("Playing time difference ≤12%, no postprocessing needed")
            return schedule, time_blocks

        logger.info(f"Playing time difference {(max_diff_percentage*100):.1f}% > 12%, applying postprocessing with {buffer_multiplier}x buffer")

        # Calculate adjustment percentage (use the difference percentage, adjusted by multiplier)
        shrink_percentage = max_diff_percentage * buffer_multiplier

        # Find players who need more time (those below average)
        players_needing_time = []
        for i, time in enumerate(playing_times):
            if time < avg_playing_time:
                deficit = avg_playing_time - time
                players_needing_time.append((i, deficit))

        # Sort by deficit (largest first)
        players_needing_time.sort(key=lambda x: x[1], reverse=True)

        if not players_needing_time:
            logger.info("No players significantly below average, no adjustment needed")
            return schedule, time_blocks

        logger.info(f"Players needing more time: {[f'Player {p[0]} (deficit: {p[1]:.1f}min)' for p in players_needing_time]}")

        # Create new time blocks and schedule with adjustments
        new_time_blocks = []
        new_schedule = {}

        # Process each section
        for section in range(self.sections):
            section_blocks = [block for block in time_blocks if block['section'] == section + 1]
            section_start = section * self.section_length
            section_end = (section + 1) * self.section_length

            # Shrink all blocks in this section
            total_shrinkage = 0
            current_time = section_start

            for block in section_blocks:
                old_key = f"{block['start_time']}-{block['end_time']}"
                original_duration = block['duration']

                # Shrink this block
                new_duration = original_duration * (1 - shrink_percentage)

                # Round the new duration to 15-second intervals for intuitive timing
                rounded_new_duration = self.round_to_15_seconds(new_duration)
                total_shrinkage += original_duration - rounded_new_duration

                # Create new block with rounded adjusted duration
                new_block = {
                    'start_time': current_time,
                    'end_time': current_time + rounded_new_duration,
                    'duration': rounded_new_duration,
                    'section': block['section']
                }
                new_time_blocks.append(new_block)

                # Copy schedule data to new key
                new_key = f"{new_block['start_time']}-{new_block['end_time']}"
                new_schedule[new_key] = schedule[old_key].copy()
                new_schedule[new_key]['duration'] = rounded_new_duration
                new_schedule[new_key]['end_time'] = new_block['end_time']

                current_time += rounded_new_duration

            # Create buffer block with the shrinkage time
            if total_shrinkage > 0.1:  # Only create if meaningful time
                buffer_start = current_time
                buffer_end = section_end  # Go to section boundary
                buffer_duration = buffer_end - buffer_start

                # Determine who plays in buffer block
                if section == self.sections - 1:  # Last section
                    # For last section, ignore pair subs rule - just add the player(s) who need time most
                    if players_needing_time:
                        player_to_add = players_needing_time[0][0]  # Player with most deficit

                        # Start with current active players and try to add the deficit player
                        last_block_key = list(new_schedule.keys())[-1]
                        current_active = set(new_schedule[last_block_key]['active'])

                        if player_to_add not in current_active and len(current_active) < self.num_players:
                            # Add the deficit player, remove someone else to maintain field size
                            current_active.add(player_to_add)
                            if len(current_active) > self.players_in_field:
                                # Remove the player with most playing time who's currently active
                                active_times = [(p, playing_times[p]) for p in current_active if p != player_to_add]
                                active_times.sort(key=lambda x: x[1], reverse=True)
                                current_active.remove(active_times[0][0])

                            buffer_active = list(current_active)
                        else:
                            # Fallback to existing active players
                            buffer_active = new_schedule[last_block_key]['active'].copy()
                    else:
                        # Fallback to existing active players
                        last_block_key = list(new_schedule.keys())[-1]
                        buffer_active = new_schedule[last_block_key]['active'].copy()
                else:
                    # For non-last sections, maintain pair subs rule
                    # Add players who need time most while respecting field size
                    last_block_key = list(new_schedule.keys())[-1]
                    current_active = set(new_schedule[last_block_key]['active'])

                    # Try to swap in players who need more time
                    for player_idx, deficit in players_needing_time:
                        if player_idx not in current_active:
                            # Find someone to swap out (prefer player with most time)
                            active_times = [(p, playing_times[p]) for p in current_active]
                            active_times.sort(key=lambda x: x[1], reverse=True)

                            current_active.remove(active_times[0][0])
                            current_active.add(player_idx)
                            break

                    buffer_active = list(current_active)

                buffer_bench = [p for p in range(self.num_players) if p not in buffer_active]

                # Create buffer block
                buffer_block = {
                    'start_time': buffer_start,
                    'end_time': buffer_end,
                    'duration': buffer_duration,
                    'section': section + 1
                }
                new_time_blocks.append(buffer_block)

                # Create buffer schedule entry
                buffer_key = f"{buffer_start}-{buffer_end}"
                new_schedule[buffer_key] = {
                    'active': buffer_active,
                    'bench': buffer_bench,
                    'start_time': buffer_start,
                    'end_time': buffer_end,
                    'duration': buffer_duration,
                    'section': section + 1
                }

                logger.info(f"Section {section + 1}: Created buffer block {buffer_duration:.1f}min with players {buffer_active} (multiplier {buffer_multiplier}x)")

        logger.info(f"Postprocessing complete (multiplier {buffer_multiplier}x): {len(new_time_blocks)} blocks created")
        return new_schedule, new_time_blocks


    def generate_random_schedule(self, time_blocks: List[Dict]) -> Dict:
        """Generate a random valid schedule."""
        schedule = {}

        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"

            # Randomly select players for this time block
            available_players = list(range(self.num_players))
            active_players = random.sample(available_players, self.players_in_field)
            bench_players = [p for p in available_players if p not in active_players]

            schedule[block_key] = {
                'active': active_players,
                'bench': bench_players,
                'start_time': block['start_time'],
                'end_time': block['end_time'],
                'duration': block['duration'],
                'section': block['section']
            }

        return schedule

    def calculate_schedule_score(self, schedule: Dict, time_blocks: List[Dict]) -> float:
        """Calculate the quality score of a schedule (lower is better)."""
        # Calculate playing time and bench blocks for each player
        playing_times = [0.0] * self.num_players
        bench_blocks = [0] * self.num_players
        substitution_counts = [0] * self.num_players

        previous_active = None

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

            # Count substitutions (when a player's status changes)
            if previous_active is not None:
                for player_idx in range(self.num_players):
                    was_active = player_idx in previous_active
                    is_active = player_idx in active_players
                    if was_active != is_active:
                        substitution_counts[player_idx] += 1

            previous_active = active_players

        # HARD CONSTRAINT: Reject schedules that are too unfair in playing time
        min_time = min(playing_times)
        max_time = max(playing_times)
        time_difference = max_time - min_time

        # Maximum allowed difference: 20% of average playing time or 3 minutes, whichever is larger
        avg_playing_time = sum(playing_times) / len(playing_times)
        max_allowed_difference = max(avg_playing_time * 0.20, 3.0)

        if time_difference > max_allowed_difference:
            # Heavily penalize unfair schedules - return very high score
            return 10000 + time_difference * 1000

        # Score components for fair schedules
        score = 0.0

        # 1. Playing time variance (reduced weight to balance with bench block fairness)
        time_variance = sum((pt - avg_playing_time) ** 2 for pt in playing_times) / len(playing_times)
        score += time_variance * 100

        # 2. Add penalty for maximum time difference (even within acceptable range)
        score += time_difference * 200

        # 3. HEAVILY weight bench block fairness (NEW)
        min_bench = min(bench_blocks)
        max_bench = max(bench_blocks)
        bench_difference = max_bench - min_bench
        score += bench_difference * 2000  # Heavy penalty for uneven bench blocks

        # 4. Bench block variance
        avg_bench = sum(bench_blocks) / len(bench_blocks)
        bench_variance = sum((bb - avg_bench) ** 2 for bb in bench_blocks) / len(bench_blocks)
        score += bench_variance * 1000

        # 5. Minimize variance in substitution counts (reduced weight)
        avg_subs = sum(substitution_counts) / len(substitution_counts)
        sub_variance = sum((sc - avg_subs) ** 2 for sc in substitution_counts) / len(substitution_counts)
        score += sub_variance * 25

        # 6. Penalize consecutive bench blocks (but don't reject entirely)
        for player_idx in range(self.num_players):
            player_bench_blocks = []
            player_active_blocks = []

            for block in time_blocks:
                block_key = f"{block['start_time']}-{block['end_time']}"
                if player_idx in schedule[block_key]['active']:
                    player_active_blocks.append(block['start_time'])
                else:
                    player_bench_blocks.append(block['start_time'])

            # Penalize consecutive bench blocks
            if len(player_bench_blocks) > 1:
                consecutive_penalty = 0
                for i in range(len(player_bench_blocks) - 1):
                    # Check if bench blocks are consecutive (next block immediately follows)
                    current_block_end = None
                    next_block_start = None

                    for block in time_blocks:
                        if block['start_time'] == player_bench_blocks[i]:
                            current_block_end = block['end_time']
                        if block['start_time'] == player_bench_blocks[i + 1]:
                            next_block_start = block['start_time']

                    # If blocks are consecutive, add penalty
                    if current_block_end == next_block_start:
                        consecutive_penalty += 500  # Moderate penalty instead of rejection

                score += consecutive_penalty

            # Penalize uneven distribution of active periods
            if len(player_active_blocks) > 1:
                # Calculate gaps between active periods
                gaps = [player_active_blocks[i+1] - player_active_blocks[i]
                       for i in range(len(player_active_blocks)-1)]
                if gaps:
                    gap_variance = sum((g - sum(gaps)/len(gaps)) ** 2 for g in gaps) / len(gaps)
                    score += gap_variance * 50  # Increased from 5 to 50

        return score

    def optimize_schedule(self, max_iterations: int = 30000) -> Tuple[Dict, List[Dict], float]:
        """Use Monte Carlo optimization to find the best schedule."""
        logger.info(f"Starting schedule optimization for game: {self.game.name}")
        logger.info(f"Game parameters - Players: {self.num_players}, In field: {self.players_in_field}, Game length: {self.game_length}min")

        time_blocks = self.calculate_time_blocks()
        logger.info(f"Generated {len(time_blocks)} time blocks")

        best_schedule = None
        best_score = float('inf')
        best_time_blocks = time_blocks
        valid_schedules = 0

        logger.info(f"Starting Monte Carlo optimization with {max_iterations} max iterations...")

        for iteration in range(max_iterations):
            # Generate random schedule
            candidate_schedule = self.generate_random_schedule(time_blocks)

            # Validate schedule
            if not self.validate_schedule(candidate_schedule, time_blocks):
                continue

            valid_schedules += 1

            # Calculate score
            score = self.calculate_schedule_score(candidate_schedule, time_blocks)

            # Keep if better
            if score < best_score:
                best_score = score
                best_schedule = candidate_schedule.copy()
                best_time_blocks = time_blocks

                # Calculate fairness metrics for logging
                playing_times = [0.0] * self.num_players
                for block in time_blocks:
                    block_key = f"{block['start_time']}-{block['end_time']}"
                    block_data = candidate_schedule[block_key]
                    for player_idx in block_data['active']:
                        playing_times[player_idx] += block_data['duration']

                min_time = min(playing_times)
                max_time = max(playing_times)
                time_diff = max_time - min_time

                logger.info(f"Iteration {iteration + 1}: New best score {score:.2f} - Time range: {min_time:.1f}-{max_time:.1f}min (diff: {time_diff:.1f}min)")

            # Log progress every 1000 iterations
            if (iteration + 1) % 1000 == 0:
                logger.info(f"Progress: {iteration + 1}/{max_iterations} iterations, current best score: {best_score:.2f}")

            # Early stopping if we find a very fair solution (time difference < 2 minutes)
            if best_score < 500:  # This means we found a fair schedule
                logger.info(f"Early stopping at iteration {iteration + 1} - fair schedule achieved (score: {best_score:.2f})")
                break

        logger.info(f"Optimization complete. Final score: {best_score:.2f} after {iteration + 1} iterations")
        logger.info(f"Total valid schedules generated: {valid_schedules}")

        # Test different rounding strategies for optimal fairness
        if best_schedule:
            logger.info("Testing different time rounding strategies...")
            try:
                best_schedule, best_time_blocks, best_score = self.test_rounding_strategies(best_schedule, best_time_blocks)
            except Exception as e:
                logger.error(f"Rounding strategy testing failed: {e}")

            # Track the absolute best schedule throughout all attempts
            absolute_best_schedule = best_schedule
            absolute_best_time_blocks = best_time_blocks
            absolute_best_score = best_score

            # Calculate playing time difference for original schedule
            original_playing_times = [0.0] * self.num_players
            for block in best_time_blocks:
                block_key = f"{block['start_time']}-{block['end_time']}"
                block_data = best_schedule[block_key]
                for player_idx in block_data['active']:
                    original_playing_times[player_idx] += block_data['duration']

            original_max_time = max(original_playing_times)
            original_min_time = min(original_playing_times)
            original_avg_time = sum(original_playing_times) / len(original_playing_times)
            original_diff_percentage = (original_max_time - original_min_time) / original_avg_time

            logger.info(f"Original Monte Carlo result: Score {best_score:.2f} - Time range: {original_min_time:.1f}-{original_max_time:.1f}min (diff: {(original_diff_percentage*100):.1f}%)")

            # Only try postprocessing if difference > 12%
            if original_diff_percentage > 0.12:
                logger.info(f"Playing time difference {(original_diff_percentage*100):.1f}% > 12%, trying postprocessing approaches...")

                # Try different buffer size multipliers
                buffer_multipliers = [1.0, 1.5, 2.0, 2.5]

                for multiplier in buffer_multipliers:
                    logger.info(f"Trying postprocessing with buffer multiplier {multiplier}x...")

                    try:
                        # Apply postprocessing with current multiplier
                        processed_schedule, processed_time_blocks = self.postprocess_for_playing_time_balance_with_multiplier(
                            best_schedule, best_time_blocks, multiplier)
                    except Exception as e:
                        logger.error(f"Postprocessing with multiplier {multiplier}x failed: {e}")
                        continue

                    # Calculate score for processed schedule
                    processed_score = self.calculate_schedule_score(processed_schedule, processed_time_blocks)

                    # Calculate fairness metrics
                    processed_playing_times = [0.0] * self.num_players
                    for block in processed_time_blocks:
                        block_key = f"{block['start_time']}-{block['end_time']}"
                        block_data = processed_schedule[block_key]
                        for player_idx in block_data['active']:
                            processed_playing_times[player_idx] += block_data['duration']

                    processed_min_time = min(processed_playing_times)
                    processed_max_time = max(processed_playing_times)
                    processed_time_diff = processed_max_time - processed_min_time

                    logger.info(f"Postprocessing {multiplier}x result: Score {processed_score:.2f} - Time range: {processed_min_time:.1f}-{processed_max_time:.1f}min (diff: {processed_time_diff:.1f}min)")

                    # Only use this postprocessed schedule if it has a better score than original Monte Carlo
                    if processed_score < best_score:
                        logger.info(f"Postprocessing {multiplier}x improved score from {best_score:.2f} to {processed_score:.2f} - ACCEPTING")
                        # Update absolute best if this is better
                        if processed_score < absolute_best_score:
                            absolute_best_schedule = processed_schedule
                            absolute_best_time_blocks = processed_time_blocks
                            absolute_best_score = processed_score
                            logger.info(f"New absolute best score: {absolute_best_score:.2f}")
                    else:
                        logger.info(f"Postprocessing {multiplier}x score {processed_score:.2f} worse than original {best_score:.2f} - REJECTING")

                # Final result is the absolute best we found
                final_schedule = absolute_best_schedule
                final_time_blocks = absolute_best_time_blocks
                final_score = absolute_best_score

            else:
                logger.info("Playing time difference ≤12%, no postprocessing needed")
                final_schedule = best_schedule
                final_time_blocks = best_time_blocks
                final_score = best_score

            # Calculate final fairness metrics for logging
            final_playing_times = [0.0] * self.num_players
            for block in final_time_blocks:
                block_key = f"{block['start_time']}-{block['end_time']}"
                block_data = final_schedule[block_key]
                for player_idx in block_data['active']:
                    final_playing_times[player_idx] += block_data['duration']

            final_min_time = min(final_playing_times)
            final_max_time = max(final_playing_times)
            final_time_diff = final_max_time - final_min_time

            logger.info(f"FINAL RESULT: Score {final_score:.2f} - Time range: {final_min_time:.1f}-{final_max_time:.1f}min (diff: {final_time_diff:.1f}min)")

            return final_schedule, final_time_blocks, final_score
        else:
            return best_schedule, time_blocks, best_score

    def validate_schedule(self, schedule: Dict, time_blocks: List[Dict]) -> bool:
        """Validate that a schedule meets all constraints."""
        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule[block_key]

            # Check correct number of active players
            if len(block_data['active']) != self.players_in_field:
                return False

            # Check no player is both active and benched
            active_set = set(block_data['active'])
            bench_set = set(block_data['bench'])
            if active_set.intersection(bench_set):
                return False

            # Check all players are accounted for
            all_players = active_set.union(bench_set)
            if len(all_players) != self.num_players:
                return False

        return True

    def create_schedule_objects(self, schedule_data: Dict, time_blocks: List[Dict], score: float):
        """Create Django model objects for the optimized schedule."""
        logger.info("Creating database objects for optimized schedule...")

        # Deactivate existing schedules for this game
        Schedule.objects.filter(game=self.game, is_active=True).update(is_active=False)

        # Get next version number
        latest_version = Schedule.objects.filter(game=self.game).aggregate(
            max_version=models.Max('version')
        )['max_version'] or 0
        next_version = latest_version + 1

        # Create new schedule version
        schedule_obj = Schedule.objects.create(
            game=self.game,
            version=next_version,
            is_active=True,
            time_blocks=time_blocks,
            player_assignments=schedule_data,
            optimization_score=score,
            iterations_run=10000
        )

        logger.info(f"Created new schedule object version {next_version}")

        # Create time blocks for this schedule version
        logger.info(f"Creating {len(time_blocks)} time block objects...")

        for block in time_blocks:
            block_key = f"{block['start_time']}-{block['end_time']}"
            block_data = schedule_data[block_key]

            TimeBlock.objects.create(
                schedule=schedule_obj,
                start_time=block['start_time'],
                end_time=block['end_time'],
                duration=block['duration'],
                section=block['section'],
                active_players=block_data['active'],
                bench_players=block_data['bench']
            )

        # Create player objects for this schedule version
        logger.info(f"Creating {len(self.players)} player objects...")

        for idx, player_name in enumerate(self.players):
            # Calculate stats for this player
            total_playing_time = 0
            bench_blocks = 0  # Count how many blocks player is on bench

            for block in time_blocks:
                block_key = f"{block['start_time']}-{block['end_time']}"
                block_data = schedule_data[block_key]

                is_active = idx in block_data['active']
                if is_active:
                    total_playing_time += block_data['duration']
                else:
                    bench_blocks += 1

            substitution_count = bench_blocks

            Player.objects.create(
                schedule=schedule_obj,
                name=player_name,
                position_index=idx,
                total_playing_time=total_playing_time,
                total_bench_time=self.game_length - total_playing_time,
                substitution_count=substitution_count
            )

        logger.info("Schedule creation completed successfully!")
        return schedule_obj