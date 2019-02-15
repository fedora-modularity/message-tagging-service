Message Tagging Service
=======================

.. image:: https://img.shields.io/pypi/v/message-tagging-service.svg
   :target: https://pypi.org/project/message-tagging-service/

.. image:: https://img.shields.io/pypi/pyversions/message-tagging-service.svg
   :target: https://pypi.org/project/message-tagging-service/

.. image:: https://img.shields.io/pypi/l/message-tagging-service.svg?colorB=green
   :target: https://pypi.org/project/message-tagging-service/

.. image:: https://travis-ci.org/fedora-modularity/message-tagging-service.svg?branch=master
   :target: https://travis-ci.org/fedora-modularity/message-tagging-service

Message tagging service is a microservice to tag build with proper tags, which
is triggered by specific message from a message bus. Currently, service
supports to tag module build according to a module build state change event.

This service works with Python 3.6 and 3.7.

Workflow
--------

This is the service workflow, for example of a module build.

* Listen on message bus (that is fedmsg in Fedora) and waiting for module build
  state change event. Only ``ready`` state is handled.
* Service consult to predefined rule definitions to check if that module build
  matches any rule.
* If one or more rules are matched, tag the module build with tags defined in
  matched rules.
* Send message to message bus to announce a module build is tagged with
  specific tags.

Rule Definition
---------------

Rule definition is documented in a `Modularity document`_

For detailed information on how the rules are matched, please refer to
`paragraph`_ in that document.

.. _Modularity document: https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md
.. _paragraph: https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md?text=True#_8

Configuration
-------------

There are two type of configurations.

* ``fedmsg.d/mts.py``: including MTS-specific configs for fedmsg hub. ``mts.py``
  enables defined consumer and configures to connect UMB accordingly. Refer to
  section ``Environment Variables`` to learn how to enable stomp protocol to
  connect other message bus other than the fedmsg.

* ``conf/config.py``: including configs for service.

  * ``BaseConfiguration`` provides default options which could be reused for
    running in production.
  * ``DevConfiguration`` contains anything for running in development mode.
  * ``TestConfiguration`` contains any config for test purpose.

* Koji login authentication method. It defaults to Kerberos, which is set in
  default ``koji`` profile. It could be changed to other ``authtype``, for
  example ``ssl``. Please note that ``cert`` has to be set as well for
  ``ssl``.

Messaging
---------

Events
~~~~~~

build.tag.requested
^^^^^^^^^^^^^^^^^^^

Message is sent when a ``tagBuild`` task is requested in Koji. An example message::

    {
      "build": {
        "id": id,
        "name": name,
        "stream": stream,
        "version": version,
        "context": context,
      },
      "nvr": N-V-R,
      "destination_tags": [
        {"tag": name_1, "task_id": 1},
        {"tag": name_2, "task_id": 2},
        ...
      ]
    }

where, ``destination_tags`` is a list of mappings each of them contains the tag
to apply and corresponding task ID returned from Koji.

build.tag.unmatched
^^^^^^^^^^^^^^^^^^^

Message is sent if a module build does not match any predefined rules. An
example message::

    {
      "build": {
        "id": id,
        "name": name,
        "stream": stream,
        "version": version,
        "context": context,
      },
    }

The message simply contains the module build information.

Topic Prefix
~~~~~~~~~~~~

For Fedora, messages are sent to topics with prefix ``org.fedoraproject.prod``,
e.g. ``org.fedoraproject.prod.mts.build.tag.requested``.

For internal, the prefix is ``VirtualTopic.eng.mts``, e.g.
``VirtualTopic.eng.mts.build.tag.requested``.

Environment Variables
---------------------

MTS_DRY_RUN
~~~~~~~~~~~

Dry run mode. Currently, no build is tagged actually in dry run mode. No
particular is required. Just define ``MTS_DRY_RUN`` in environment variables.

MTS_DEV
~~~~~~~

Switch service to run in development mode as long as ``MTS_DEV`` is defined.

MTS_USE_STOMP
~~~~~~~~~~~~~

Make service run with internal infrastructure. No particular value is required.
Just define ``MTS_USE_STOMP`` in environment variables.

MTS_STOMP_URI
~~~~~~~~~~~~~

A comma-separated string of UMB broker URIs. For example::

   'messaging-broker01.dev1.example.com,messaging-broker02.dev2.example.com'

MTS_STOMP_CRT
~~~~~~~~~~~~~

An absolute path to certificate file.

MTS_STOMP_KEY
~~~~~~~~~~~~~

An absolute path to private key file.

Both of the certificate file and this private key file are required to connect
to internal UMB brokers.

Contribution
------------

Report issue at https://github.com/fedora-modularity/message-tagging-service/issues.

Before making a pull request, ensure the changes do not break anything and are
covered by tests. Run tests::

  tox

Change Logs
-----------

0.2 (2019-01-22)
~~~~~~~~~~~~~~~~

- Add missing files to tarball generated by sdist

0.1 (2019-01-21)
~~~~~~~~~~~~~~~~

- First release that MTS is able to handle specific message to tag build.

