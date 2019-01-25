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

    # Messages sent to these topics will be handled.
    # For internal, it is set to a UMB queue name, for example,
    # Consumer.client-mts.queue.VirtualTopic.eng.mbs.module.state.change
    consumer_topics = [
        'org.fedoraproject.prod.mbs.module.state.change',
    ]

    # Indicate which messaging backend will be used to send message.
    # Choices: fedmsg and rhmsg. For internal, set it to rhmsg.
    messaging_backend = 'fedmsg'

    # Define messaging backends for sending messages to message bus. In Fedora,
    # it is fedmsg, rhmsg for internal.
    messaging_backends = {
        'fedmsg': {
            'service': 'mts',
        },
        'rhmsg': {
            # Broker URIs to connect, e.g. ['amqps://host:5671', 'amqps://anotherhost:5671']
            'brokers': [],
            # Absolute path to certificate file used to authenticate freshmaker
            'certificate': '',
            # Absolute path to private key file used to authenticate freshmaker
            'private_key': '',
            # Absolute path to trusted CA certificate bundle.
            'ca_cert': '',
            # Prefix to construct full topic to send message
            'topic_prefix': 'VirtualTopic.eng.mts',
        },
    }

    # Default is INFO. Refer to Python logging module to know valid values.
    log_level = 'INFO'

    # A URL of rules file which can be accessible via HTTP GET without authentication.
    # Example: https://example.com/rules/mts-rules.yaml
    rules_file_url = ''


class DevConfiguration(BaseConfiguration):
    koji_profile = 'stg'
    consumer_topics = [
        'org.fedoraproject.dev.mbs.module.state.change',
        'org.fedoraproject.stg.mbs.module.state.change',
    ]
    log_level = 'DEBUG'
    rules_file_url = (
        'https://raw.githubusercontent.com/fedora-modularity/message-tagging-service/'
        'master/rules/mts-rules.yaml'
    )


class TestConfiguration(DevConfiguration):
    pass
