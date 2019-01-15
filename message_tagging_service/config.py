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


import importlib.machinery
import os
import sys


running_tests = any('py.test' in arg for arg in sys.argv)


def get_config_file():
    config_file = os.environ.get('MTS_CONFIG_FILE')
    if config_file:
        return config_file
    elif 'MTS_DEV' in os.environ or running_tests:
        # Use {project root directory}/conf/config.py
        return os.path.realpath(
            os.path.join(os.path.dirname(__file__), '..', 'conf', 'config.py'))
    else:
        return '/etc/mts/config.py'


def load_config():
    config_file = get_config_file()
    loader = importlib.machinery.SourceFileLoader('mts_conf', config_file)
    mod = loader.load_module()
    if 'MTS_DEV' in os.environ:
        return mod.DevConfiguration()
    else:
        return mod.BaseConfiguration()
