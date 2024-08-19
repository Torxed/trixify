__version__ = "0.1"


import asyncio
import traceback
import logging

from .output import log
from .config import config
from .jsonify import JSON

import pydantic
import asyncio
from nvchecker import core
from nvchecker import __main__ as main
from nvchecker.util import Entries, ResultData, RawResult


async def check_versions(client, entries):
	oldvers :ResultData = {}

	while True:
		max_concurrency = 10
		result_q: asyncio.Queue[RawResult] = asyncio.Queue()
		
		entry_waiter = core.EntryWaiter()
		task_sem = asyncio.Semaphore(max_concurrency)
		keymanager = core.KeyManager(None)
		dispatcher = core.setup_httpclient()
		futures = dispatcher.dispatch(
			entries, task_sem, result_q,
			keymanager, entry_waiter, 1, {},
		)

		result_coro = core.process_result(oldvers, result_q, entry_waiter)
		runner_coro = core.run_tasks(futures)

		results, _has_failures = await main.run(result_coro, runner_coro)
		
		#if len(oldvers) != 0:
		for application in results:
			if results.get(application, None) != oldvers.get(application, None):
				await client.send_message(
					config.general.room,
					{
						"msgtype": "m.text",
						"body": f"{','.join(["@"+str(user.friendly_name) for user in config.watching[application].users])} - New version of {application}: {results[application].version}",
						"format": "org.matrix.custom.html",
						"formatted_body": ','.join([f'<a href="https://matrix.to/#/{user.full_id}">@{user.friendly_name}</a>' for user in config.watching[application].users]) + f": New version of {application} ({results[application].version})",
					}
				)

		oldvers = results

		await asyncio.sleep(config.general.check_interval)


async def entrypoint():
	from .matrix import client

	await client.initiate(check_versions)
	await client.run_forever()
	

def run_as_a_module():
	exc = None

	try:
		asyncio.run(entrypoint())
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