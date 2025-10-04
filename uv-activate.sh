#!/bin/sh
uv_directory=$(uv sync --dry-run --script yeeval.py 2>&1 \
    | grep 'Would use script environment at: ' \
    | sed 's/Would use script environment at: //')

uv_activate_file="$uv_directory/bin/activate"

[ -e "$uv_activate_file" ] || { echo "$uv_activate_file not found" >&2; exit 1; }

. "$uv_activate_file"
