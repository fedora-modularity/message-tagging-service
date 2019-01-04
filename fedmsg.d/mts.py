# -*- coding: utf-8 -*-

import os
import warnings

config = {
    'mts-consumer': True,
}


if 'MTS_RH' in os.environ:
    stomp_uri = os.environ.get('MTS_STOMP_URI')
    if not stomp_uri:
        warnings.warn(
            'Missing environment variable MTS_STOMP_URI for UMB brokers.',
            RuntimeWarning)

    stomp_ssl_crt = os.environ.get('MTS_STOMP_SSL_CRT')
    if not stomp_ssl_crt:
        warnings.warn(
            'Missing environment variable MTS_STOMP_SSL_CRT for certificate file.',
            RuntimeWarning)
    if not os.path.exists(stomp_ssl_crt):
        raise ValueError(f'Certificate file {stomp_ssl_crt} does not exist.')

    stomp_ssl_key = os.environ.get('MTS_STOMP_SSL_KEY')
    if not stomp_ssl_key:
        warnings.warn(
            'Missing environment variable MTS_STOMP_SSL_KEY for private key file.',
            RuntimeWarning)
    if not os.path.exists(stomp_ssl_key):
        raise ValueError(f'Private key file {stomp_ssl_key} does not exist.')

    config.update({
        'validate_signatures': False,
        'zmq_enabled': False,

        'stomp_heartbeat': 1000,

        # UMB brokers. Could be a comma-separated string of broker URIs.
        'stomp_uri': stomp_uri,
        # File name with absolute path to certificate file.
        'stomp_ssl_crt': stomp_ssl_crt,
        # File name with absolute path to private key file.
        'stomp_ssl_key': stomp_ssl_key,
    })
