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
# Authors: Troy Dawson
#          Chenxiong Qi <cqi@redhat.com>

import koji
import logging
import re
import requests
import yaml

from message_tagging_service import messaging
from message_tagging_service import conf
from message_tagging_service.utils import retrieve_modulemd_content

logger = logging.getLogger(__name__)


class RuleMatch(object):
    """Result of :meth:`RuleDef.match`

    A rule match object can be evaluated as truth or false. Hence, it is doable
    like this::

        match = RuleDef.match(...)
        if match: ...
        if not match: ...

    :param bool matched: indicate if rule definition is matched.
    :param str dest_tag: the formatted destination tag from rule definition
        item ``destination``.
    """

    def __init__(self, matched, dest_tag=None):
        self.matched = matched
        self.dest_tag = dest_tag

    def __bool__(self):
        return self.matched


class RuleDef(object):
    """Represent a rule definition

    Refer to https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md
    """

    def __init__(self, data):
        for name in ['id', 'type', 'destinations']:
            if name not in data:
                raise ValueError(f'Rule definition does not have property {name}.')

        self.data = data

        self._property_matches = []
        self._regex_has_named_group = []

    @property
    def id(self):
        return self.data['id']

    @property
    def description(self):
        return self.data['description']

    @property
    def type(self):
        return self.data['type']

    @property
    def rule(self):
        """Return property rule of definition

        Note that, a rule definition may or may not have match criteria in rule
        property. If no rule is defined, None will be returned.
        """
        # YAML allows to read a empty section like:
        # - name: xxx
        #   rule:
        #   destination: xxx
        # In this case, parsed YAML dict has key/value: {'rule': None}
        return self.data.get('rule')

    @property
    def destinations(self):
        return self.data['destinations']

    def find_diff_value(self, regex, mmd_property_value):
        """Match a property value with expected regular expression

        :param str regex: the regular expression to try to match property value.
        :param mmd_property_value: property value to match. It could be a single
            value, or a list of values for example the dependencies like
            ``{'dependencies': {'buildrequires': {'platform': ['f28']}}}``.
        :type mmd_property_value: list or str
        :return: True if given regular expression matches the single value, or
            match one of the list of values. If not match anything, False is
            returned.
        :rtype: bool
        """
        if isinstance(mmd_property_value, list):
            check_values = mmd_property_value
        else:
            check_values = [mmd_property_value]
        for value in check_values:
            match = re.search(regex, value)
            if match:
                if match.groupdict():
                    self._regex_has_named_group.append((regex, value))
                return True
        return False

    def find_diff_list(self, match_candidates, mmd_property_value):
        """Find out if module property value matches one of values defined in rule

        :param match_candidates: list of regular expressions in rule definition
            to check if one of them could match the corresponding property
            value in modulemd.
        :type match_candidates: list[str]
        :param str mmd_property_value: modulemd's property value to check.
        :return: True if match, otherwise False.
        :rtype: bool
        """
        logger.debug('Checking %s against regular expressions %r',
                     mmd_property_value, match_candidates)
        for regex in match_candidates:
            if self.find_diff_value(regex, mmd_property_value):
                return True
        return False

    def find_diff_dict(self, rule_dict, check_dict):
        """Check if rule matches modulemd values recursively for dict type

        Modulemd dependencies is a dict, which could be::

            {
                'dependencies': {
                    'buildrequires': {'platform': ['f29']},
                    'requires': {'platform': ['f29']}
                }
            }

        When rule definition has a rule like::

            {'dependencies': {'requires': {'platform': r'f\d+'}}}

        this function has to check if rule matches the module's runtime
        requirement platform f29.

        :param dict rule_dict:
        :param dict check_dict:
        :return: True if match, otherwise False.
        :rtype: bool
        """  # noqa
        match = True
        for key, value in rule_dict.items():
            new_check_dict = check_dict.get(key)
            if new_check_dict is None:
                logger.debug("'%s' is not found in module", key)
                return False
            if isinstance(value, dict):
                match = self.find_diff_dict(value, new_check_dict)
            elif isinstance(value, list):
                match = self.find_diff_list(value, new_check_dict)
            else:
                match = self.find_diff_value(value, new_check_dict)
            if not match:
                # As long as one of rule criteria does not match module
                # property, the whole dict rule match fails.
                break
        return match

    def match(self, modulemd):
        """Check if a rule definition matches a module

        The match implementation follows
        https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md

        :param dict modulemd: a mapping parsed from modulemd YAML file.
        :return: a RuleMatch object to indicate whether modulemd matches the rule.
        :rtype: :class:`RuleMatch`
        """
        if self.rule is None:
            logger.debug(
                'No rule criteria is defined. Build will be tagged to %s',
                self.destinations)
            return RuleMatch(True, self.destinations)

        for property, expected in self.rule.items():
            # Both scratch and development have default value to compare with
            # expected in rule definition.

            if property == 'scratch':
                mmd_value = modulemd['data'].get("scratch", False)
                if expected == mmd_value:
                    logger.debug('Rule/Value: %s: %s. Matched.', property, expected)
                    self._property_matches.append(True)
                else:
                    logger.debug('Rule/Value: %s: %s. Not Matched. Real value: %s',
                                 property, expected, mmd_value)
                    self._property_matches.append(False)

            elif property == 'development':
                mmd_value = modulemd["data"].get("development", False)
                if expected == mmd_value:
                    logger.debug('Rule/Value: %s: %s. Matched.', property, expected)
                    self._property_matches.append(True)
                else:
                    logger.debug('Rule/Value: %s: %s. Not Matched. Real value: %s',
                                 property, expected, mmd_value)
                    self._property_matches.append(False)

            else:
                # Now check rules that have regex
                value_to_check = modulemd["data"].get(property)
                if value_to_check is None:
                    logger.debug('%s is not match. Modulemd does not have %s', property, property)
                    self._property_matches.append(False)

                elif isinstance(expected, dict):
                    if self.find_diff_dict(expected, value_to_check[0]):
                        logger.debug('Rule/Value: %s: %r. Matched.', property, expected)
                        self._property_matches.append(True)
                    else:
                        logger.debug('Rule/Value: %s: %r. Not Matched. Real value: %r',
                                     property, expected, value_to_check[0])
                        self._property_matches.append(False)

                elif isinstance(expected, list):
                    if self.find_diff_list(expected, value_to_check):
                        logger.debug('Rule/Value: %s: %r. Matched.', property, expected)
                        self._property_matches.append(True)
                    else:
                        logger.debug('Rule/Value: %s: %r. Not Matched. Real value: %s',
                                     property, expected, value_to_check)
                        self._property_matches.append(False)

                else:
                    if self.find_diff_value(expected, str(value_to_check)):
                        logger.debug('Rule/Value: %s: %r. Matched.', property, expected)
                        self._property_matches.append(True)
                    else:
                        logger.debug('Rule/Value: %s: %r. Not Matched.', property, expected)
                        self._property_matches.append(False)

        if all(self._property_matches):
            if self._regex_has_named_group:
                formatted_dest_tags = [
                    re.sub(regex, self.destinations, mmd_property_value)
                    for regex, mmd_property_value in self._regex_has_named_group
                ]
                return RuleMatch(True, formatted_dest_tags[-1])
            else:
                return RuleMatch(True, self.destinations)
        else:
            return RuleMatch(False)


