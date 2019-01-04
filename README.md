# Message Tagging Service

Message tagging service is a microservice to tag build with proper tags, which
is triggered by specific message from a message bus. Currently, service
supports to tag module build according to a module build state change event.

This service works with Python 3.6 and 3.7.

## Workflow

This is the service workflow, for example of a module build.

- Listen on message bus (that is fedmsg in Fedora) and waiting for module build
  state change event. Only ``ready`` state is handled.
- Service consult to predefined rule definitions to check if that module build
  matches any rule.
- If one or more rules are matched, tag the module build with tags defined in
  matched rules.
- Send message to message bus to announce a module build is tagged with
  specific tags.

## Rule Definition

Rule definition is documented in a [Modularity document](https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md).

For detailed information of how the rules are matched, please refer to [paragraph](https://pagure.io/modularity/blob/master/f/drafts/module-tagging-service/format.md?text=True#_8) in that document.

## Configuration

There are two type of configurations.

- ``fedmsg.d/``: including config files for fedmsg hub. ``config.py`` configures
  fedmsg hub for service itself. ``mts.py`` enables defined consumer and
  configures to connect UMB accordingly.

- ``mts_config.py``: including configs for service. There are two sections,
  ``BaseConfiguration`` provides default options which could be reused for
  running in production. ``DevConfiguration`` contains anything for running in
  development mode.

## Enviornment Variables

### MTS_DRY_RUN

Dry run mode. Currently, no build is tagged actually in dry run mode. No
particular is required. Just define ``MTS_DRY_RUN`` in environment variables.

### MTS_DEV

Switch service to run in development mode as long as ``MTS_DEV`` is defined.

### MTS_RH

Make service run with internal infrastructure. No particular value is required.
Just define ``MTS_RH`` in environment variables. 

### MTS_STOMP_URI

A comma-separated string of UMB broker URIs. For example:

```
'messaging-broker01.dev1.redhat.com,messaging-broker02.dev2.redhat.com'
```

### MTS_STOMP_CRT

An absolute path to certificate file.

### MTS_STOMP_KEY

An absolute path to private key file.

Both of the certificate file and this private key file are required to connect
to internal UMB brokers.

## Contribution

Report issue at https://github.com/fedora-modularity/message-tagging-service/issues.

Before making a pull request, ensure the changes do not break anything and are
covered by tests. Run tests:

```
tox
```
