# -*- coding: utf-8 -*-

import os


class BaseConfiguration:
    dry_run = os.environ.get('MTS_DRY_RUN', False)
    rule_file = '/etc/mts/mts.module-rules.yaml'
    koji_profile = 'koji'
    koji_cert = '/etc/mts/msg-tagger.pem'
    msg_certificate = '/etc/mts/msg-tagger.crt'
    msg_private_key = '/etc/mts/msg-tagger.key'
    msg_trusted_certificates = '/etc/mts/msg-tagger-ca.crt'
    msg_topic_send = 'message.bus.msgtag'

    # Messages sent to these topics will be handled.
    if 'MTS_RH' in os.environ:
        messaging_topics = [
            'Consumer.mts-client.queue.VirtualTopic.eng.mbs.module.state.change',
        ]
    else:
        messaging_topics = [
            'org.fedoraproject.prod.mbs.module.state.change',
        ],


class DevConfiguration(BaseConfiguration):
    koji_profile = 'stg'
    messaging_topics = [
        'org.fedoraproject.dev.mbs.build.state.change'
        'org.fedoraproject.stg.mbs.build.state.change'
    ]


if 'MTS_DEV' in os.environ:
    mts_conf = DevConfiguration()
else:
    mts_conf = BaseConfiguration()
