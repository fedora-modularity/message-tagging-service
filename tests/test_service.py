# -*- coding: utf-8 -*-

import os

from mock import Mock
from mock import call
from mock import patch

from message_tagging_service import tagging_service
from message_tagging_service.utils import read_rule_defs

test_data_dir = os.path.join(os.path.dirname(__file__), 'data')


class TestRuleDefinitionCheck(object):
    """Test rule_matches_module_build"""

    def test_simple_rule_definition(self):
        rule_def = {
            'id': 'Simple match any module',
            'type': 'module',
            'description': 'Match any module build.',
            'destinations': 'modular-fallback-tag'
        }
        match = tagging_service.RuleDef(rule_def).match(Mock())
        assert match
        assert 'modular-fallback-tag' == match.dest_tag

    def test_match_scratch_module_build(self):
        rule_def = {
            'id': 'Simple match by scratch',
            'type': 'module',
            'rule': {'scratch': True},
            'description': 'Match module build by scratch.',
            'destinations': 'modular-fallback-tag'
        }

        modulemd = {'data': {'scratch': True}}
        match = tagging_service.RuleDef(rule_def).match(modulemd)
        assert match
        assert 'modular-fallback-tag' == match.dest_tag

        modulemd = {'data': {'scratch': False}}
        assert not tagging_service.RuleDef(rule_def).match(modulemd)

        modulemd = {'data': {}}
        assert not tagging_service.RuleDef(rule_def).match(modulemd)

    def test_match_development_module_build(self):
        rule_def = {
            'id': 'Simple match by development',
            'type': 'module',
            'rule': {'development': True},
            'description': 'Match module build by development.',
            'destinations': 'modular-fallback-tag'
        }

        modulemd = {'data': {'development': True}}
        match = tagging_service.RuleDef(rule_def).match(modulemd)
        assert match
        assert 'modular-fallback-tag' == match.dest_tag

        modulemd = {'data': {'development': False}}
        assert not tagging_service.RuleDef(rule_def).match(modulemd)

        modulemd = {'data': {}}
        assert not tagging_service.RuleDef(rule_def).match(modulemd)

    def test_match_module_by_list_of_regex(self):
        rule_def = {
            'id': 'Match module by list of regular expressions',
            'type': 'module',
            'rule': {
                'name': [r'^javapackages-tools$', r'-ursamajor$']
            },
            'description': 'Match module build by development.',
            'destinations': r'\g<platform>-modular-ursamajor',
        }

        modulemd = {'data': {'name': 'javapackages-tools'}}
        match = tagging_service.RuleDef(rule_def).match(modulemd)
        assert match
        assert r'\g<platform>-modular-ursamajor' == match.dest_tag

        modulemd = {'data': {'name': 'module-a-ursamajor'}}
        assert tagging_service.RuleDef(rule_def).match(modulemd)

        modulemd = {'data': {'name': 'module-b'}}
        assert not tagging_service.RuleDef(rule_def).match(modulemd)

    def test_match_module_by_dict_type_rule(self):
        rule_def = {
            'id': 'Match module by name',
            'type': 'module',
            'rule': {
                'dependencies': {
                    'buildrequires': {'platform': r'^.*$'},
                    'requires': {'platform': r'^(?P<platform>f\d+)$'}
                },
            },
            'description': 'Match module build by development.',
            'destinations': r'\g<platform>-modular-ursamajor',
        }

        modulemd = {'data': {
            'dependencies': [{
                'buildrequires': {'platform': ['f28']},
                'requires': {'platform': ['f28']},
            }]
        }}
        match = tagging_service.RuleDef(rule_def).match(modulemd)
        assert match
        assert 'f28-modular-ursamajor' == match.dest_tag


