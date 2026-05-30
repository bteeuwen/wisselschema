from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divides the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def minutes_to_mmss(value):
    """Convert decimal minutes to mm:ss format."""
    try:
        total_seconds = int(float(value) * 60)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "0:00"

@register.simple_tag
def block_relative_time(blocks, current_block):
    """Return 'start-end' label relative to the block's section start (e.g. 0:00-5:00)."""
    section = current_block.section
    section_start = min(b.start_time for b in blocks if b.section == section)
    rel_start = current_block.start_time - section_start
    rel_end = current_block.end_time - section_start

    def fmt(minutes):
        total_seconds = int(float(minutes) * 60)
        m = total_seconds // 60
        s = total_seconds % 60
        return f"{m}:{s:02d}"

    return f"{fmt(rel_start)}-{fmt(rel_end)}"

@register.simple_tag
def section_letter(blocks, current_block):
    """Generate section letter (1a, 1b, 2a, 2b, etc.) for the current block."""
    section = current_block.section
    # Count how many blocks in this section come before the current block
    blocks_in_section_before = 0
    for block in blocks:
        if block.section == section and block.start_time < current_block.start_time:
            blocks_in_section_before += 1

    # Convert to letter (a=0, b=1, c=2, etc.)
    letter = chr(ord('a') + blocks_in_section_before)
    return f"{section}{letter}"