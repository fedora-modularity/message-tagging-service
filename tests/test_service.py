# -*- coding: utf-8 -*-

import contextlib
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


# Fake koji config returned from koji.read_config that ensures gssapi_login is
# called successfully.
koji_config_krb_auth = {
    'authtype': 'kerberos',
    'debug': False,
    'server': 'http://localhost/',
    'cert': '',
    'keytab': None,
    'principal': None,
}


@contextlib.contextmanager
def mock_get_rule_file(rule_file):
    with patch('requests.get') as get:
        with open(rule_file, 'r') as f:
            get.return_value.text = f.read()
        yield


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

    def setup_method(self, test_method):
        self.p_read_config = patch('koji.read_config',
                                   return_value=koji_config_krb_auth)
        self.mock_read_config = self.p_read_config.start()

        self.p_retrieve_modulemd_content = patch(
            'message_tagging_service.tagging_service.retrieve_modulemd_content')
        self.mock_retrieve_modulemd_content = self.p_retrieve_modulemd_content.start()

        self.p_publish = patch('message_tagging_service.messaging.publish')
        self.mock_publish = self.p_publish.start()

        self.p_ClientSesison = patch('koji.ClientSession')
        self.mock_ClientSession = self.p_ClientSesison.start()

    def teardown_method(self, test_method):
        self.p_ClientSesison.stop()
        self.p_publish.stop()
        self.p_retrieve_modulemd_content.stop()
        self.p_read_config.stop()

    @patch('message_tagging_service.tagging_service.tag_build')
    @mock_get_rule_file(os.path.join(
        test_data_dir, 'mts-test-for-no-match.yaml'))
    def test_not_tag_build_if_no_rules_are_matched(self, tag_build):
        # Note that, platform does not match the rule in rule file.
        self.mock_retrieve_modulemd_content.return_value = dedent('''\
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

    @mock_get_rule_file(os.path.join(test_data_dir, 'mts-test-rules.yaml'))
    def test_tag_build_if_match_one_rule_only(self):

        # Note that, platform does not match the rule in rule file.
        self.mock_retrieve_modulemd_content.return_value = dedent('''\
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

        session = self.mock_ClientSession.return_value
        session.tagBuild.side_effect = [1, 2, 3]

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
            call('f29-modular-ursamajor', nvr_devel),
        ], any_order=True)

        # 2 messages should be sent:
        # javapackages-tools: f29
        # javapackages-tools-devel: f29
        self.mock_publish.assert_has_calls([
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
    @mock_get_rule_file(os.path.join(test_data_dir, 'mts-test-rules.yaml'))
    def test_apply_multiple_tags_to_a_matched_build(
            self,
            tagBuild_side_effect,
            expected_destination_tags_for_build,
            expected_destination_tags_for_devel_build
    ):

        # Because rule file specifies that destination tag uses the value of
        # requires.platform, and there are two of those values in modulemd,
        # the module build should be tagged with two tags.
        self.mock_retrieve_modulemd_content.return_value = dedent('''\
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

        session = self.mock_ClientSession.return_value
        session.tagBuild.side_effect = tagBuild_side_effect

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
        self.mock_publish.assert_has_calls([
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

    @mock_get_rule_file(os.path.join(test_data_dir, 'mts-test-rules.yaml'))
    def test_tag_build_with_complex_destination(self):
        self.mock_retrieve_modulemd_content.return_value = dedent('''\
            ---
            document: modulemd
            version: 2
            data:
              name: virt
              stream: 8.1
              version: 1
              context: c1
              dependencies:
              - buildrequires:
                  platform: [el8.1.1]
                requires:
                  platform: [el8]
            ''')

        session = self.mock_ClientSession.return_value
        session.tagBuild.side_effect = [1, 2]

        rule_defs = read_rule_defs()
        tagging_service.handle(rule_defs, {
            'id': 1,
            'name': 'virt',
            'stream': '8.1',
            'version': '1',
            'context': 'c1',
            'state_name': 'ready',
        })

        nvr = 'virt-8.1-1.c1'
        nvr_devel = 'virt-devel-8.1-1.c1'
        session.tagBuild.assert_has_calls([
            call('advanced-virt-8.1-rhel-8.1.1-modules-gate', nvr),
            call('advanced-virt-8.1-rhel-8.1.1-modules-gate', nvr_devel),
        ], any_order=True)

    @pytest.mark.parametrize('build_state', ['done', 'build'])
    @mock_get_rule_file(os.path.join(test_data_dir, 'mts-test-rules.yaml'))
    def test_match_module_by_build_state_in_rule(self, build_state):
        self.mock_retrieve_modulemd_content.return_value = dedent('''\
            ---
            document: modulemd
            version: 2
            data:
              name: nodejs
              stream: 10
              version: 1
              context: c1
              dependencies:
              - buildrequires:
                  platform: [f29]
                requires:
                  platform: [f29]
            ''')

        session = self.mock_ClientSession.return_value
        session.tagBuild.side_effect = [1, 2, 3]

        rule_defs = read_rule_defs()
        tagging_service.handle(rule_defs, {
            'id': 1,
            'name': 'nodejs',
            'stream': '10',
            'version': '1',
            'context': 'c1',
            'state_name': build_state,
        })

        if build_state == 'done':
            session.tagBuild.assert_has_calls([
                call('f29-modular-gating', 'nodejs-10-1.c1'),
                call('f29-modular-gating', 'nodejs-devel-10-1.c1'),
            ], any_order=True)
        elif build_state == 'build':
            # The rule file for this test does not any rule defined for state
            # "build", so no rule is matched, then no tag should be applied to
            # the fake module build.
            session.tagBuild.assert_not_called()


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

        session.gssapi_login.assert_called_once_with(**krb_login_kwargs)

    @patch.object(tagging_service.conf, 'koji_cert', new='path/to/cert')
    def test_raise_error_if_ssl_cert_is_not_readable(self):
        session = Mock()
        # Ensure koji_cli.lib.activate_session completes API version check.
        session.getAPIVersion.return_value = 1

        with pytest.raises(
                IOError, match='SSL certificate path/to/cert is not readable.'):
            tagging_service.login_koji(session, {
                'authtype': 'kerberos',
                'serverca': '',
                'debug': False,
            })
