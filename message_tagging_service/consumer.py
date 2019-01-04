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

from message_tagging_service.mts_config import mts_conf
from message_tagging_service import tagging_service
from message_tagging_service.utils import read_rule_defs

logger = logging.getLogger(__name__)


class MTSConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = mts_conf.messaging_topics
    config_key = 'mts-consumer'

    def __init__(self, *args, **kwargs):
        super(MTSConsumer, self).__init__(*args, **kwargs)
        self.rule_defs = read_rule_defs()

    def consume(self, msg):
        logger.debug('Got message: %r', msg)

        event_msg = msg['msg']
        if event_msg['state_name'] != 'ready':
            logger.info('Skip module build %s as it is not in ready state yet.',
                        event_msg['koji_tag'])
            return

        tagging_service.handle(self.rule_defs, event_msg)
