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
# Authors: Chenxiong Qi <cqi@redhat.com>

from flask import Flask, Response
from prometheus_client import CONTENT_TYPE_LATEST

from message_tagging_service.monitor import generate_metrics_report

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return Response('Welcome to Message-Tagging-Service (aka MTS)')


@app.route('/monitor/metrics', methods=['GET'])
def metrics():
    return Response(generate_metrics_report(),
                    content_type=CONTENT_TYPE_LATEST)