def tag_build(nvr, dest_tags):
    """Tag build with specific tags

    Calling Koji API to tag build might fail, however successful tagged tag will
    be returned and to log the failed tag operation.

    :param str nvr: build NVR.
    :param dest_tags: tag names.
    :type dest_tags: list[str]
    :return: tag names which are tagged to build successfully.
    :rtype: list[str]
    """
    tagged_tags = []
    koji_config = koji.read_config(conf.koji_profile)
    koji_session = koji.ClientSession(koji_config['server'])
    koji_session.krb_login()
    for tag in dest_tags:
        try:
            if conf.dry_run:
                logger.info("DRY-RUN: koji_session.tagBuild('%s', '%s')", tag, nvr)
            else:
                koji_session.tagBuild(tag, nvr)
        except Exception:
            logger.exception('Failed to tag %s to build %s', tag, nvr)
        else:
            tagged_tags.append(tag)
    koji_session.logout()
    return tagged_tags


def handle(rule_defs, event_msg):
    this_name = event_msg["name"]
    this_stream = event_msg["stream"]
    this_version = event_msg["version"]
    this_context = event_msg["context"]
    nsvc = f"{this_name}-{this_stream}-{this_version}-{this_context}"

    try:
        modulemd = yaml.safe_load(retrieve_modulemd_content(event_msg['id']))
    except requests.exceptions.HTTPError as e:
        logger.exception(f'Failed to retrieve modulemd for {nsvc}: {str(e)}')

        # Continue to wait for and handle next module build which moves
        # to ready state.
        return

    logger.debug('Modulemd file is downloaded and parsed.')

    rule_matches = []
    for i, rule_def in enumerate(rule_defs, 1):
        rd = RuleDef(rule_def)
        logger.info('[%s] Checking rule definition: %s', i, rd.id)
        match = rd.match(modulemd)
        if match:
            rule_matches.append(match)
            logger.info('[%d] Rule definition: Matched.', i)
        else:
            logger.info('[%d] Rule definition: Not Matched.', i)

    if not rule_matches:
        logger.info('Module build %s does not match any rule.', nsvc)
        return

    stream = this_stream.replace('-', '_')
    nvr = f'{this_name}-{stream}-{this_version}.{this_context}'
    dest_tags = [item.dest_tag for item in rule_matches]
    logger.info('Tag build %s with tag(s) %s', nvr, ', '.join(dest_tags))

    tagged_tags = tag_build(nvr, dest_tags)

    if not tagged_tags:
        logger.warning(
            'None of tag(s) %r is tagged to build %s. Skip to send message.',
            dest_tags, nvr)
        return

    messaging.publish('build.tagged', {
        'build': {
            'id': event_msg['id'],
            'name': this_name,
            'stream': this_stream,
            'version': this_version,
            'context': this_context,
        },
        'nvr': nvr,
        'destination_tags': tagged_tags,
    })
