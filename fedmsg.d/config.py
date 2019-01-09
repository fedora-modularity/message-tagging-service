# -*- coding: utf-8 -*-

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
