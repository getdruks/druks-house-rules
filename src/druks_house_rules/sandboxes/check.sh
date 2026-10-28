#!/bin/sh
# The package at the app's version, on PATH for the run's user.
set -eu
as_root=""
[ "$(id -u)" -eq 0 ] || as_root="sudo -E"
$as_root apt-get update
$as_root apt-get install -y --no-install-recommends git python3 python3-venv
$as_root python3 -m venv /opt/druks-house-rules
$as_root /opt/druks-house-rules/bin/pip install --quiet \
    "git+https://github.com/getdruks/druks-house-rules@v0.0.4"
$as_root ln -sf /opt/druks-house-rules/bin/druks-house-rules /usr/local/bin/druks-house-rules
