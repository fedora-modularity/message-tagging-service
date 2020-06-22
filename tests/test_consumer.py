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

import fedora_messaging.api
import json
import os
import pytest
import requests.exceptions
import yaml

from mock import patch, Mock
from message_tagging_service.consumer import run
from message_tagging_service import conf, consumer

try:
    import rhmsg
except ImportError:
    rhmsg = None


test_data_dir = os.path.join(os.path.dirname(__file__), 'data')


class Container(object):
    """
    Fake proton.Container to just call on_message in order to test the consume
    callback function.
    """

    def __init__(self, handler):
        self.handler = handler

    def run(self):
        event = Mock()
        self.handler.on_message(event)


class ReceiverHandler(object):
    """Fake ReceiverHandler in order to call consumer.consume function"""

    fake_msg_body = ''

    def __init__(self, urls, address, callback, **kwargs):
        self.callback = callback
        self.result = Mock()

    def on_message(self, event):
        import proton
        fake_msg = proton.Message(
            body=ReceiverHandler.fake_msg_body,
            id='msg-id-01',
            address='topic://VirtualTopic.eng.app.event',
        )
        self.callback(fake_msg, data=None)


class TestConsumer(object):
    """Test consumer method is able to handle two different type of messages

    There are two types of messages, one is coming from fedora-messaging, and
    another one is coming UMB.
    """

    @pytest.mark.skipif(rhmsg is None, reason='rhmsg is not installed.')
    # Test code working with rhmsg library
    @patch.object(conf, 'messaging_backend', new='rhmsg')
    # Patch rhmsg to not connect broker actually and just call the consume
    # callback inside on_message event.
    @patch('rhmsg.activemq.consumer.ReceiverHandler', new=ReceiverHandler)
    @patch('rhmsg.activemq.consumer.Container', new=Container)
    @patch('rhmsg.activemq.consumer.SSLDomain')
    @patch.object(consumer.tagging_service, 'handle')
    @patch('requests.get')
    def test_skip_if_rule_file_is_empty(self, get, handle, SSLDomain):
        ReceiverHandler.fake_msg_body = json.dumps({}).encode()
        get.return_value.text = '---'
        run()
        handle.assert_not_called()

    @pytest.mark.skipif(rhmsg is None, reason='rhmsg is not installed.')
    @patch.object(conf, 'messaging_backend', new='rhmsg')
    @patch('rhmsg.activemq.consumer.ReceiverHandler', new=ReceiverHandler)
    @patch('rhmsg.activemq.consumer.Container', new=Container)
    @patch('rhmsg.activemq.consumer.SSLDomain')
    @patch('message_tagging_service.consumer.tagging_service.handle')
    @patch('requests.get')
    def test_handle_umb_message(self, get, handle, SSLDomain):
        mbs_event_msg = {
            'name': 'python',
            'stream': '2.7',
            'version': '1',
            'context': 'c1',
        }
        ReceiverHandler.fake_msg_body = json.dumps(mbs_event_msg).encode()

        with open(os.path.join(test_data_dir, 'mts-test-rules.yaml'), 'r') as f:
            rules_content = f.read()
        get.return_value.text = rules_content

        run()

        handle.assert_called_once_with(
            yaml.safe_load(rules_content), mbs_event_msg)

    @pytest.mark.parametrize('msg_body', [{
        'name': 'python',
        'stream': '2.7',
        'version': '1',
        'context': 'c1',
        'state_name': 'ready',
    }, {}])
    @patch('message_tagging_service.consumer.tagging_service.handle')
    @patch('requests.get')
    def test_handle_fedora_messaging_message(self, get, handle, msg_body):
        with open(os.path.join(test_data_dir, 'mts-test-rules.yaml'), 'r') as f:
            rules_content = f.read()

        get.return_value.text = rules_content

        def api_consume(callback):
            msg = fedora_messaging.api.Message(msg_body)
            callback(msg)

        with patch('fedora_messaging.api.consume', new=api_consume):
            run()

        if msg_body:
            handle.assert_called_once_with(yaml.safe_load(rules_content), msg_body)
        else:
            # In case event message is empty, MTS stops handling the message.
            handle.assert_not_called()

    @pytest.mark.skipif(rhmsg is None, reason='rhmsg is not installed.')
    def test_umb_message(self):
        from message_tagging_service.consumer import UMBMessage
        import proton
        msg = UMBMessage(proton.Message(
            body=json.dumps({'name': 'modulea'}),
            id='msg-id-01',
            address='topic://VirtualTopic.event',
        ))
        assert 'msg-id-01' == msg.id
        assert {'name': 'modulea'} == msg.body
        assert 'topic://VirtualTopic.event' == msg.topic

    def test_raise_error_if_specified_messaging_backend_is_unknown(self):
        with patch.object(conf, 'messaging_backend', new='xxxxxx'):
            with pytest.raises(ValueError, match='Unknown messaging backend: .+'):
                run()

    @patch('message_tagging_service.consumer.tagging_service.handle')
    @patch('requests.get')
    def test_consume_terminates_if_fail_to_read_rules_from_remote(self, get, handle):
        get.side_effect = requests.exceptions.HTTPError
        consumer.consume(Mock())
        handle.assert_not_called()

    @patch('message_tagging_service.consumer.tagging_service.handle')
    @patch('requests.get')
    def test_mts_should_log_and_dont_terminate_handle_function(self, get, handle):
        with open(os.path.join(test_data_dir, 'mts-test-rules.yaml'), 'r') as f:
            rules_content = f.read()
        get.return_value.text = rules_content

        # Set any error to make handle function fail
        handle.side_effect = IndexError

        msg = fedora_messaging.api.Message(body={
            'name': 'modulea',
            'stream': '10',
            'version': '20200107111030',
            'context': 'c1',
            'state_name': 'ready',
        })

        with patch.object(consumer, 'logger') as logger:
            consumer.consume(msg)

            args, _ = logger.exception.call_args
            assert "Failed to handle message" in args[0]
            args, _ = logger.info.call_args
            assert 'Continue to handle next MBS message ...' == args[0]

    @pytest.mark.skipif(rhmsg is None, reason='rhmsg is not installed.')
    @patch.object(conf, 'messaging_backend', new='rhmsg')
    @patch('rhmsg.activemq.consumer.ReceiverHandler', new=ReceiverHandler)
    @patch('rhmsg.activemq.consumer.Container', new=Container)
    @patch('rhmsg.activemq.consumer.SSLDomain')
    @patch('message_tagging_service.consumer.tagging_service.handle')
    @patch('requests.get')
    def test_log_error_if_umb_message_body_is_invalid(self, get, handle, SSLDomain):
        with open(os.path.join(test_data_dir, 'mts-test-rules.yaml'), 'r') as f:
            rules_content = f.read()
        get.return_value.text = rules_content
        ReceiverHandler.fake_msg_body = 'non-JSON message body'

        with patch.object(consumer, 'logger') as logger:
            run()

            args, _ = logger.error.call_args_list[0]
            assert 'Cannot decode message body: non-JSON message body' == args[0]
            args, _ = logger.error.call_args_list[1]
            assert args[0].startswith('Reason:')

    def test_ignore_scratch_build(self):
        msg = fedora_messaging.api.Message(body={'name': 'modulea', 'scratch': True})

        with patch.object(consumer, 'logger') as logger:
            consumer.consume(msg)
            args, _ = logger.warning.call_args
            assert 'Ignore scratch build' in args[0]

    def test_ignore_filtered_out_by_states(self):
        msg = fedora_messaging.api.Message(body={'name': 'modulea',
                                                 'state_name': 'init'})

        with patch.object(consumer, 'logger') as logger:
            consumer.consume(msg)
            args, _ = logger.warning.call_args
            assert 'The message with build_state:' in args[0]
