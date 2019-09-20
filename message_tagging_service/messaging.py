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

import logging
import json

from message_tagging_service import conf, monitor

logger = logging.getLogger(__name__)


def publish(topic, msg):
    """
    Publish a single message to a given backend, and return

    :param str topic: the topic of the message (e.g. module.state.change)
    :param dict msg: the message contents of the message (typically JSON)
    :return: the value returned from underlying backend "send" method.
    """
    backend = conf.messaging_backend
    try:
        handler = _messaging_backends[backend]['publish']
    except KeyError:
        raise KeyError(f'No messaging backend found for {backend}')
    try:
        return handler(topic, msg)
    except Exception:
        monitor.messaging_tx_failed_counter.inc()
        logger.exception('Failed to send message to topic %s: %s', topic, msg)


def _fedora_messaging_publish(topic, msg):
    from fedora_messaging import api, message

    if conf.dry_run:
        logger.info(
            'DRY-RUN: send message to fedora-messaging, topic: %s, msg: %s',
            topic, msg)
    else:
        fm_msg = message.Message(topic=topic, body=msg)
        logger.debug('Send message: %s', fm_msg)
        api.publish(fm_msg)


def _rhmsg_publish(topic, msg):
    """Send message to Unified Message Bus

    :param str topic: the topic where message will be sent to, e.g.
        ``build.tagged``.
    :param dict msg: the message that will be sent.
    """
    import proton
    from rhmsg.activemq.producer import AMQProducer

    producer_config = {
        'urls': conf.rhmsg_brokers,
        'certificate': conf.rhmsg_certificate,
        'private_key': conf.rhmsg_private_key,
        'trusted_certificates': conf.rhmsg_ca_cert,
    }
    with AMQProducer(**producer_config) as producer:
        topic = f'{conf.rhmsg_topic_prefix.rstrip(".")}.{topic}'
        producer.through_topic(topic)

        outgoing_msg = proton.Message()
        outgoing_msg.body = json.dumps(msg)
        if conf.dry_run:
            logger.info('DRY-RUN: AMQProducer.send(%s) through topic %s',
                        outgoing_msg, topic)
        else:
            logger.debug('Send message: %s', outgoing_msg)
            producer.send(outgoing_msg)


_messaging_backends = {
    'fedora-messaging': {
        'publish': _fedora_messaging_publish
    },
    'rhmsg': {
        'publish': _rhmsg_publish
    }
}
