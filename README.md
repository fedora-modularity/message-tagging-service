# message-tagging-service
Tag koji builds with the correct tags, triggered by the message bus

This is still a prototype.  It does not do any actual tagging.  But it tells you what it would tag the module build as.

This works with python3 only.  
You need the python3 fedmsg libraries.
To convert to python2 you need to change print and urllib

Usage: ./message-tagging-service.py
