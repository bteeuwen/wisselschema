#!/bin/bash

# Wisselschema Generator - Quick Run Script
# Usage: ./run.sh [options]
# Example: ./run.sh --team D1 --keeper Casper --absent "Chester,Faber"

# Default configuration
TEAM="D1"
KEEPER="Casper"
ABSENT="Chester"
SECTIONS=4

# Activate virtual environment and run
venv/bin/python generate_schema.py \
    --team "$TEAM" \
    --keeper "$KEEPER" \
    --absent "$ABSENT" \
    --sections "$SECTIONS" \
    "$@"
