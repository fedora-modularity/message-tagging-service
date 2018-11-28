#!/usr/bin/python3
# This has been optimized for python3
#   print and urllib are different from python2

import fedmsg
import urllib.request
import yaml
import re

# Import fedmsg config file
config = fedmsg.config.load_config([], None)
config['mute'] = True
config['timeout'] = 0
config['topic'] = "org.fedoraproject.prod.mbs.module.state.change"

# Import message-tagger config file
config_stream = open('mts.module-rules.yaml', 'r')
this_config = yaml.load(config_stream)
config_stream.close()

def findDiffValue(d1, d2, spacer) :
			print("    %s Value: %s" % (spacer, d2))
			print("    %s regular variable: %s" % (spacer, d1))
			print("      %s Checking against: %s" % (spacer, d2))
			if isinstance(d2,list):
				list_check = False
				for list_value in d2 :
					print("        %s Checking against: %s" % (spacer, list_value))
					rule_pattern = re.compile(d1)
					if rule_pattern.match(str(list_value)) :
						this_destination = rule_pattern.sub(i["destinations"],str(list_value))
						final_destination.append(this_destination)
						print("          %s Passed" % (spacer))
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
					this_destination = rule_pattern.sub(i["destinations"],str(d2))
					final_destination.append(this_destination)
					print("  %s Passed" % (spacer))
					print("     %s this destination: %s" % (spacer,this_destination))
					return True
				else :
					print("  %s Failed" % (spacer))
					return False

def findDiffList(d1, d2, spacer) :
			print("    %s List: %s" % (spacer, d2))
			list_check = False
			for list_value in d1 :
				print("    %s list variable: %s" % (spacer, list_value))
				print("      %s Checking against: %s" % (spacer, d2))
				newspacer = "  %s" % (spacer)
				if findDiffValue(list_value, d2, newspacer) :
					list_check = True
			if list_check :
				print("  %s Passed" % (spacer))
				return True
			else :
				print("  %s Failed" % (spacer))
				return False


def findDiffDict(d1, d2, spacer) :
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
			return findDiffDict(value, newd2, newspacer)
		elif isinstance(value,list):
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDiffList(value, newd2, newspacer)
		else :
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDiffValue(value, newd2, newspacer)
			

for name, endpoint, topic, msg in fedmsg.tail_messages(**config):
	this_message=msg["msg"]
	print(name, this_message["state_name"])
	# print(fedmsg.encoding.pretty_dumps(msg))
	if this_message["state_name"] == "ready":
		this_name=this_message["name"]
		this_stream=this_message["stream"]
		this_version=this_message["version"]
		this_context=this_message["context"]
		this_modulemd_txt="https://kojipkgs.fedoraproject.org/packages/%s/%s/%s.%s/files/module/modulemd.txt" % (this_name, this_stream, this_version, this_context)
		print("  Downloading yaml file: %s" % (this_modulemd_txt))
		this_module_yaml_url = urllib.request.urlopen(this_modulemd_txt)
		this_module_yaml = yaml.load(this_module_yaml_url)
		print("    Yaml file downloaded and parsed.")
		# print(yaml.dump(this_module_yaml))
		for i in this_config:
			print("  Checking: %s" % (i["id"]))
			final_destination = []
			try:
				check_rule = i["rule"]
			except:
				final_destination.append(i["destinations"])
				print("    No rules found.  Thus we tag: %s" % (final_destination))
				break
			# print("    rules: %s" % (check_rule))
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
						#print("      Rule has a dictionary: %s" % (v))
						if findDiffDict(v, check_topkey[0], "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
					elif isinstance(v,list):
						#print("      Rule has a list/array: %s" % (v))
						if findDiffList(v, check_topkey, "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
					else :
						#print("      Rule has a regular variable: %s" % (v))
						if findDiffValue(v, check_topkey, "  ") :
							print("      Passed")
							print("        Final Destination(s): %s" % (final_destination))
						else :
							print("      Failed")
							tagit = False
							break
			if tagit :
				if len(final_destination) == 0 :
					final_destination.append(i["destinations"])
				print("  According to the rules, this should be tagged: %s" % (str(final_destination)))
				break
