# -*- coding: utf-8 -*-
#
# Message tagging service is an event-driven service to tag build.
# Copyright (C) 2019  Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Original authors: Filip Valder

# Copied from https://pagure.io/monitor-flask-sqlalchemy/blob/master/f/monitor.py
# Customized for MTS, e.g. database metrics are removed because MTS does not
# uses a database.

import os
import tempfile

from prometheus_client import CollectorRegistry
from prometheus_client import ProcessCollector
from prometheus_client import multiprocess
from prometheus_client import Counter
from prometheus_client import generate_latest

if not os.environ.get('prometheus_multiproc_dir'):
    dir_name = tempfile.mkdtemp(prefix='mts-prometheus-multiproc-')
    os.environ.setdefault('prometheus_multiproc_dir', dir_name)

registry = CollectorRegistry()
ProcessCollector(registry=registry)
multiprocess.MultiProcessCollector(registry)

failed_tag_build_requests_counter = Counter(
    'failed_tag_build_requests',
    'The number of failed tagBuild API calls.',
    registry=registry
)

matched_module_builds_counter = Counter(
    'matched_module_builds',
    'The number of module builds which are matched rule(s) to be tagged.',
    registry=registry
)

messaging_tx_failed_counter = Counter(
    'messaging_tx_failed',
    'The number of errors occurred during sending message to bus.',
    registry=registry
)


def generate_metrics_report():
    return generate_latest(registry)
