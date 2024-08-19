import asyncio
import traceback
import logging
import pyglet

from .output import log
from .config import config
from .jsonify import JSON

import pydantic


async def main():
	from .matrix import client
	await client.initiate()
	

def run_as_a_module():
	exc = None

	try:
		asyncio.run(main())
	except Exception as e:
		exc = e
	finally:
		if exc:
			err = ''.join(traceback.format_exception(exc))
			log(err, level=logging.ERROR, fg="red")

			text = (
				'trixify experienced the above error. If you think this is a bug, please report it to\n'
				'https://github.com/Torxed/trixify and include the log file "/var/log/trixify/error.log".\n\n'
				'Hint: You can publish it via \ncurl -F\'file=@/var/log/trixify/error.log\' https://0x0.st\n'
			)

			log(text, level=logging.WARNING, fg="orange") and exit(1)