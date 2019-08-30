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

import json
import pytest

from message_tagging_service import messaging
from mock import patch

try:
    import rhmsg
except ImportError:
    rhmsg = None


class TestMessaging(object):

    @patch.object(messaging.conf, 'messaging_backend', new='fedora-messaging')
    @patch('fedora_messaging.api.publish')
    @patch('fedora_messaging.message.Message')
    def test_send_via_fedora_messaging(self, Message, publish):
        messaging.publish('build.tagged', {'build_id': 1})

        Message.assert_called_once_with(topic='build.tagged', body={'build_id': 1})

        outgoing_msg = Message.return_value
        publish.assert_called_once_with(outgoing_msg)

    @pytest.mark.skipif(not rhmsg, reason='Library rhmsg is not available.')
    @patch.object(messaging.conf, 'messaging_backend', new='rhmsg')
    @patch.object(messaging.conf, 'rhmsg_brokers', new=['amqps://broker1/', 'amqps://broker2/'])
    @patch.object(messaging.conf, 'rhmsg_certificate', new='/path/to/certificate')
    @patch.object(messaging.conf, 'rhmsg_private_key', new='/path/to/private_key')
    @patch.object(messaging.conf, 'rhmsg_ca_cert', new='/path/to/ca_cert')
    @patch.object(messaging.conf, 'rhmsg_topic_prefix', new='VirtualTopic.eng.mts.')
    @patch('proton.Message')
    @patch('rhmsg.activemq.producer.AMQProducer')
    def test_send_via_rhmsg(self, AMQProducer, Message):
        msg = {'koji_tag': 'module-a-1-1-c1'}
        messaging.publish('build.tagged', msg)

        config = {
            'urls': ['amqps://broker1/', 'amqps://broker2/'],
            'certificate': '/path/to/certificate',
            'private_key': '/path/to/private_key',
            'trusted_certificates': '/path/to/ca_cert',
        }
        AMQProducer.assert_called_once_with(**config)
        producer = AMQProducer.return_value.__enter__.return_value
        producer.through_topic.assert_called_once_with('VirtualTopic.eng.mts.build.tagged')

        Message.return_value.body = json.dumps(msg)
        producer.send.assert_called_once_with(Message.return_value)

    @patch.object(messaging.conf, 'messaging_backend', new='anothercool')
    def test_no_backend_handler_is_found(self):
        with pytest.raises(KeyError):
            messaging.publish('topic', {})
