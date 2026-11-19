#!/bin/sh
# Patch français non officiel de Neo Junk City (Linux, Steam Deck)
exec python3 "$(dirname "$0")/vf.py" install "$@"
