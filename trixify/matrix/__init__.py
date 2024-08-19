#!/usr/bin/env python3

import asyncio
import traceback
from nio import (
	AsyncClient,
	AsyncClientConfig,
	InviteEvent,
	RoomMessageText,
	MatrixRoom,
	KeyVerificationEvent,
	KeyVerificationStart,
	KeyVerificationCancel,
	KeyVerificationKey,
	KeyVerificationMac,
	ToDeviceError,
)

from ..config import config
from ..output import log

_client = None


class MatrixBot(AsyncClient):
	def __init__(self, *args, **kwargs):
		super(MatrixBot, self).__init__(*args, **kwargs)

		self.restore_login(
			user_id=config.credentials.username,
			device_id=config.credentials.devicename,
			access_token=config.credentials.token
		)

		# auto-join room invites
		self.add_event_callback(self.join_room, InviteEvent)

		# print all the messages we receive
		self.add_event_callback(self.print_message, RoomMessageText)

	async def initiate(self, version_check):
		# from .keyverification import Callbacks
		# callbacks = Callbacks(self.client)
		# self.add_event_callback(callbacks.to_device_callback, KeyVerificationEvent)

		if self.should_upload_keys:
			await self.keys_upload()

		await self.sync(timeout=30000, full_state=True)

		loop = asyncio.get_event_loop()
		task = loop.create_task(
			version_check(
				self,
				{
					application_name: {
						"source" : application_obj.source,
						"git" : application_obj.git
					} for application_name, application_obj in config.watching.applications.items()
				}
			)
		)


	async def join_room(self, room :MatrixRoom, event :InviteEvent):
		print(event)
		_client.join(room.room_id)
		# room = _client.rooms[room.room_id]
		# log(f"Room {room.name} is encrypted: {room.encrypted}", fg="green")

	async def print_message(self, room :MatrixRoom, event: RoomMessageText):
		if event.decrypted:
			encrypted_symbol = "🛡 "
		else:
			encrypted_symbol = "⚠️ "
		log(
			f"{room.display_name} |{encrypted_symbol}| {room.user_name(event.sender)}: {event.body}"
		)

	async def send_message(self, room_id, content):
		"""Process message.

		Format messages according to instructions from command line arguments.
		Then send all messages to room_id.

		Arguments:
		---------
		room_id : str
		message : str
			message to send as read from -m, pipe or keyboard
			message is without mime formatting

		"""
		# remove leading AND trailing newlines to beautify
		# message = message.strip("\n")

		# if message == "" or message.strip() == "":
		# 	log(
		# 		"The message is empty. "
		# 		"This message is being droppend and NOT sent.", fg="gray")
		# 	return

		# content = {"msgtype": "m.text"}

		# if message_format == 'code':
		# 	log("Sending message in format \"code\".", fg="gray")
		# 	formatted_message = "<pre><code>" + message + "</code></pre>"
		# 	content["format"] = "org.matrix.custom.html"  # add to dict
		# 	content["formatted_body"] = formatted_message
		# elif message_format == 'markdown':
		# 	log("Converting message from MarkDown into HTML. "
		# 				 "Sending message in format \"markdown\".", fg="gray")
		# 	# e.g. converts from "-abc" to "<ul><li>abc</li></ul>"
		# 	formatted_message = markdown(message)
		# 	content["format"] = "org.matrix.custom.html"  # add to dict
		# 	content["formatted_body"] = formatted_message
		# elif message_format == 'html':
		# 	log("Sending message in format \"html\".", fg="gray")
		# 	formatted_message = message  # the same for the time being
		# 	content["format"] = "org.matrix.custom.html"  # add to dict
		# 	content["formatted_body"] = formatted_message
		# else:
		# 	log("Sending message in format \"text\".", fg="gray")

		# content["body"] = message

		try:
			await self.room_send(
				room_id,
				message_type="m.room.message",
				content=content,
				ignore_unverified_devices=True,
			)
			log(f"This message was sent: \"{content.get('body', None)}\" "
						 f"to room \"{room_id}\".", fg="gray")
		except Exception:
			log("Image send failed. Sorry. Here is the traceback.", fg="red")
			log(traceback.format_exc(), fg="red")

	async def run_forever(self):
		await self.sync_forever(timeout=30000, full_state=True)

		# Either way we're logged in here, too
		await self.close()


(config.general.root / "store").mkdir(parents=True, exist_ok=True)
client = MatrixBot(
	homeserver=config.general.homeserver,
	user=config.credentials.username,
	device_id=config.credentials.devicename,		
	store_path=config.general.root / "store",
	config=AsyncClientConfig(
		max_limit_exceeded=0,
		max_timeouts=0,
		store_sync_tokens=True,
		encryption_enabled=True,
	),
)