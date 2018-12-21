#!/usr/bin/python3

import json
import urllib.request
import yaml
import re
import proton
import koji
import mts_config

from rhmsg.activemq.consumer import AMQConsumer
from rhmsg.activemq.producer import AMQProducer

broker_envs = mts_config.broker_envs
mts_conf = mts_config.mts_conf

# Import message-tagger rule file
config_stream = open(mts_conf['rule_file'], 'r')
this_config = yaml.load(config_stream)
config_stream.close()

# Import koji config
koji_config = koji.get_profile_module(mts_conf['koji_profile']).config

# Setup messaging configuration
message_config = {
  'urls': broker_envs[mts_conf['msg_enviroment']],
  'certificate': mts_conf['msg_certificate'],
  'private_key': mts_conf['msg_private_key'],
  'trusted_certificates': mts_conf['msg_trusted_certificates'],
}


def findDiffValue(d1, d2, td, fd, spacer):
    print("    %s Value: %s" % (spacer, d2))
    print("    %s regular variable: %s" % (spacer, d1))
    print("      %s Checking against: %s" % (spacer, d2))
    if isinstance(d2, list):
        print("      %s List: %s" % (spacer, d2))
        list_check = False
        for list_value in d2:
            print("        %s Checking against: %s" % (spacer, list_value))
            rule_pattern = re.compile(d1)
            if rule_pattern.match(str(list_value)):
                print("          %s Passed" % spacer)
                list_check = True
                try:
                    this_destination = rule_pattern.sub(td, str(list_value))
                    fd.append(this_destination)
                    print("            %s this destination: %s" % (spacer, this_destination))
                except Exception:
                    print("            %s this destination same as last one." % spacer)
            else:
                print("          %s Failed" % spacer)
        if list_check:
            print("  %s Passed" % spacer)
            return True
        else:
            print("  %s Failed" % spacer)
            return False
    else:
        rule_pattern = re.compile(d1)
        if rule_pattern.match(str(d2)):
            print("  %s Passed" % spacer)
            try:
                this_destination = rule_pattern.sub(td, str(d2))
                fd.append(this_destination)
                print("     %s this destination: %s" % (spacer, this_destination))
            except Exception:
                print("            %s this destination same as last one." % spacer)
            return True
        else:
            print("  %s Failed" % spacer)
            return False


def findDiffList(d1, d2, td, fd, spacer):
    print("    %s List: %s" % (spacer, d2))
    list_check = False
    for list_value in d1:
        print("    %s list variable: %s" % (spacer, list_value))
        print("      %s Checking against: %s" % (spacer, d2))
        newspacer = "  %s" % spacer
        if findDiffValue(list_value, d2, td, fd, newspacer):
            list_check = True
        else:
            return False
    if list_check:
        print("  %s Passed" % spacer)
        return True
    else:
        print("  %s Failed" % spacer)
        return False


def findDiffDict(d1, d2, td, fd, spacer):
    print("    %s Dict: %s" % (spacer, d2))
    dict_check = False
    for key, value in d1.items():
        newd2 = d2.get(key)
        if newd2 is None:
            print("    %s Not found in module: %s" % (spacer, key))
            return False
        if isinstance(value, dict):
            print("  %s Checking: %s" % (spacer, key))
            newspacer = "  %s" % spacer
            if findDiffDict(value, newd2, td, fd, newspacer):
                dict_check = True
            else:
                return False
        elif isinstance(value, list):
            print("  %s Checking: %s" % (spacer, key))
            newspacer = "  %s" % spacer
            if findDiffList(value, newd2, td, fd, newspacer):
                dict_check = True
            else:
                return False
        else:
            print("  %s Checking: %s" % (spacer, key))
            newspacer = "  %s" % spacer
            if findDiffValue(value, newd2, td, fd, newspacer):
                dict_check = True
            else:
                return False
    return dict_check


