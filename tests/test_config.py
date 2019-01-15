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

from mock import patch
from message_tagging_service import config

test_config = os.path.join(os.path.dirname(__file__),
                           'data',
                           'config.py')


class TestGetConfigFile(object):

    @patch.dict('os.environ', values={'MTS_CONFIG_FILE': test_config})
    def test_use_specified_config_file(self):
        conf = config.load_config()
        assert conf.test

    @patch.dict('os.environ', values={'MTS_DEV': '1'})
    def test_use_config_from_source_code(self):
        conf = config.load_config()
        assert 'DevConfiguration' == conf.__class__.__name__

    @patch.dict('os.environ', clear=True)
    @patch.object(config, 'running_tests', new=False)
    @patch('importlib.machinery')
    def test_use_installed_config(self, machinery):
        conf = config.load_config()

        machinery.SourceFileLoader.assert_called_once_with(
            'mts_conf',
            '/etc/mts/config.py')

        loader = machinery.SourceFileLoader.return_value
        mod = loader.load_module.return_value
        assert conf == mod.BaseConfiguration.return_value
