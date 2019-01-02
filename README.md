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

## Contribution

Report issue at https://github.com/fedora-modularity/message-tagging-service/issues.

Before making a pull request, ensure the changes do not break anything and are
covered by tests. Run tests:

```
tox
```
