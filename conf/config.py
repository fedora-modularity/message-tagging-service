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

    # Set messaging_backend to 'kafka' to interact with the IT Managed Kafka
    # service instead of UMB. During the UMB->Kafka migration the relevant
    # topics are kept in sync by the Messaging Bridge, so the kafka and rhmsg
    # backends can be switched independently for producing and consuming.

    # Kafka bootstrap servers to connect to, e.g.
    # ['kafka-broker1:9092', 'kafka-broker2:9092']
    kafka_bootstrap_servers = []
    # Kafka topic MTS consumes MBS module state change events from. During the
    # UMB->Kafka migration this topic is kept in sync with the equivalent UMB
    # VirtualTopic by the Messaging Bridge.
    kafka_consumer_topic = 'VirtualTopic.eng.mbs.module.state.change'
    # Consumer group id. Kafka tracks committed offsets per consumer group, so
    # keep this stable to avoid reprocessing messages across restarts.
    kafka_consumer_group_id = 'mts'
    # Where to start consuming when no committed offset exists for the group.
    kafka_auto_offset_reset = 'earliest'
    # A topic like build.tag.requested is passed to the publish function to
    # generalize the messaging publish interface. This prefix is prepended to
    # construct the full topic MTS publishes to.
    kafka_topic_prefix = 'VirtualTopic.eng.mts'
    # Timeout (seconds) to wait for a published message to be acknowledged.
    kafka_send_timeout = 30

    # Connection security for Kafka. One of: PLAINTEXT, SSL, SASL_PLAINTEXT,
    # SASL_SSL. IT Managed Kafka typically uses SASL_SSL.
    kafka_security_protocol = 'SASL_SSL'
    # SASL mechanism, e.g. SCRAM-SHA-512, PLAIN or OAUTHBEARER. Leave empty when
    # not using SASL.
    kafka_sasl_mechanism = 'SCRAM-SHA-512'
    # Credentials for SASL username/password mechanisms (PLAIN, SCRAM-*).
    kafka_sasl_username = ''
    kafka_sasl_password = ''
    # Absolute paths to TLS material. kafka_ssl_cafile verifies the brokers;
    # kafka_ssl_certfile/kafka_ssl_keyfile are only needed for mutual TLS auth.
    kafka_ssl_cafile = ''
    kafka_ssl_certfile = ''
    kafka_ssl_keyfile = ''

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

    # Default timeout of outgoing connection by python-requests
    requests_timeout = 60


class DevConfiguration(BaseConfiguration):
    koji_profile = 'stg'
    log_level = 'DEBUG'
    rules_file_url = (
        'https://raw.githubusercontent.com/fedora-modularity/message-tagging-service/'
        'master/rules/mts-rules.yaml'
    )


class TestConfiguration(DevConfiguration):
    pass
