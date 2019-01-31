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

import fedmsg.consumers
import logging
import requests

from message_tagging_service import conf
from message_tagging_service import tagging_service
from message_tagging_service.utils import read_rule_defs
from message_tagging_service import messaging

logger = logging.getLogger(__name__)


class ModuleBuildStateChangeConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = conf.consumer_topics['module-build-state-change-consumer']
    config_key = 'module-build-state-change-consumer'

    def consume(self, msg):
        logger.debug('Got message: %r', msg)

        event_msg = msg['body']['msg']
        if event_msg['state_name'] != 'ready':
            logger.info('Skip module build %s as it is not in ready state yet.',
                        event_msg['koji_tag'])
            return

        try:
            rule_defs = read_rule_defs()
        except requests.exceptions.HTTPError:
            logger.exception('Failed to retrieve rules content.')
        else:
            # For an empty yaml file, YAML returns None. So, if the remote rule
            # file is empty, catch this case and skip to handle the tag.
            if rule_defs is not None:
                tagging_service.handle(rule_defs, event_msg)


class BuildTagConsumer(fedmsg.consumers.FedmsgConsumer):
    """Consumer messages on build is tagged

    BuildTagConsumer handles two different format of messages for Fedora and
    Brew. For Fedora, the message is a simple mapping containing tag name and
    build info. Whereas, the message sent from Brew contains those information in
    individual mapping. This consumer handles both of them to get build NVR and
    tag name.
    """

    topic = conf.consumer_topics['build-tag-consumer']
    config_key = 'build-tag-consumer'

    def consume(self, msg):
        logger.debug('Got message: %r', msg)

        event_msg = msg['body']['msg']

        user = event_msg['user']
        if isinstance(user, dict):
            # Handle Brew format.
            user = user['name']
            nvr = event_msg['build']['nvr']
            tag = event_msg['tag']['name']
        else:
            # The Fedora case.
            nvr = '{name}-{version}-{release}'.format(**event_msg)
            tag = event_msg['tag']

        if user != conf.koji_mts_username:
            logger.debug('Build %s is not tagged by MTS. Skip to notify.', nvr)
            return

        messaging.publish('build.tagged', {
            'nvr': nvr,
            'tag': tag,
        })