class TestMatchRuleDefinitions(object):

    @patch('message_tagging_service.tagging_service.retrieve_modulemd_content')
    @patch('message_tagging_service.tagging_service.tag_build')
    def test_not_tag_build_if_no_rules_are_matched(
            self, tag_build, retrieve_modulemd_content):
        # Note that, platform does not match the rule in rule file.
        retrieve_modulemd_content.return_value = '''\
---
document: modulemd
version: 2
data:
  name: ant
  stream: 1
  version: 1
  context: c1
  dependencies:
  - buildrequires:
      platform: [el8]
    requires:
      platform: [el8]
'''

        rule_file = os.path.join(test_data_dir, 'mts-test-for-no-match.yaml')
        with patch('requests.get') as get:
            with open(rule_file, 'r') as f:
                get.return_value.text = f.read()
            rule_defs = read_rule_defs()

        with patch.object(tagging_service.logger, 'info') as info:
            # Note that, no module property matches rule in rule file.
            tagging_service.handle(rule_defs, {
                'id': 1,
                'name': 'ant',
                'stream': '1',
                'version': '1',
                'context': 'c1',
                'state_name': 'ready',
            })

            assert ('Module build %s does not match any rule.', 'ant-1-1-c1') == \
                info.call_args[0]
            tag_build.assert_not_called()

    @patch('message_tagging_service.tagging_service.retrieve_modulemd_content')
    @patch('koji.ClientSession')
    @patch('koji.read_config')
    def test_tag_build_if_match_one_rule_only(
            self, read_config, ClientSession, retrieve_modulemd_content):
        # Note that, platform does not match the rule in rule file.
        retrieve_modulemd_content.return_value = '''\
---
document: modulemd
version: 2
data:
  name: javapackages-tools
  stream: 1
  version: 1
  context: c1
  dependencies:
  - buildrequires:
      platform: [f29]
    requires:
      platform: [f29]
'''

        rule_file = os.path.join(test_data_dir, 'mts-test-rules.yaml')
        with patch('requests.get') as get:
            with open(rule_file, 'r') as f:
                get.return_value.text = f.read()
            rule_defs = read_rule_defs()

            tagging_service.handle(rule_defs, {
                'id': 1,
                'name': 'javapackages-tools',
                'stream': '1',
                'version': '1',
                'context': 'c1',
                'state_name': 'ready',
            })

            session = ClientSession.return_value
            nvr = 'javapackages-tools-1-1.c1'
            session.tagBuild.assert_has_calls([
                call('f29-modular-ursamajor', nvr),
                call('modular-fallback-tag', nvr),
            ], any_order=True)

    @patch('message_tagging_service.tagging_service.retrieve_modulemd_content')
    @patch('message_tagging_service.messaging.publish')
    @patch('koji.ClientSession')
    @patch('koji.read_config')
    def test_tag_build_if_multiple_rules_are_matched(
            self, read_config, ClientSession, publish, retrieve_modulemd_content):
        # Note that, {development: true} is added. That will causes this module
        # matches a second rule as well.
        retrieve_modulemd_content.return_value = '''\
---
document: modulemd
version: 2
data:
  name: javapackages-tools
  stream: 1
  version: 1
  context: c1
  development: true
  dependencies:
  - buildrequires:
      platform: [f29]
    requires:
      platform: [f29]
'''

        rule_file = os.path.join(test_data_dir, 'mts-test-rules.yaml')
        with patch('requests.get') as get:
            with open(rule_file, 'r') as f:
                get.return_value.text = f.read()
            rule_defs = read_rule_defs()

            tagging_service.handle(rule_defs, {
                'id': 1,
                'name': 'javapackages-tools',
                'stream': '1',
                'version': '1',
                'context': 'c1',
                'state_name': 'ready',
            })

            session = ClientSession.return_value
            session.tagBuild.side_effect = [1, 2]  # Task ids
            nvr = 'javapackages-tools-1-1.c1'
            session.tagBuild.assert_has_calls([
                call('modular-development-builds', nvr),
                call('modular-fallback-tag', nvr),
            ], any_order=True)

            publish.assert_called_once_with('build.tagged', {
                'build': {
                    'id': 1,
                    'name': 'javapackages-tools',
                    'stream': '1',
                    'version': '1',
                    'context': 'c1',
                },
                'nvr': nvr,
                'destination_tags': [
                    'modular-development-builds',
                    'modular-fallback-tag',
                ]
            })