def tagBuild(message, fd):
    print("    Tagging Package")
    koji_session = koji.ClientSession(koji_config.server,
                                      opts=koji_config.__dict__)
    koji_session.ssl_login(cert=mts_conf['koji_cert'])
    this_nvr = '{}-{}-{}.{}'.format(message["name"],
                                    message["stream"].replace('-', '_'),
                                    message["version"],
                                    message["context"])
    for this_tag in fd:
        print("      tag: %s nvr: %s" % (this_tag, this_nvr))
        try:
            koji_session.tagBuild(this_tag, this_nvr)
        except Exception:
            print("        Unable to tag.")
    koji_session.logout()
    print("    Sending message on message bus")
    this_body = {
        'name': message["name"],
        'stream': message["stream"].replace('-', '_'),
        'version': message["version"],
        'context': message["context"],
        'nvr': this_nvr,
        'destination': fd,
    }
    producer = AMQProducer(**message_config)
    producer.through_topic(mts_conf['msg_topic_send'])
    mb_message = proton.Message()
    mb_message.subject = "tagging:" + message["name"]
    mb_message.body = this_body
    producer.send(mb_message)
    print("      Message sent.")


def message_handler(message, data):
    this_message = json.loads(message.body)
    print(this_message["name"], this_message["state_name"])
    if this_message["state_name"] == "ready":
        this_name = this_message["name"]
        this_stream = this_message["stream"].replace('-', '_')
        this_version = this_message["version"]
        this_context = this_message["context"]
        this_modulemd_txt = "%s/%s/%s/%s.%s/files/module/modulemd.txt" % (
            mts_conf['mod_url_header'], this_name, this_stream, this_version, this_context)
        print("  Downloading yaml file: %s" % this_modulemd_txt)
        try:
            # FIXME: use requests
            this_module_yaml_url = urllib.request.urlopen(this_modulemd_txt)
        except Exception:
            print("      Unable to find yaml file for module.")
            return data['one_message_only'], not data['manual_ack']
        this_module_yaml = yaml.load(this_module_yaml_url)
        print("    Yaml file downloaded and parsed.")
        # print(yaml.dump(this_module_yaml))
        for this_rule in this_config:
            print("  Checking: %s" % (this_rule["id"]))
            final_destination = []
            check_rule = this_rule.get("rule")
            if check_rule is None:
                final_destination.append(this_rule["destinations"])
                print("    No rules found.  Thus we tag: %s" % final_destination)
                tagBuild(this_message, final_destination)
                break
            for k, v in check_rule.items():
                tagit = True
                print("    Rule/Value: %s : %s" % (k, v))
                # Check the Booleans first
                # Check if it is scratch
                if k == 'scratch':
                    check_value = this_module_yaml["data"].get("scratch", False)
                    if v != check_value:
                        print("      Failed")
                        tagit = False
                        break
                    else:
                        print("      Passed")
                # Check if it is Development
                elif k == 'development':
                    check_value = this_module_yaml["data"].get("development", False)
                    if v != check_value:
                        print("      Failed")
                        tagit = False
                        break
                    else:
                        print("      Passed")
                # Now check rules that have regix
                else:
                    check_topkey = this_module_yaml["data"].get(k)
                    if check_topkey is None:
                        print("      Failed : %s not found." % k)
                        tagit = False
                        break
                    if isinstance(v, dict):
                        if findDiffDict(v, check_topkey[0], this_rule["destinations"],
                                        final_destination, "  "):
                            print("      Passed")
                            print("        Final Destination(s): %s" % final_destination)
                        else:
                            print("      Failed")
                            tagit = False
                            break
                    elif isinstance(v, list):
                        if findDiffList(v, check_topkey, this_rule["destinations"],
                                        final_destination, "  "):
                            print("      Passed")
                            print("        Final Destination(s): %s" % (final_destination))
                        else:
                            print("      Failed")
                            tagit = False
                            break
                    else:
                        if findDiffValue(v, check_topkey, this_rule["destinations"],
                                         final_destination, "  "):
                            print("      Passed")
                            print("        Final Destination(s): %s" % final_destination)
                        else:
                            print("      Failed")
                            tagit = False
                            break
            if tagit:
                if len(final_destination) == 0:
                    final_destination.append(this_rule["destinations"])
                print("  According to the rules, this should be tagged: %r" % final_destination)
                tagBuild(this_message, final_destination)
                break
    return data['one_message_only'], not data['manual_ack']


consumer = AMQConsumer(**message_config)
consumer.consume(
    mts_conf['msg_topic_listen'],
    selector=None,
    callback=message_handler,
    auto_accept=False,
    data={
        'dump': True,
        'pp': False,
        'one_message_only': False,
        'manual_ack': False
    }
)
