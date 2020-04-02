# -*- coding: utf-8 -*-

import os


class BaseConfiguration:
    dry_run = os.environ.get('MTS_DRY_RUN', False)
    mbs_api_url = 'https://mbs.fedoraproject.org/module-build-service/1/'

    koji_profile = 'koji'

    # User for ssl authtype to log into Koji.
    # In Koji configuration, kerberos is the default authtype. If this is set,
    # ssl authtype will be used instead.
    # A workable value could be '/etc/mts/msg-tagger.pem'
    koji_cert = None

    # Used for kerberos authtype to log into Koji.
    # Example: '/etc/mts/mts.keytab'
    keytab = None
    # MTS host principal inside the keytab. If keytab is specified to use a
    # keytab explicitly, principal must be set as well.
    # Example: 'mts/hostname@EXAMPLE.COM'
    principal = None

    # Please note that, if neither keytab nor principal is set or valid, the
    # default or configured Kerberos ccache will be used to get ticket. That
    # means kinit should be run with the keytab and principal in advance.

    # Please note that, no specific config for fedora-messaging is defined here.
    # Instead, refer to mts.toml for the complete configuration.
    # Set this to rhmsg for interacting with UMB.
    messaging_backend = 'fedora-messaging'

    # Broker URIs to connect, e.g. ['amqps://host:5671', 'amqps://anotherhost:5671']
    rhmsg_brokers = []
    # Absolute path to certificate file used to authenticate MTS
    rhmsg_certificate = ''
    # Absolute path to private key file used to authenticate MTS
    rhmsg_private_key = ''
    # Absolute path to trusted CA certificate bundle.
    rhmsg_ca_cert = ''
    # topic like build.tag.requested is passed to publish function to
    # generalize the messaging publish interface. For rhmsg, this
    # topic_prefix is used to construct full topic in order to send message.
    rhmsg_topic_prefix = 'VirtualTopic.eng.mts'
    # Queue name to receive message from. For example:
    # Consumer.client-mts.queue.VirtualTopic.eng.mbs.module.state.change
    rhmsg_queue = 'Consumer.client-mts.queue.VirtualTopic.eng.mbs.module.state.change'
    # The name used to identify unique subscriptions. Set this to a unique value
    # to enable durable messages.
    rhmsg_subscription_name = None

    # Default is INFO. Refer to Python logging module to know valid values.
    log_level = 'INFO'

    # A URL of rules file which can be accessible via HTTP GET without authentication.
    # Example: https://example.com/rules/mts-rules.yaml
    rules_file_url = ''

    # Default build state. Module builds which are in this state will be
    # tagged if no build state is specified in rule explicitly.
    build_state = 'ready'

    # Default build state filter for the messages sent by MBS. This happens
    # before any rules applied. Default: ['ready', 'done']
    build_state_msg_filter = ['ready', 'done']


class DevConfiguration(BaseConfiguration):
    koji_profile = 'stg'
    log_level = 'DEBUG'
    rules_file_url = (
        'https://raw.githubusercontent.com/fedora-modularity/message-tagging-service/'
        'master/rules/mts-rules.yaml'
    )


class TestConfiguration(DevConfiguration):
    pass
