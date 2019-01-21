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
# Authors: Chenxiong Qi

import queue

from mock import MagicMock
from mock import patch

from message_tagging_service import consumer


class TestConsumer(object):

    def new_consumer(self):
        hub = MagicMock()
        hub.config = {}
        hub.config['mts-consumer'] = True
        hub.config['validate_signatures'] = False
        c = consumer.MTSConsumer(hub)
        c.incoming = queue.Queue()
        return c

    @patch.object(consumer, 'read_rule_defs')
    @patch.object(consumer.tagging_service, 'handle')
    def test_consume_msg(self, handle, read_rule_defs):
        consumer = self.new_consumer()

        event_msg = {'state_name': 'ready'}
        consumer.consume({'body': {'msg': event_msg}})

        handle.assert_called_once_with(read_rule_defs.return_value, event_msg)

    @patch.object(consumer, 'read_rule_defs')
    @patch.object(consumer.tagging_service, 'handle')
    def test_ignore_message_if_not_ready(self, handle, read_rule_defs):
        consumer = self.new_consumer()
        consumer.consume({'body': {'msg': {
            'state_name': 'done',
            'koji_tag': 'module-modulea-1-1-c1',
        }}})

        handle.assert_not_called()

    @patch('requests.get')
    @patch.object(consumer.tagging_service, 'handle')
    def test_skip_if_rule_file_is_empty(self, handle, get):
        get.return_value.text = '---'

        consumer = self.new_consumer()
        consumer.consume({'body': {'msg': {
            'state_name': 'ready',
            'koji_tag': 'module-modulea-1-1-c1',
        }}})

        handle.assert_not_called()
