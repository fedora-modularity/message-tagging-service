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
import logging
import requests

from message_tagging_service import conf
from message_tagging_service import tagging_service
from message_tagging_service.utils import read_rule_defs

logger = logging.getLogger(__name__)


class UMBMessage(object):
    """Representing a message received from rhmsg message bus

    :param msg: the message object received from underlying rhmsg message bus.
    :type msg: ``proton.Message``
    """

    def __init__(self, msg):
        self._orig_msg = msg
        self._body = json.loads(msg.body)

    @property
    def id(self):
        return self._orig_msg.id

    @property
    def topic(self):
        return self._orig_msg.address

    @property
    def body(self):
        return self._body

    def __repr__(self):
        return "{}(id={}, topic={}, body={})".format(
            self.__class__.__name__, repr(self.id), repr(self.topic), repr(self.body)
        )


def consume(msg):
    """Do the work to tag build if it matches a rule

    :param msg: the message got from message bus.
    :type msg: a Message object implementing interfaces to access message body
        at least.
    """

    mbs_msg = msg.body
    if not mbs_msg:
        logger.error('Cannot find out the embedded MBS message from received '
                     'message %r.', msg)
        return

    if mbs_msg.get('scratch'):
        logger.warning('Ignore scratch build %s', mbs_msg)
        return

    build_state = mbs_msg.get('state_name')
    if build_state not in conf.build_state_msg_filter:
        logger.warning('The message with build_state: %s is ignored.', build_state)
        return

    try:
        rule_defs = read_rule_defs()
    except requests.exceptions.HTTPError:
        logger.exception('Failed to retrieve rules content.')
        return

    nsvc = '{name}:{stream}:{version}:{context}'.format(**mbs_msg)

    # For an empty yaml file, YAML returns None. So, if the remote rule
    # file is empty, catch this case and skip to handle the tag.
    if rule_defs is None:
        logger.warning(
            'Ignore module build %s as no rule is defined in rule file.', nsvc)
    else:
        try:
            logger.info('Start to handle build: %s', nsvc)
            tagging_service.handle(rule_defs, mbs_msg)
        except:  # noqa
            logger.exception(f'Failed to handle message {mbs_msg}')
            logger.info('Continue to handle next MBS message ...')


def fedora_messaging_backend():
    """
    Launch consumer backend based on fedora-messaging to consume message from
    Fedora infra RabbitMQ message bus

    Refer to config file mts.toml for details of how the consumer is configured
    to receive messages from fedora-messaging.
    """
    from fedora_messaging import api
    api.consume(consume)


def rhmsg_backend():
    """Launch consumer backend based on rhmsg to consume message from UMB"""
    from rhmsg.activemq.consumer import AMQConsumer

    def _consumer_wrapper(msg, data=None):
        """Wrap UMB message in a message object

        fedora-messaging passes a message object rather than a raw dict into
        consumer function, but rhmsg does pass a dict instead. This wrapper
        makes it easier to handle message in a unified way in function
        ``consume``.

        :param msg: a proton.Message object represeting received message.
        :param data: any data passed from caller calling ``consumer.consume``.
        """
        logger.debug('Received message: %r', msg)
        try:
            consume(UMBMessage(msg))
        except json.JSONDecodeError as e:
            logger.error(f'Cannot decode message body: {msg.body}')
            logger.error(f'Reason: {str(e)}')

    consumer = AMQConsumer(
        urls=conf.rhmsg_brokers,
        certificate=conf.rhmsg_certificate,
        private_key=conf.rhmsg_private_key,
        trusted_certificates=conf.rhmsg_ca_cert,
    )

    consumer.consume(
        conf.rhmsg_queue, callback=_consumer_wrapper,
        subscription_name=conf.rhmsg_subscription_name)


def run():
    """The entrypoint of MTS to run specific consumer backend

    Config file has config to indicate which consumer backend to run.
    """
    if conf.messaging_backend == 'rhmsg':
        rhmsg_backend()
    elif conf.messaging_backend == 'fedora-messaging':
        fedora_messaging_backend()
    else:
        raise ValueError(f'Unknown messaging backend: {conf.messaging_backend}')
