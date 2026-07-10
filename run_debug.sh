#!/usr/bin/env bash
set -euo pipefail
export PYTHONFAULTHANDLER=1
export QT_LOGGING_RULES='qt.qpa.wayland.textinput=false'
python -X faulthandler main.py
