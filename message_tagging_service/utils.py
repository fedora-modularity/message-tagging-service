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

import os
import requests
import yaml
import logging

from message_tagging_service import conf

logger = logging.getLogger(__name__)


def load_module_md(module_build_id):
    """Load corresponding module metadata of a specific module build

    For handling the rule match easily, this function also inject some
    necessary module build properties into the loaded module metadata
    mapping.

    :param int module_build_id: module build ID.
    :return: a mapping representing the module metadata.
    :rtype: dict
    """
    api_url = conf.mbs_api_url.rstrip('/')
    resp = requests.get(f'{api_url}/module-builds/{module_build_id}', params={
        'verbose': True
    })
    resp.raise_for_status()
    module_build = resp.json()
    modulemd = yaml.safe_load(module_build['modulemd'])
    modulemd['data']['scratch'] = module_build['scratch']
    return modulemd


def read_rule_defs():
    """Read rule definiations from configured rule file

    :return: a rule file is a YAML file, which is read, parsed and returned as
        a mapping.
    :rtype: dict
    """
    r = requests.get(conf.rules_file_url)
    r.raise_for_status()
    return yaml.safe_load(r.text)


def is_file_readable(filename):
    return os.path.exists(filename) and os.access(filename, os.R_OK)
