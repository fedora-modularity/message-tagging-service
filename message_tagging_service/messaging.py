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

from message_tagging_service import conf

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
    return handler(topic, msg)


def _fedmsg_publish(topic, msg):
    # fedmsg doesn't really need access to conf, however other backends do
    import fedmsg
    config = conf.messaging_backends['fedmsg']
    if conf.dry_run:
        logger.info("DRY-RUN: fedmsg.publish('%s', msg=%s, modname='%s')",
                    topic, msg, config['service'])
    else:
        return fedmsg.publish(topic, msg=msg, modname=config['service'])


def _rhmsg_publish(topic, msg):
    """Send message to Unified Message Bus

    :param str topic: the topic where message will be sent to, e.g.
        ``build.tagged``.
    :param dict msg: the message that will be sent.
    """
    import proton
    from rhmsg.activemq.producer import AMQProducer

    config = conf.messaging_backends['rhmsg']
    producer_config = {
        'urls': config['brokers'],
        'certificate': config['certificate'],
        'private_key': config['private_key'],
        'trusted_certificates': config['ca_cert'],
    }
    with AMQProducer(**producer_config) as producer:
        prefix = config['topic_prefix'].rstrip('.')
        topic = f'{prefix}.{topic}'
        producer.through_topic(topic)

        outgoing_msg = proton.Message()
        outgoing_msg.body = json.dumps(msg)
        if conf.dry_run:
            logger.info('DRY-RUN: AMQProducer.send(%s) through topic %s',
                        outgoing_msg, topic)
        else:
            producer.send(outgoing_msg)


_messaging_backends = {
    'fedmsg': {
        'publish': _fedmsg_publish
    },
    'rhmsg': {
        'publish': _rhmsg_publish
    }
}
