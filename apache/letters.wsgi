#!/usr/bin/python
import sys
import logging
# Debugging
from werkzeug.debug import DebuggedApplication
application = DebuggedApplication(letters, True)
letters.debug = True

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/root/var/www/letters")

from letters import app as application
application.debug = True
application.secret_key = 'ASdd your secret key'
