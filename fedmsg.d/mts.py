# -*- coding: utf-8 -*-

import os

config = {
    "validate_signatures": False,
    "active": True,
    "environment": "prod",
    "endpoints": {
        "fedora-infrastructure": [
            # Just listen to staging for now, not to production (spam!)
            # "tcp://hub.fedoraproject.org:9940",
            "tcp://stg.fedoraproject.org:9940",
        ],
        'relay_outbound': ["tcp://127.0.0.1:4001"],
    },
    'relay_inbound': ["tcp://127.0.0.1:2003"],

    'mts-consumer': True,
}

if 'MTS_USE_STOMP' in os.environ:
    config.update({
        'zmq_enabled': False,
        'stomp_heartbeat': 1000,
        # UMB brokers. Could be a comma-separated string of broker URIs.
        'stomp_uri': os.environ['MTS_STOMP_URI'],
        # File name with absolute path to certificate file.
        'stomp_ssl_crt': os.environ['MTS_STOMP_SSL_CRT'],
        # File name with absolute path to private key file.
        'stomp_ssl_key': os.environ['MTS_STOMP_SSL_KEY'],
    })
