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

from hockeysub.forms import GameConfigForm
from hockeysub.models import Game

def test_form_fields():
    """Test that the GameConfigForm includes the custom_block_duration field"""

    print("TESTING WEB FORM INTEGRATION")
    print("=" * 50)

    # Create a blank form
    form = GameConfigForm()

    print("Available form fields:")
    for field_name in form.fields.keys():
        field = form.fields[field_name]
        print(f"  - {field_name}: {field.__class__.__name__}")
        if hasattr(field, 'help_text') and field.help_text:
            print(f"    Help: {field.help_text}")

    # Check if custom_block_duration is in the form
    if 'custom_block_duration' in form.fields:
        field = form.fields['custom_block_duration']
        print(f"\n✅ custom_block_duration field found!")
        print(f"   Widget: {field.widget.__class__.__name__}")
        print(f"   Required: {field.required}")
        if hasattr(field.widget, 'attrs'):
            print(f"   Widget attributes: {field.widget.attrs}")
    else:
        print(f"\n❌ custom_block_duration field NOT found!")
        return False

    # Test form validation with custom block duration
    print(f"\n" + "=" * 50)
    print("TESTING FORM VALIDATION")

    # Test valid data
    valid_data = {
        'name': 'Test Game',
        'players_in_field': 5,
        'total_players': 7,
        'game_length': 50,
        'sections': 2,
        'substitution_length': 'short',
        'paired_subbing': True,
        'custom_block_duration': 3.5,
        'player_names': ''
    }

    form = GameConfigForm(data=valid_data)
    if form.is_valid():
        print("✅ Form validation with custom_block_duration = 3.5: PASSED")
        # Create game to test it saves correctly
        game = form.save()
        print(f"✅ Game saved with custom_block_duration: {game.custom_block_duration}")
        game.delete()  # Clean up
    else:
        print("❌ Form validation with custom_block_duration = 3.5: FAILED")
        print(f"   Errors: {form.errors}")

    # Test invalid data (block duration too large)
    invalid_data = valid_data.copy()
    invalid_data['custom_block_duration'] = 30  # Larger than section length (25min)

    form = GameConfigForm(data=invalid_data)
    if not form.is_valid() and 'custom_block_duration' in str(form.errors):
        print("✅ Form validation correctly rejects oversized custom_block_duration")
    else:
        print("❌ Form validation should have rejected oversized custom_block_duration")
        if form.errors:
            print(f"   Errors: {form.errors}")

    # Test without custom block duration (should be valid)
    no_custom_data = valid_data.copy()
    del no_custom_data['custom_block_duration']

    form = GameConfigForm(data=no_custom_data)
    if form.is_valid():
        print("✅ Form validation without custom_block_duration: PASSED")
        game = form.save()
        print(f"✅ Game saved without custom_block_duration: {game.custom_block_duration}")
        game.delete()  # Clean up
    else:
        print("❌ Form validation without custom_block_duration: FAILED")
        print(f"   Errors: {form.errors}")

    return True

if __name__ == "__main__":
    test_form_fields()