#!/usr/bin/python3

import json
import os
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

def findDiffValue(d1, d2, td, fd, spacer) :
			print("    %s Value: %s" % (spacer, d2))
			print("    %s regular variable: %s" % (spacer, d1))
			print("      %s Checking against: %s" % (spacer, d2))
			if isinstance(d2,list):
				print("      %s List: %s" % (spacer, d2))
				list_check = False
				for list_value in d2 :
					print("        %s Checking against: %s" % (spacer, list_value))
					rule_pattern = re.compile(d1)
					if rule_pattern.match(str(list_value)) :
						print("          %s Passed" % (spacer))
						this_destination = rule_pattern.sub(td,str(list_value))
						fd.append(this_destination)
						print("            %s this destination: %s" % (spacer,this_destination))
						list_check = True
					else :
						print("          %s Failed" % (spacer))
				if list_check :
					print("  %s Passed" % (spacer))
					return True
				else :
					print("  %s Failed" % (spacer))
					return False
			else :
				rule_pattern = re.compile(d1)
				if rule_pattern.match(str(d2)) :
					this_destination = rule_pattern.sub(td,str(d2))
					fd.append(this_destination)
					print("  %s Passed" % (spacer))
					print("     %s this destination: %s" % (spacer,this_destination))
					return True
				else :
					print("  %s Failed" % (spacer))
					return False

def findDiffList(d1, d2, td, fd, spacer) :
			print("    %s List: %s" % (spacer, d2))
			list_check = False
			for list_value in d1 :
				print("    %s list variable: %s" % (spacer, list_value))
				print("      %s Checking against: %s" % (spacer, d2))
				newspacer = "  %s" % (spacer)
				if findDiffValue(list_value, d2, td, fd, newspacer) :
					list_check = True
			if list_check :
				print("  %s Passed" % (spacer))
				return True
			else :
				print("  %s Failed" % (spacer))
				return False


def findDiffDict(d1, d2, td, fd, spacer) :
	print("    %s Dict: %s" % (spacer, d2))
	for key, value in d1.items():
		try :
			newd2 = d2[key]
		except:
			print("    %s Not found in module: %s" % (spacer, key))
			return False
		if isinstance(value,dict):
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDiffDict(value, newd2, td, fd, newspacer)
		elif isinstance(value,list):
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDiffList(value, newd2, td, fd, newspacer)
		else :
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDiffValue(value, newd2, td, fd, newspacer)

def tagBuild(message, fd) :
	print("    Tagging Package")
	## The koji code works, but it is commented out
	##   due to permissions of tags and packages.
	## Uncomment out the koji_session lines when tags
	##   and permissions have been figured out
	# koji_session = koji.ClientSession(koji_config.server, opts=koji_config.__dict__)
	# koji_session.ssl_login(cert='/home/quake/tmp/message-tagger/internal/msg-tagger.pem')
	this_nvr = message["name"] + '-' + message["stream"].replace('-', '_') + '-' + message["version"] + '.' + message["context"]
	for this_tag in fd :
		print("      tag: %s nvr: %s" % (this_tag, this_nvr))
		# koji_session.tagBuild(this_tag, this_nvr)
	# koji_session.logout()
	print("    Sending message on message bus")
	this_body = {}
	this_body['name'] = message["name"]
	this_body['stream'] = message["stream"].replace('-', '_')
	this_body['version'] = message["version"]
	this_body['context'] = message["context"]
	this_body['nvr'] = this_nvr
	this_body['destination'] = fd
	producer = AMQProducer(**message_config)
	producer.through_topic(mts_conf['msg_topic_send'])
	mb_message = proton.Message()
	mb_message.subject = "tagging:" + message["name"]
	mb_message.body = this_body
	producer.send(mb_message)
	print
	

def message_handler(message, data):
	this_message = json.loads(message.body)
	print(this_message["name"], this_message["state_name"])
	if this_message["state_name"] == "ready":
		this_name=this_message["name"]
		this_stream=this_message["stream"].replace('-', '_')
		this_version=this_message["version"]
		this_context=this_message["context"]
		this_modulemd_txt="%s/%s/%s/%s.%s/files/module/modulemd.txt" % (mts_conf['mod_url_header'], this_name, this_stream, this_version, this_context)
		print("  Downloading yaml file: %s" % (this_modulemd_txt))
		try:
			this_module_yaml_url = urllib.request.urlopen(this_modulemd_txt)
		except:
			print("      Unable to find yaml file for module.")
			return data['one_message_only'], not data['manual_ack']
		this_module_yaml = yaml.load(this_module_yaml_url)
		print("    Yaml file downloaded and parsed.")
		# print(yaml.dump(this_module_yaml))
		for this_rule in this_config:
			print("  Checking: %s" % (this_rule["id"]))
			final_destination = []
			try:
				check_rule = this_rule["rule"]
			except:
				final_destination.append(this_rule["destinations"])
				print("    No rules found.  Thus we tag: %s" % (final_destination))
				tagBuild(this_message, final_destination)
				break
			for k, v in check_rule.items():
				tagit = True
				print("    Rule/Value: %s : %s" % (k, v))
				## Check the Booleans first
				# Check if it is scratch
				if k == 'scratch' :
					try:
						check_value = this_module_yaml["data"]["scratch"]
					except:
						check_value = False
					if v != check_value :
						print("      Failed")
						tagit = False
						break
					else :
						print("      Passed")
				# Check if it is Development
				elif k == 'development':
					try:
						check_value = this_module_yaml["data"]["development"]
					except:
						check_value = False
					if v != check_value :
						print("      Failed")
						tagit = False
						break
					else :
						print("      Passed")
				## Now check rules that have regix
				else :
					try:
						check_topkey = this_module_yaml["data"][k]
					except:
						print("      Failed : %s not found." % (k))
						tagit = False
						break
					if isinstance(v,dict):
						if findDiffDict(v, check_topkey[0], this_rule["destinations"], final_destination, "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
					elif isinstance(v,list):
						if findDiffList(v, check_topkey, this_rule["destinations"], final_destination, "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
					else :
						if findDiffValue(v, check_topkey, this_rule["destinations"], final_destination, "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
			if tagit :
				if len(final_destination) == 0 :
					final_destination.append(this_rule["destinations"])
				print("  According to the rules, this should be tagged: %s" % (str(final_destination)))
				tagBuild(this_message, final_destination)
				break
	return data['one_message_only'], not data['manual_ack']

consumer = AMQConsumer(**message_config)
consumer.consume(mts_conf['msg_topic_listen'],
  selector=None,
  callback=message_handler,
  auto_accept=False,
  data={'dump': True,
        'pp': False,
        'one_message_only': False,
        'manual_ack': False,
        })
