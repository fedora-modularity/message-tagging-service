#!/usr/bin/env bash
set -euo pipefail

script_dir=$(dirname $(realpath $0))

$script_dir/install-ca.sh
gunicorn-3 --log-level ${GUNICORN_LOG_LEVEL:-info} -b 0.0.0.0:8080 message_tagging_service.web:app &
exec python3 -m message_tagging_service
