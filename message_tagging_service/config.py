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
# Authors: Chenxiong Qi <cqi@redhat.com>, Valerij Maljulin <vmaljuli@redhat.com>


import importlib.machinery
import os
import sys


running_tests = any('py.test' in arg for arg in sys.argv)


class Config:
    """
    This class allows to instanciate configuration. It has 3 types of properties
        (starting from the least priority):
    - default properties - set as members of dictionary __defaults to this class
        (common for all instances)
    - class properties - properties of configuration class from configuration file (__conf_class)
    - overrided properties - properties changed in runtime
    All properties could be read using instance.name or instance['name'] form.
    Setting a new value to instance['name'] will override the value of property
        (but only for this particular instance)
    """
    _defaults = {
        'build_state_msg_filter': ['ready', 'done']
    }

    def __init__(self, profile=None, config_file=None, config_class=None):
        """
        Initialize config, read sets configuration class from configuration file
        :param profile: to be set to config file name
        :type profile: str
        :param config_file: force configuration file path (overrides profile setting if present)
        :type config_file: str
        :param config_class: force class name in configuration file
        :type config_class: str
        """
        self._conf_class = None  # set lazily later
        self._overrides = {}
        self.load_new_config(profile, config_file, config_class)

    @staticmethod
    def get_config_file(profile):
        """
        Trying to get information about config file. Lookup through:
        1. Value of MTS_CONFIG_FILE environmental variable
        2. Try development configuration if MTS_DEV is set or in tests mode
        3. Default configuration path /etc/mts/config.py
        :param profile: profile name to be a part of config file
        :type profile: str
        :return: file path
        :rtype: str
        """
        config_file = os.environ.get('MTS_CONFIG_FILE')
        if config_file:
            return config_file
        elif 'MTS_DEV' in os.environ or running_tests:
            # Use {project root directory}/conf/config.py
            return os.path.realpath(
                os.path.join(os.path.dirname(__file__), '..', 'conf', 'config.py'))
        else:
            if profile:
                return f'/etc/mts/config.{profile}.py'
            else:
                return '/etc/mts/config.py'

    @staticmethod
    def get_config_class_name():
        """
        Determine a class name according to running mode
        :return: class name
        :rtype: str
        """
        if running_tests:
            return 'TestConfiguration'
        elif 'MTS_DEV' in os.environ:
            return 'DevConfiguration'
        else:
            return 'BaseConfiguration'

    def update(self, new_val_dict=None, **kwargs):
        """
        Support update configuration with the dictionary or keyword arguments
        :param new_val_dict: dictionary containing new configuration values
        :type new_val_dict: dict
        :param kwargs: keyword-styled new configuration values
        :return:
        """
        if new_val_dict and isinstance(new_val_dict, dict):
            self._overrides.update(new_val_dict)
        self._overrides.update(kwargs)

    def reset(self):
        """
        Reset overrides
        :return:
        """
        self._overrides.clear()

    def load_new_config(self, profile=None, config_file=None, config_class=None,
                        keep_overrides=False):
        """
        Reloads a base file from a config class
        :param profile: to be set to config file name
        :type profile: str
        :param config_file: force configuration file path (overrides profile setting if present)
        :type config_file: str
        :param config_class: force class name in configuration file
        :type config_class: str
        :param keep_overrides: keep overrided values if True
        :type keep_overrides: bool
        :return:
        """
        if not config_file:
            config_file = self.get_config_file(profile=profile)
        loader = importlib.machinery.SourceFileLoader('mts_conf', config_file)
        mod = loader.load_module()
        if not config_class:
            config_class = self.get_config_class_name()
        if getattr(mod, config_class, None) is not None:
            self._conf_class = getattr(mod, config_class)
        else:
            raise AttributeError(f'Configuration class {config_class} '
                                 f'not found in configuration file {config_file}')
        if not keep_overrides:
            self._overrides.clear()

    def __getattr__(self, item):
        """
        Allows to access configuration parameters as instance.item
        :param item: item name
        :type item: str
        :return: item value
        """
        return self[item]

    def __getitem__(self, item):
        """
        Allows to access configuration parameters as instance['item']
        :param item: item name
        :return: item value
        """
        # check overrides first:
        if item in self._overrides:
            return self._overrides[item]

        # trying configuration class then
        try:
            return getattr(self._conf_class, item)
        except AttributeError:
            pass

        # fallback to defaults if any
        if item in self._defaults:
            return self._defaults[item]

        raise KeyError(f'{self._conf_class.__name__} has no config {item}.')

    def __setitem__(self, key, value):
        """
        Value can be overrided using instance['key'] = value
        :param key: item name
        :type key: str
        :param value: new value
        :return: None
        """
        self._overrides[key] = value

    @property
    def conf_class(self):
        return self._conf_class
