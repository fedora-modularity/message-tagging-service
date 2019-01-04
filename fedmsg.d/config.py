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
}

if 'MTS_DEV' in os.environ:
    config['endpoints']['relay_outbound'] = ["tcp://fedmsg-relay:4001"]
    config['relay_inbound'] = ["tcp://fedmsg-relay:2003"]
