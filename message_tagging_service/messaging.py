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


def kafka_client_config():
    """Build common connection kwargs for KafkaProducer and KafkaConsumer.

    Only the options that are configured are included so that unused auth
    material (e.g. SASL credentials when using plain SSL) is left at the
    kafka-python defaults.

    :return: keyword arguments accepted by both ``KafkaProducer`` and
        ``KafkaConsumer``.
    :rtype: dict
    """
    config = {
        'bootstrap_servers': conf.kafka_bootstrap_servers,
        'security_protocol': conf.kafka_security_protocol,
    }
    if conf.kafka_sasl_mechanism:
        config['sasl_mechanism'] = conf.kafka_sasl_mechanism
    if conf.kafka_sasl_username:
        config['sasl_plain_username'] = conf.kafka_sasl_username
    if conf.kafka_sasl_password:
        config['sasl_plain_password'] = conf.kafka_sasl_password
    if conf.kafka_ssl_cafile:
        config['ssl_cafile'] = conf.kafka_ssl_cafile
    if conf.kafka_ssl_certfile:
        config['ssl_certfile'] = conf.kafka_ssl_certfile
    if conf.kafka_ssl_keyfile:
        config['ssl_keyfile'] = conf.kafka_ssl_keyfile
    return config


def _kafka_publish(topic, msg):
    """Send message to the IT Managed Kafka service

    :param str topic: the topic where message will be sent to, e.g.
        ``build.tagged``. The configured ``kafka_topic_prefix`` is prepended to
        build the full topic name.
    :param dict msg: the message that will be sent.
    """
    from kafka import KafkaProducer

    full_topic = f'{conf.kafka_topic_prefix.rstrip(".")}.{topic}'

    if conf.dry_run:
        logger.info(
            'DRY-RUN: send message to kafka, topic: %s, msg: %s',
            full_topic, msg)
        return

    producer = KafkaProducer(
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        **kafka_client_config())
    try:
        logger.debug('Send message to topic %s: %s', full_topic, msg)
        future = producer.send(full_topic, value=msg)
        # Block until the broker acknowledges the message so that any delivery
        # error is raised here and counted by the caller's failure handler.
        future.get(timeout=conf.kafka_send_timeout)
    finally:
        producer.flush()
        producer.close()


_messaging_backends = {
    'fedora-messaging': {
        'publish': _fedora_messaging_publish
    },
    'rhmsg': {
        'publish': _rhmsg_publish
    },
    'kafka': {
        'publish': _kafka_publish
    }
}
