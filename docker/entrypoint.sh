#!/usr/bin/env bash

script_dir=$(dirname $(realpath $0))

$script_dir/install-ca.sh && exec fedmsg-hub-3 &
gunicorn-3 --log-level debug -b 0.0.0.0:8080 --workers 4 message_tagging_service.web:app
