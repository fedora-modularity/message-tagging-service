# -*- coding: utf-8 -*-

import os


class BaseConfiguration:
    dry_run = os.environ.get('MTS_DRY_RUN', False)
    rule_file = '/etc/mts/mts.module-rules.yaml'
    koji_profile = 'koji'
    koji_cert = '/etc/mts/msg-tagger.pem'

    # Messages sent to these topics will be handled.
    # For internal, it is set to a UMB queue name, for example,
    # Consumer.client-mts.queue.VirtualTopic.eng.mbs.module.state.change
    consumer_topics = [
        'org.fedoraproject.prod.mbs.module.state.change',
    ],

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


class DevConfiguration(BaseConfiguration):
    koji_profile = 'stg'
    consumer_topics = [
        'org.fedoraproject.dev.mbs.build.state.change'
        'org.fedoraproject.stg.mbs.build.state.change'
    ]


if 'MTS_DEV' in os.environ:
    mts_conf = DevConfiguration()
else:
    mts_conf = BaseConfiguration()
