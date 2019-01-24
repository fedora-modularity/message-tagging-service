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


class TestConfig(object):

    @patch.dict('os.environ', values={'MTS_CONFIG_FILE': test_config})
    def test_use_specified_config_file(self):
        conf = config.Config()
        assert conf.test

    @patch.dict('os.environ', values={'MTS_DEV': '1'})
    def test_test_config(self):
        conf = config.Config()
        assert 'TestConfiguration' == conf.conf_class.__name__

    @patch.dict('os.environ', values={'MTS_DEV': '1'})
    @patch.object(config, 'running_tests', new=False)
    def test_dev_config(self):
        conf = config.Config()
        assert 'DevConfiguration' == conf.conf_class.__name__

    @patch.dict('os.environ', clear=True)
    @patch.object(config, 'running_tests', new=False)
    @patch('importlib.machinery')
    def test_use_installed_config(self, machinery):
        conf = config.Config()

        machinery.SourceFileLoader.assert_called_once_with(
            'mts_conf',
            '/etc/mts/config.py')

        loader = machinery.SourceFileLoader.return_value
        mod = loader.load_module.return_value
        assert conf.conf_class == mod.BaseConfiguration

    @patch.dict('os.environ', clear=True)
    @patch.object(config, 'running_tests', new=False)
    @patch('importlib.machinery')
    def test_config_profile(self, machinery):
        profile_name = 'abc123'
        conf = config.Config(profile=profile_name)

        machinery.SourceFileLoader.assert_called_once_with(
            'mts_conf',
            f'/etc/mts/config.{profile_name}.py')

        loader = machinery.SourceFileLoader.return_value
        mod = loader.load_module.return_value
        assert conf.conf_class == mod.BaseConfiguration

    @patch.dict('os.environ', values={'MTS_CONFIG_FILE': test_config})
    def test_overriding(self):
        new_value = 'dddeeefff123'
        test_val2 = 3
        test_val3 = 10
        conf = config.Config()
        import tests.data.config as conf_data
        assert conf.test_val1 == conf_data.TestConfiguration.test_val1
        assert conf['test_val1'] == conf_data.TestConfiguration.test_val1
        conf['test_val1'] = new_value
        assert conf.test_val1 == new_value
        assert conf['test_val1'] == new_value
        conf.update({'test_val2': test_val2})
        conf.update(test_val3=test_val3)
        assert conf.test_val2 == test_val2
        assert conf.test_val3 == test_val3
        conf.reset()
        assert conf.test_val1 == conf_data.TestConfiguration.test_val1
