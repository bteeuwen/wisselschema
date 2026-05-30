from django import forms
from .models import Game


class GameConfigForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = [
            'name', 'players_in_field', 'total_players', 'game_length',
            'sections', 'substitution_mode', 'substitution_length', 'paired_subbing', 'custom_block_duration', 'player_names'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter game name'
            }),
            'players_in_field': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'total_players': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'game_length': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 200
            }),
            'sections': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'substitution_mode': forms.Select(attrs={
                'class': 'form-control'
            }),
            'substitution_length': forms.Select(attrs={
                'class': 'form-control'
            }),
            'paired_subbing': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'custom_block_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.25,
                'max': 60,
                'step': 0.25,
                'placeholder': 'e.g., 3.5 for 3:30 minutes (optional)'
            }),
            'player_names': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter player names separated by commas or spaces (optional)'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        players_in_field = cleaned_data.get('players_in_field')
        total_players = cleaned_data.get('total_players')
        custom_block_duration = cleaned_data.get('custom_block_duration')
        game_length = cleaned_data.get('game_length')
        sections = cleaned_data.get('sections')

        if players_in_field and total_players:
            if players_in_field >= total_players:
                raise forms.ValidationError(
                    "Number of players in field must be less than total number of players."
                )

        # Validate custom block duration
        if custom_block_duration is not None and game_length and sections:
            section_length = game_length / sections
            if custom_block_duration >= section_length:
                raise forms.ValidationError(
                    f"Custom block duration ({custom_block_duration} min) must be smaller than section length ({section_length} min)."
                )
            if custom_block_duration < 0.25:
                raise forms.ValidationError(
                    "Custom block duration must be at least 0.25 minutes (15 seconds)."
                )

        return cleaned_data

    def clean_player_names(self):
        player_names = self.cleaned_data.get('player_names', '')
        total_players = self.cleaned_data.get('total_players', 0)

        if player_names.strip():
            names = [name.strip() for name in player_names.replace(',', ' ').split() if name.strip()]
            if len(names) > total_players:
                raise forms.ValidationError(
                    f"You provided {len(names)} names but specified {total_players} total players."
                )

        return player_names