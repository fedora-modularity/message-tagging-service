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

import koji
import requests
import yaml

from message_tagging_service import conf


def retrieve_modulemd_content(name, stream, version, context):
    """Retrieve and return modulemd.txt from Koji/Brew

    :param str name: module's name.
    :param str stream: module's stream.
    :param str version: module's version.
    :param str context: module's context.
    :return: modulemd content.
    :rtype: str
    """
    koji_config = koji.read_config(conf.koji_profile)
    url = (f'{koji_config["topurl"]}/{name}/{stream}/{version}.{context}'
           f'/files/module/modulemd.txt')
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content


def read_rule_defs():
    """Read rule definiations from configured rule file

    :return: a rule file is a YAML file, which is read, parsed and returned as
        a mapping.
    :rtype: dict
    """
    with open(conf.rule_file, 'r') as f:
        return yaml.safe_load(f)
