# -*- coding: utf-8 -*-

# This has been optimized for python3
#   print and urllib are different from python2

import fedmsg
import koji
import logging
import re
import requests
import yaml

from operator import truth

from message_tagging_service.mts_config import mts_conf
from message_tagging_service.utils import retrieve_modulemd_content

logger = logging.getLogger(__name__)

# Import fedmsg config file
config = fedmsg.config.load_config([], None)
config['mute'] = True
config['timeout'] = 0
config['topic'] = "org.fedoraproject.prod.mbs.module.state.change"


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
        logger.debug('Checking regex %s against %r', regex, check_values)
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
        """
        match = True
        for key, value in rule_dict.items():
            new_check_dict = check_dict.get(key)
            if new_check_dict is None:
                logger.warning('%s is not found in module', key)
                return False
            if isinstance(value, dict):
                logger.debug('Checking: %s', key)
                match = self.find_diff_dict(value, new_check_dict)
            elif isinstance(value, list):
                logger.debug('Checking: %s', key)
                match = self.find_diff_list(value, new_check_dict)
            else:
                logger.debug('Checking: %s', key)
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
            logger.info('No rule criteria is defined. Build will be tagged to %s',
                        self.destinations)
            return RuleMatch(True, self.destinations)

        for property, expected in self.rule.items():
            logger.info('Rule/Value: %s : %s', property, expected)

            # Both scratch and development have default value to compare with
            # expected in rule definition.

            if property == 'scratch':
                mmd_value = modulemd['data'].get("scratch", False)
                if expected == mmd_value:
                    self._property_matches.append(True)
                else:
                    logger.debug('scratch is not matched. Expected: %s. Value in modulemd: %s',
                                 expected, mmd_value)
                    self._property_matches.append(False)

            elif property == 'development':
                mmd_value = modulemd["data"].get("development", False)
                if expected == mmd_value:
                    self._property_matches.append(True)
                else:
                    logger.debug('development is not matched. Expected: %s. Value in modulemd: %s',
                                 expected, mmd_value)
                    self._property_matches.append(False)

            else:
                # Now check rules that have regex
                value_to_check = modulemd["data"].get(property)
                if value_to_check is None:
                    logger.info('%s is not match. Modulemd does not have %s', property, property)
                    self._property_matches.append(False)

                elif isinstance(expected, dict):
                    logger.debug('Rule has a dictionary: %r', expected)
                    if self.find_diff_dict(expected, value_to_check[0]):
                        self._property_matches.append(True)
                    else:
                        logger.info('%s is not matched.', property)
                        self._property_matches.append(False)

                elif isinstance(expected, list):
                    logger.debug('Rule has a list: %r', expected)
                    if self.find_diff_list(expected, value_to_check):
                        self._property_matches.append(True)
                    else:
                        logger.info('% is not matched.', property)
                        self._property_matches.append(False)

                else:
                    if self.find_diff_value(expected, str(value_to_check)):
                        self._property_matches.append(True)
                    else:
                        logger.info('%s is not matched.', property)
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
    koji_config = koji.read_config(mts_conf['koji_profile'])
    koji_session = koji.ClientSession(koji_config['server'])
    koji_session.krb_login()
    for tag in dest_tags:
        try:
            koji_session.tagBuild(tag, nvr)
        except Exception:
            logger.exception('Failed to tag %s to build %s', tag, nvr)
    koji_session.logout()


def main():
    # Import message-tagger config file
    with open(mts_conf['rule_file'], 'r') as f:
        rule_defs = yaml.safe_load(f)

    for name, endpoint, topic, msg in fedmsg.tail_messages(**config):
        this_message = msg["msg"]
        logger.debug(name, this_message["state_name"])

        if this_message["state_name"] != "ready":
            continue

        this_name = this_message["name"]
        this_stream = this_message["stream"]
        this_version = this_message["version"]
        this_context = this_message["context"]
        nsvc = f"{this_name}-{this_stream}-{this_version}-{this_context}"

        try:
            modulemd = yaml.safe_load(
                retrieve_modulemd_content(
                    this_name, this_stream, this_version, this_context))
        except requests.exceptions.HTTPError as e:
            print("      Unable to find yaml file for module.")
            logger.exception(f'Failed to retrieve modulemd for {nsvc}: {str(e)}')

            # Continue to wait for and handle next module build which moves
            # to ready state.
            continue

        logger.debug('Modulemd file is downloaded and parsed.')

        rule_matches = list(filter(truth, (
            RuleDef(rule_def).match(modulemd)
            for rule_def in rule_defs
        )))

        if rule_matches:
            stream = this_stream.replace('-', '_')
            nvr = f'{this_name}-{stream}-{this_version}.{this_context}'
            dest_tags = [item.dest_tag for item in rule_matches]
            logger.debug('Tag build %s with tag(s) %s', nvr, ', '.join(dest_tags))
            tag_build(nvr, dest_tags)
        else:
            logger.info('Module build %s does not match any rule.', nsvc)
