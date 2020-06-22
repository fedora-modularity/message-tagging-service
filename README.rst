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

.. image:: https://quay.io/repository/factory2/message-tagging-service/status
   :target: https://quay.io/repository/factory2/message-tagging-service/status

Message tagging service is a microservice to tag build with proper tags, which
is triggered by specific message from a message bus. Currently, service
supports to tag module build according to a module build state change event.

This service works with Python 3.6 and 3.7.

Workflow
--------

This is the service workflow, for example of a module build.

* Listen on message bus, which is `fedora-messaging`_ in Fedora, and waiting
  for module build state change events.

* Once received a message, MTS checks predefined rule definitions one by one in
  the order of presence in rule file.

* If the module build matches a rule, apply tags defined in matched rule to
  this build and its associated ``-devel`` build.

* Send message to message bus to announce a module build is tagged with
  specific tags. Please note that MTS does not actually wait for the tag build
  task to finish. The message is sent just after ``tagBuild`` returns, which
  just creates a tag build task and returns immediately.

.. _fedora-messaging: https://fedora-messaging.readthedocs.io/en/stable/

Rule Definition
---------------

Rule definition is documented in a `Modularity document`_

For detailed information on how the rules are matched, please refer to
`paragraph`_ in that document.

.. _Modularity document: https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md
.. _paragraph: https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md?text=True#_8

Configuration
-------------

Application configuration ``conf/config.py``. Each config is well-documented,
please refer to this file's content for detailed information. Following three
config section are defined for different purpose to run MTS.

* ``BaseConfiguration`` provides default options which could be reused for
  running in production.
* ``DevConfiguration`` contains anything for running in development mode.
* ``TestConfiguration`` contains any config for test purpose.

Messaging configuration for fedora-messaging included in file ``conf/mts.toml``,
which includes configs for receiving and sending messages from and to
fedora-messaging broker in `TOML`_ format. The default config values is defined
well for interacting with a local RabbitMQ broker, which is good for testing
locally. For deployment, copy this file and adjust config values for the Fedora
messaging broker.

.. _TOML: https://github.com/toml-lang/toml

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
For example, ``export MTS_DEV=1``.

MTS_CONFIG_FILE
~~~~~~~~~~~~~~~

Specify an alternative config file instead of reading the ``conf/config.py``
when ``MTS_DEV`` is enabled or ``/etc/mts/config.py`` if MTS is installed in
system. Either an absolute path or relative path works.

Contribution
------------

Report issue at https://github.com/fedora-modularity/message-tagging-service/issues.

Before making a pull request, ensure the changes do not break anything and are
covered by tests. Run tests::

  tox

Change Logs
-----------

0.8.1 (2020-06-22)
~~~~~~~~~~~~~~~~~~

* Fix the field from build_state to state_name for state filter (Yu Ming Zhu)

0.8 (2020-06-18)
~~~~~~~~~~~~~~~~

* Only receive msgs with build_state is ready or done by default (Yu Ming Zhu)
* Unittest: the latest koji use gssapi_login instead of krb_login (Yu Ming Zhu)
* CI: Fix missing command to run tests (Chenxiong Qi)
* Use image fedora:31 in CI (Chenxiong Qi)

0.7 (2020-02-07)
~~~~~~~~~~~~~~~~

* Upgrade base image to Fedora 30
* Do not attempt to tag a scratch build (Chenxiong Qi)
* Do not handle scratch from rule (Chenxiong Qi)
* Add support for complex destinations (Luiz Carvalho)
* Run mts in the foreground (Luiz Carvalho)

0.6 (2019-09-27)
~~~~~~~~~~~~~~~~

* Revert "Log the exception when tag failures occur" (Chenxiong Qi)
* Allow durable queues when using rhmsg (Luiz Carvalho)
* Fix param type of dest_tags (Chenxiong Qi)
* Better logs (Chenxiong Qi)
* Log the exception when tag failures occur (mprahl)
* Set image version to latest (Chenxiong Qi)
* Fix consumer and add tests (Chenxiong Qi)
* Massive updates to README.rst (Chenxiong Qi)
* Fix variable name inside log message format (Chenxiong Qi)
* Include mts.toml config in sdist package (Chenxiong Qi)
* Do not include removed fedmsg.d/ directory (Chenxiong Qi)
* Remove fedmsg related lines from Dockerfile (Chenxiong Qi)
* Remove duplicate code handling rule scratch and development (Chenxiong Qi)
* Migrate to fedora-messaging (Chenxiong Qi)
* Refactor function is_file_readable (Chenxiong Qi)
* No need to set koji_cert if not use ssl auth (Chenxiong Qi)
* Ensure logout koji session if something wrong on session (Chenxiong Qi)
* Revert "Set USER for fedmsg to publish message" (Chenxiong Qi)
* Revert "Install packages for Fedora container" (Chenxiong Qi)
* Set USER for fedmsg to publish message (Chenxiong Qi)
* Install packages for Fedora container (Chenxiong Qi)
* Use new pytest.raises argument match (Chenxiong Qi)

