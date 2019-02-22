# -*- coding: utf-8 -*-

import koji
import os
import pytest

from mock import Mock
from mock import call
from mock import patch
from textwrap import dedent

from message_tagging_service import tagging_service
from message_tagging_service.utils import read_rule_defs

test_data_dir = os.path.join(os.path.dirname(__file__), 'data')


# Fake koji config returned from koji.read_config that ensures krb_login is
# called successfully.
koji_config_krb_auth = {
    'authtype': 'kerberos',
    'debug': False,
    'server': 'http://localhost/',
    'cert': '',
    'keytab': None,
    'principal': None,
}


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
        assert ['modular-fallback-tag'] == match.dest_tags

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
        assert ['modular-fallback-tag'] == match.dest_tags

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
        assert ['modular-fallback-tag'] == match.dest_tags

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
        assert [r'\g<platform>-modular-ursamajor'] == match.dest_tags

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
        assert ['f28-modular-ursamajor'] == match.dest_tags


class TestMatchRuleDefinitions(object):

    @patch('message_tagging_service.tagging_service.retrieve_modulemd_content')
    @patch('message_tagging_service.tagging_service.tag_build')
    def test_not_tag_build_if_no_rules_are_matched(
            self, tag_build, retrieve_modulemd_content):
        # Note that, platform does not match the rule in rule file.
        retrieve_modulemd_content.return_value = dedent('''\
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
            ''')

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
    @patch('message_tagging_service.messaging.publish')
    @patch('koji.ClientSession')
    @patch('koji.read_config')
    def test_tag_build_if_match_one_rule_only(
            self, read_config, ClientSession, publish, retrieve_modulemd_content):
        read_config.return_value = koji_config_krb_auth

        # Note that, platform does not match the rule in rule file.
        retrieve_modulemd_content.return_value = dedent('''\
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
            ''')

        rule_file = os.path.join(test_data_dir, 'mts-test-rules.yaml')
        with patch('requests.get') as get:
            with open(rule_file, 'r') as f:
                get.return_value.text = f.read()
            rule_defs = read_rule_defs()

            session = ClientSession.return_value
            session.tagBuild.side_effect = [1, 2, 3]

            tagging_service.handle(rule_defs, {
                'id': 1,
                'name': 'javapackages-tools',
                'stream': '1',
                'version': '1',
                'context': 'c1',
                'state_name': 'ready',
            })

            nvr = 'javapackages-tools-1-1.c1'
            nvr_devel = 'javapackages-tools-devel-1-1.c1'
            session.tagBuild.assert_has_calls([
                call('f29-modular-ursamajor', nvr),
                call('f29-modular-ursamajor', nvr_devel),
            ], any_order=True)

            # 2 messages should be sent:
            # javapackages-tools: f29
            # javapackages-tools-devel: f29
            publish.assert_has_calls([
                call('build.tag.requested', {
                    'build': {
                        'id': 1, 'name': 'javapackages-tools',
                        'stream': '1', 'version': '1', 'context': 'c1',
                    },
                    'nvr': nvr,
                    'destination_tags': [
                        {'tag': 'f29-modular-ursamajor', 'task_id': 1},
                    ],
                }),
                call('build.tag.requested', {
                    'build': {
                        'id': 1, 'name': 'javapackages-tools-devel',
                        'stream': '1', 'version': '1', 'context': 'c1',
                    },
                    'nvr': nvr_devel,
                    'destination_tags': [
                        {'tag': 'f29-modular-ursamajor', 'task_id': 2},
                    ],
                }),
            ], any_order=True)

    @pytest.mark.parametrize(
        'tagBuild_side_effect,expected_destination_tags_for_build,'
        'expected_destination_tags_for_devel_build',
        [
            # All tagBuild requests succeed
            [
                [1, 2, 3, 4, 5],
                [
                    {'tag': 'f29-modular-ursamajor', 'task_id': 1},
                    {'tag': 'f28-modular-ursamajor', 'task_id': 2},
                ],
                [
                    {'tag': 'f29-modular-ursamajor', 'task_id': 3},
                    {'tag': 'f28-modular-ursamajor', 'task_id': 4},
                ]
            ],
            # All tagBuild requests fail
            [
                [
                    koji.TagError('failed to tag build'),
                    koji.TagError('failed to tag build'),
                    koji.TagError('failed to tag build'),
                    koji.TagError('failed to tag build'),
                ],
                [
                    {
                        'tag': 'f29-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                    {
                        'tag': 'f28-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                ],
                [
                    {
                        'tag': 'f29-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                    {
                        'tag': 'f28-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                ]
            ],
            # tagBuild requests fail for f29-* tags, but succeed for f28-*
            [
                [
                    koji.TagError('failed to tag build'),
                    1,  # Returned fake task id for applying tag f28-* to build
                    koji.TagError('failed to tag build'),
                    2,  # Returned fake task id for applying tag f28-* to devel build
                ],
                [
                    {
                        'tag': 'f29-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                    {
                        'tag': 'f28-modular-ursamajor',
                        'task_id': 1,
                    },
                ],
                [
                    {
                        'tag': 'f29-modular-ursamajor',
                        'task_id': None,
                        'error': 'failed to tag build'
                    },
                    {
                        'tag': 'f28-modular-ursamajor',
                        'task_id': 2,
                    },
                ]
            ],
        ])
    @patch('message_tagging_service.tagging_service.retrieve_modulemd_content')
    @patch('message_tagging_service.messaging.publish')
    @patch('koji.ClientSession')
    @patch('koji.read_config')
    def test_apply_multiple_tags_to_a_matched_build(
            self, read_config, ClientSession, publish, retrieve_modulemd_content,
            tagBuild_side_effect, expected_destination_tags_for_build,
            expected_destination_tags_for_devel_build
    ):
        read_config.return_value = koji_config_krb_auth

        # Because rule file specifies that destination tag uses the value of
        # requires.platform, and there are two of those values in modulemd,
        # the module build should be tagged with two tags.
        retrieve_modulemd_content.return_value = dedent('''\
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
                  platform: [f29, f28]
            ''')

        session = ClientSession.return_value
        session.tagBuild.side_effect = tagBuild_side_effect

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

            nvr = 'javapackages-tools-1-1.c1'
            nvr_devel = 'javapackages-tools-devel-1-1.c1'
            session.tagBuild.assert_has_calls([
                call('f29-modular-ursamajor', nvr),
                call('f28-modular-ursamajor', nvr),
                call('f29-modular-ursamajor', nvr_devel),
                call('f28-modular-ursamajor', nvr_devel),
            ], any_order=True)

            # 2 messages should be sent:
            # javapackages-tools: f29, f28
            # javapackages-tools-devel: f29, f28
            publish.assert_has_calls([
                call('build.tag.requested', {
                    'build': {
                        'id': 1, 'name': 'javapackages-tools',
                        'stream': '1', 'version': '1', 'context': 'c1',
                    },
                    'nvr': nvr,
                    'destination_tags': expected_destination_tags_for_build,
                }),
                call('build.tag.requested', {
                    'build': {
                        'id': 1, 'name': 'javapackages-tools-devel',
                        'stream': '1', 'version': '1', 'context': 'c1',
                    },
                    'nvr': nvr_devel,
                    'destination_tags': expected_destination_tags_for_devel_build,
                }),
            ], any_order=True)


class TestLoginKoji(object):
    """Test login_koji"""

    @patch.object(tagging_service.conf, 'koji_cert', new='path/to/cert')
    @patch('os.path.exists', return_value=True)
    @patch('os.access', return_value=True)
    def test_ssl_login(self, access, exists):
        session = Mock()
        # Ensure koji_cli.lib.activate_session completes API version check.
        session.getAPIVersion.return_value = 1

        tagging_service.login_koji(session, {
            'authtype': 'kerberos',
            'serverca': '',
            'debug': False,
        })

        session.ssl_login.assert_called_once_with(
            'path/to/cert', None, '', proxyuser=None)

    @pytest.mark.parametrize("keytab,principal,krb_login_kwargs", [
        (None, None, {'proxyuser': None}),
        ('path/to/keytab', None, {'proxyuser': None}),
        (None, 'mts/hostname@EXAMPLE.COM', {'proxyuser': None}),
        ('path/to/keytab', 'mts/hostname@EXAMPLE.COM', {
            'keytab': 'path/to/keytab',
            'principal': 'mts/hostname@EXAMPLE.COM',
            'proxyuser': None
        }),
    ])
    @patch('os.path.exists', return_value=True)
    @patch('os.access', return_value=True)
    def test_krb_login(self, access, exists, keytab, principal, krb_login_kwargs):
        session = Mock()
        session.getAPIVersion.return_value = 1

        with patch.object(tagging_service.conf, 'keytab', new=keytab):
            with patch.object(tagging_service.conf, 'principal', new=principal):
                tagging_service.login_koji(session, koji_config_krb_auth)

        session.krb_login.assert_called_once_with(**krb_login_kwargs)

    @patch.object(tagging_service.conf, 'koji_cert', new='path/to/cert')
    def test_raise_error_if_ssl_cert_is_not_readable(self):
        session = Mock()
        # Ensure koji_cli.lib.activate_session completes API version check.
        session.getAPIVersion.return_value = 1

        with pytest.raises(
                IOError, message='SSL certificate path/to/cert is not readable.'):
            tagging_service.login_koji(session, {
                'authtype': 'kerberos',
                'serverca': '',
                'debug': False,
            })
