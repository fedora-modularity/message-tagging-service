# -*- coding: utf-8 -*-

mts_conf = {
    'rule_file': '/etc/mts/mts.module-rules.yaml',
    'koji_profile': 'brew',
    'koji_cert': '/etc/mts/msg-tagger.pem',
    'msg_environment': 'stage',
    'msg_certificate': '/etc/mts/msg-tagger.crt',
    'msg_private_key': '/etc/mts/msg-tagger.key',
    'msg_trusted_certificates': '/etc/mts/msg-tagger-ca.crt',
    'msg_topic_send': 'message.bus.msgtag',
    'msg_topic_listen': 'Consumer.username.stage.message.bus.mbs.module.state.change',
}

broker_envs = {
    'dev': [
        'amqps://messaging-broker01.dev.example.com:5678',
        'amqps://messaging-broker02.dev.example.com:5678'
    ],
    'stage': [
        'amqps://messaging-broker01.stage.example.com:5678',
        'amqps://messaging-broker02.stage.example.com:5678'
    ],
    'prod': [
        'amqps://messaging-broker01.prod.example.com:5678',
        'amqps://messaging-broker02.prod.example.com:5678'
    ]
}