0.5 (2019-04-15)
~~~~~~~~~~~~~~~~

- Change metric name to be in sync with other services (Filip Valder)
- Reduce the number of tries to match rules (Chenxiong Qi)
- Match module build by build state (Chenxiong Qi)

0.4.1 (2019-04-01)
~~~~~~~~~~~~~~~~~~

- Ignore https verify while downloading ca cert (Chenxiong Qi)

0.4 (2019-03-30)
~~~~~~~~~~~~~~~~

- Adjust gunicorn command line options (Chenxiong Qi)
- Increase the number of workers to run the web app (Chenxiong Qi)
- Set gunicorn log level to debug (Chenxiong Qi)
- Test image build and container in Travis-CI (Chenxiong Qi)
- Refactor Dockerfile (Chenxiong Qi)
- Add missing deps to Dockerfile (Chenxiong Qi)
- Add missing \ to break dnf-install command properly in Dockerfile (Chenxiong Qi)
- Expose metrics endpoint for monitoring (Chenxiong Qi)
- Add container badge in README (Chenxiong Qi)
- Include failed tagBuild task request in build.tag.requested message (Chenxiong Qi)

0.3 (2019-02-20)
~~~~~~~~~~~~~~~~

- Refine event topics (Chenxiong Qi)
- Fix badges in README (Chenxiong Qi)
- Better log when module build in init state (Chenxiong Qi)
- Use known good version of moksha-hub (Luiz Carvalho)
- Tag -devel CG Koji build (Luiz Carvalho)
- Handle multiple tags for single rule (Luiz Carvalho)
- Refine code for the first match wins (Chenxiong Qi)
- Use dedent in tests when mocking modulemd data (Luiz Carvalho)
- Only allow a single rule match (Luiz Carvalho)
- Make docker/install-ca.sh executable (mprahl)
- Add missing docker/install-ca.sh (mprahl)
- Add back the volumes for improved UX in OpenShift (mprahl)
- Connect over http when using the rcm-tools repo since the CA isn't trusted (mprahl)
- Fix a comment in the Jenkinsfile (mprahl)
- Add a Jenkins job to build container images and push them to quay.io (mprahl)
- Install rhmsg in the container image (mprahl)
- Add the ability to install a custom CA in the container image (mprahl)
- Set the default container user to 1001 to mimic OpenShift (mprahl)
- Add additional DNF arguments to make the container image slightly smaller (mprahl)
- Remove the volumes in the Dockerfile that MTS doesn't write to (mprahl)
- Don't rely on default fedmsg configuration files in the container image (mprahl)
- Add Dockerfile for building prod image (Chenxiong Qi)
- Allow set None to a config (Chenxiong Qi)
- Refine configuration section in README (Chenxiong Qi)
- Fix consumer_topics in config (Chenxiong Qi)
- Install MTS and fedmsg.d config files (Chenxiong Qi)
- Fix grammar issues in README (Chenxiong Qi)
- Support multiple authtype to login a Koji session (Chenxiong Qi)
- Refactor fedmsg.d config (Chenxiong Qi)
- Convert README to RST format (Chenxiong Qi)
- Login koji session by calling koji_cli.lib.activate_session (Chenxiong Qi)
- Config update and reset methods. Extending tests for Config (Valerij Maljulin)
- Merge __getattr__ with __getitem__ in Config class (Valerij Maljulin)
- Adding support for profile parameter (Valerij Maljulin)
- Base class for configuration profiles (Valerij Maljulin)

0.2 (2019-01-22)
~~~~~~~~~~~~~~~~

- Add missing files to tarball generated by sdist

0.1 (2019-01-21)
~~~~~~~~~~~~~~~~

- First release that MTS is able to handle specific message to tag build.

