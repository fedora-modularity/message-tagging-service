# -*- coding: utf-8 -*-

mts_conf = {
	'rule_file': 'mts.module-rules-internal.yaml',
	'koji_profile': 'brew',
	'msg_enviroment': 'stage',
	'msg_certificate': 'mts.crt',
	'msg_private_key': 'mts.key',
	'msg_trusted_certificates': '/etc/pki/ca-trust/source/anchors/CA.crt',
	'msg_topic_send': 'message.bus.msgtag',
	'msg_topic_listen': 'Consumer.username.stage.message.bus.mbs.module.state.change',
	'mod_url_header': 'http://download.example.com/koji/brewroot/packages',

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
