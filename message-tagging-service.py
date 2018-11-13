import fedmsg
import urllib
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

def findDictDiff(d1, d2, spacer) :
	for key, value in d1.items():
		try :
			newd2 = d2[key]
		except:
			print("    %s Not found in module: %s" % (spacer, key))
			return False
		if isinstance(value,dict):
			print("  %s Checking: %s" % (spacer, key))
			newspacer = "  %s" % (spacer)
			return findDictDiff(value, newd2, newspacer)
		elif isinstance(value,list):
			print("  %s Checking: %s" % (spacer, key))
			list_check = False
			for list_value in value :
				print("    %s list variable: %s" % (spacer, list_value))
				print("      %s Checking against: %s" % (spacer, d2))
				rule_pattern = re.compile(list_value)
				if rule_pattern.match(str(d2)) :
					print("        %s Passed" % (spacer))
					list_check = True
					break
				else :
					print("        %s Failed" % (spacer))
			if list_check :
				print("  %s Passed" % (spacer))
				return True
			else :
				print("  %s Failed" % (spacer))
				return False
		else :
			print("    %s regular variable: %s" % (spacer, value))
			print("      %s Checking against: %s" % (spacer, newd2))
			if isinstance(newd2,list):
				list_check = False
				for list_value in newd2 :
					print("        %s Checking against: %s" % (spacer, list_value))
					rule_pattern = re.compile(value)
					if rule_pattern.match(str(list_value)) :
						print("        %s Passed" % (spacer))
						list_check = True
						break
					else :
						print("        %s Failed" % (spacer))
				if list_check :
					print("  %s Passed" % (spacer))
					return True
				else :
					print("  %s Failed" % (spacer))
					return False
			else :
				rule_pattern = re.compile(value)
				if rule_pattern.match(str(newd2)) :
					print("  %s Passed" % (spacer))
					return True
				else :
					print("  %s Failed" % (spacer))
					return False
			

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
		this_module_yaml_url = urllib.urlopen(this_modulemd_txt)
		this_module_yaml = yaml.load(this_module_yaml_url)
		print("    Yaml file downloaded and parsed.")
		# print(yaml.dump(this_module_yaml))
		for i in this_config :
			print("  Checking: %s" % (i["id"]))
			try:
				check_rule = i["rule"]
			except:
				print("    No rules found.  Thus we tag: %s" % (i["destinations"]))
				break
			print("    rules: %s" % (check_rule))
			for k, v in check_rule.items():
				tagit = True
				print("    Rule/Value: %s : %s" % (k, v))
				## Check the Booleans first
				# Check scratch
				if k == 'scratch':
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
				# Check Development
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
						print("      Rule has a dictionary: %s" % (v))
						dist_check = findDictDiff(v, check_topkey[0], "  ")
						if dist_check :
							print("      Passed")
						else :
							print("      Failed")
							tagit = False
							break
					elif isinstance(v,list):
						print("      Rule has a list/array: %s" % (v))
						list_check = False
						for list_value in v :
							print("        list variable: %s" % (list_value))
							print("          Checking against: %s" % (check_topkey))
							rule_pattern = re.compile(list_value)
							if rule_pattern.match(str(check_topkey)) :
								print("        Passed")
								list_check = True
								break
							else :
								print("        Failed")
						if list_check :
							print("      Passed")
						else :
							print("      Failed")
							tagit = False
							break
					else :
						print("      Rule has a regular variable: %s" % (v))
						print("        Checking against: %s" % (check_topkey))
						rule_pattern = re.compile(v)
						if rule_pattern.match(str(check_topkey)) :
							print("      Passed")
						else :
							print("      Failed")
							tagit = False
							break
			if tagit :
				print("    According to the rules, this should be tagged: %s" % (i["destinations"]))
				break
