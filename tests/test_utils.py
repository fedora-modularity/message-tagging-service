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

import pytest

from mock import patch, Mock
from message_tagging_service import utils
from requests.exceptions import HTTPError


class TestRetrieveModulemdContent(object):
    """Test utils.retrieve_modulemd_content"""

    @patch.object(utils.conf, 'mbs_api_url', new='https://mbs.local/')
    @patch('requests.get')
    def test_retrieve_the_content(self, get):
        get.return_value = Mock(status_code=200)
        fake_modulemd = 'modulemd conent'
        get.return_value.json.return_value = {
            'modulemd': fake_modulemd,
        }

        modulemd = utils.retrieve_modulemd_content(1)

        assert fake_modulemd == modulemd
        get.assert_called_once_with(
            'https://mbs.local/module-builds/1',
            params={'verbose': True})

    @patch.object(utils.conf, 'mbs_api_url', new='https://mbs.local/')
    @patch('requests.get')
    def test_raise_error_if_failed_to_get_module(self, get):
        get.return_value.raise_for_status.side_effect = HTTPError('error')
        pytest.raises(HTTPError, utils.retrieve_modulemd_content, 1)
