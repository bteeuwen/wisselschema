import logging

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Game, Schedule
from .forms import GameConfigForm
from .scheduler import ScheduleOptimizer

logger = logging.getLogger(__name__)


def register(request):
    if request.user.is_authenticated:
        return redirect('hockeysub:index')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created! Welcome, {user.username}.')
            return redirect('hockeysub:index')
    else:
        form = UserCreationForm()
    return render(request, 'hockeysub/register.html', {'form': form})


@login_required
def index(request):
    recent_games = Game.objects.order_by('-created_at')[:5]
    return render(request, 'hockeysub/index.html', {'recent_games': recent_games})


@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameConfigForm(request.POST)
        if form.is_valid():
            game = form.save()
            messages.success(request, f'Game "{game.name}" created successfully!')
            return redirect('hockeysub:generate_schedule', game_id=game.id)
    else:
        form = GameConfigForm()

    return render(request, 'hockeysub/create_game.html', {'form': form})


@login_required
def edit_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if request.method == 'POST':
        form = GameConfigForm(request.POST, instance=game)
        if form.is_valid():
            form.save()
            messages.success(request, f'Game "{game.name}" updated successfully!')
            return redirect('hockeysub:game_detail', game_id=game.id)
    else:
        form = GameConfigForm(instance=game)

    return render(request, 'hockeysub/edit_game.html', {'form': form, 'game': game})


@login_required
def generate_schedule(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if request.method == 'POST':
        try:
            optimizer = ScheduleOptimizer(game)
            schedule_data, time_blocks, score = optimizer.optimize_schedule()

            if schedule_data:
                schedule = optimizer.create_schedule_objects(schedule_data, time_blocks, score)
                messages.success(request, f'Schedule generated with optimization score: {score:.2f}')
                return redirect('hockeysub:view_schedule', game_id=game.id)
            else:
                messages.error(request, 'Failed to generate a valid schedule. Please check your game parameters.')

        except Exception as e:
            logger.error('Error generating schedule for game %s: %s', game_id, str(e))
            messages.error(request, 'An error occurred while generating the schedule. Please try again.')

    return render(request, 'hockeysub/generate_schedule.html', {'game': game})


@login_required
def view_schedule(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    try:
        schedule = game.get_active_schedule()
        if not schedule:
            raise Schedule.DoesNotExist
        time_blocks = schedule.blocks.all().order_by('start_time')
        players = schedule.players.all().order_by('position_index')

        # Create schedule matrix for table visualization
        schedule_matrix = []
        for player in players:
            row = {
                'player': player,
                'blocks': [],
                'total_playing_time': player.total_playing_time,
                'total_bench_time': player.total_bench_time,
                'substitutions': player.substitution_count
            }

            for block in time_blocks:
                is_active = player.position_index in block.active_players
                row['blocks'].append({
                    'block': block,
                    'is_active': is_active,
                    'status': 'active' if is_active else 'bench'
                })

            schedule_matrix.append(row)

        # Calculate column totals (should always equal players_in_field)
        column_totals = []
        for block in time_blocks:
            total_active = len(block.active_players)
            column_totals.append({
                'block': block,
                'total_active': total_active,
                'is_valid': total_active == game.players_in_field
            })

        context = {
            'game': game,
            'schedule': schedule,
            'time_blocks': time_blocks,
            'players': players,
            'schedule_matrix': schedule_matrix,
            'column_totals': column_totals,
        }

        return render(request, 'hockeysub/view_schedule.html', context)

    except Schedule.DoesNotExist:
        messages.error(request, 'No schedule found for this game. Please generate one first.')
        return redirect('hockeysub:generate_schedule', game_id=game.id)


@login_required
def view_schedule_version(request, game_id, version):
    game = get_object_or_404(Game, id=game_id)
    schedule = get_object_or_404(Schedule, game=game, version=version)

    time_blocks = schedule.blocks.all().order_by('start_time')
    players = schedule.players.all().order_by('position_index')

    # Create schedule matrix for table visualization
    schedule_matrix = []
    for player in players:
        row = {
            'player': player,
            'blocks': [],
            'total_playing_time': player.total_playing_time,
            'total_bench_time': player.total_bench_time,
            'substitutions': player.substitution_count
        }

        for block in time_blocks:
            is_active = player.position_index in block.active_players
            row['blocks'].append({
                'block': block,
                'is_active': is_active,
                'status': 'active' if is_active else 'bench'
            })

        schedule_matrix.append(row)

    # Calculate column totals (should always equal players_in_field)
    column_totals = []
    for block in time_blocks:
        total_active = len(block.active_players)
        column_totals.append({
            'block': block,
            'total_active': total_active,
            'is_valid': total_active == game.players_in_field
        })

    context = {
        'game': game,
        'schedule': schedule,
        'time_blocks': time_blocks,
        'players': players,
        'schedule_matrix': schedule_matrix,
        'column_totals': column_totals,
        'is_historical': not schedule.is_active,
    }

    return render(request, 'hockeysub/view_schedule.html', context)


@login_required
def activate_schedule_version(request, game_id, version):
    game = get_object_or_404(Game, id=game_id)
    schedule = get_object_or_404(Schedule, game=game, version=version)

    if request.method == 'POST':
        # Deactivate all other schedules
        Schedule.objects.filter(game=game).update(is_active=False)
        # Activate this schedule
        schedule.is_active = True
        schedule.save()

        messages.success(request, f'Schedule version {version} is now active!')
        return redirect('hockeysub:view_schedule', game_id=game.id)

    return redirect('hockeysub:game_detail', game_id=game.id)


@login_required
def game_list(request):
    games = Game.objects.order_by('-created_at')
    return render(request, 'hockeysub/game_list.html', {'games': games})


@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    has_schedule = game.has_schedule()
    active_schedule = game.get_active_schedule()
    all_schedules = game.schedules.all().order_by('-version')
    return render(request, 'hockeysub/game_detail.html', {
        'game': game,
        'has_schedule': has_schedule,
        'active_schedule': active_schedule,
        'all_schedules': all_schedules
    })
