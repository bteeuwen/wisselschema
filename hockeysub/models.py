from django.db import models


class Game(models.Model):
    SUBSTITUTION_LENGTH_CHOICES = [
        ('short', 'Short'),
        ('long', 'Long'),
    ]

    SUBSTITUTION_MODE_CHOICES = [
        ('standard', 'Standard (multiple subs per section)'),
        ('zen', 'Zen (one substitution per quarter)'),
    ]

    name = models.CharField(max_length=100, default="Hockey Game")
    players_in_field = models.IntegerField(default=5)
    total_players = models.IntegerField(default=8)
    game_length = models.IntegerField(default=50, help_text="Game length in minutes")
    sections = models.IntegerField(default=2, help_text="Number of game sections (halves)")
    substitution_length = models.CharField(
        max_length=5,
        choices=SUBSTITUTION_LENGTH_CHOICES,
        default='long'
    )
    substitution_mode = models.CharField(
        max_length=10,
        choices=SUBSTITUTION_MODE_CHOICES,
        default='standard'
    )
    paired_subbing = models.BooleanField(default=True)
    custom_block_duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Custom block duration in minutes (e.g., 3.5 for 3:30). If not set, automatic block sizing is used."
    )
    player_names = models.TextField(
        blank=True,
        help_text="Comma or space separated player names"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.total_players} players"

    def get_player_list(self):
        if self.player_names.strip():
            names = [name.strip() for name in self.player_names.replace(',', ' ').split() if name.strip()]
            return names[:self.total_players]
        else:
            return [f"Player {i+1}" for i in range(self.total_players)]

    def calculate_total_playing_time(self):
        return self.players_in_field * self.game_length

    def calculate_playing_time_per_player(self):
        total_time = self.calculate_total_playing_time()
        return total_time / self.total_players

    def get_active_schedule(self):
        """Get the currently active schedule for this game."""
        return self.schedules.filter(is_active=True).first()

    def has_schedule(self):
        """Check if this game has any schedules."""
        return self.schedules.exists()


class Schedule(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='schedules')
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    time_blocks = models.JSONField(default=list)
    player_assignments = models.JSONField(default=dict)
    optimization_score = models.FloatField(null=True, blank=True)
    iterations_run = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['game', 'version']
        ordering = ['-version']

    def __str__(self):
        return f"Schedule v{self.version} for {self.game.name}"

    def get_time_blocks(self):
        return self.time_blocks

    def get_player_assignments(self):
        return self.player_assignments


class Player(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=50)
    position_index = models.IntegerField()
    total_playing_time = models.FloatField(default=0)
    total_bench_time = models.FloatField(default=0)
    substitution_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['position_index']
        unique_together = ['schedule', 'position_index']

    def __str__(self):
        return f"{self.name} (Schedule v{self.schedule.version})"


class TimeBlock(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='blocks')
    start_time = models.FloatField()
    end_time = models.FloatField()
    duration = models.FloatField()
    section = models.IntegerField(help_text="Which game section this block belongs to")
    active_players = models.JSONField(default=list)
    bench_players = models.JSONField(default=list)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"Block {self.start_time}-{self.end_time}min (Section {self.section})"
