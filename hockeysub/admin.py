from django.contrib import admin
from .models import Game, Schedule, Player, TimeBlock


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_players', 'players_in_field', 'game_length', 'created_at')
    list_filter = ('sections', 'substitution_length', 'paired_subbing', 'created_at')
    search_fields = ('name', 'player_names')
    readonly_fields = ('created_at',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('game', 'version', 'is_active', 'optimization_score', 'iterations_run', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'schedule', 'total_playing_time', 'substitution_count')
    list_filter = ('schedule__game',)
    search_fields = ('name', 'schedule__game__name')


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'start_time', 'end_time', 'duration', 'section')
    list_filter = ('section', 'schedule__game')
    readonly_fields = ('duration',)
