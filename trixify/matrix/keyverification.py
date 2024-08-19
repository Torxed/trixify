# from nio import (
# 	AsyncClient,
# 	AsyncClientConfig,
# 	InviteEvent,
# 	RoomMessageText,
# 	MatrixRoom,
# 	KeyVerificationEvent,
# 	KeyVerificationStart,
# 	KeyVerificationCancel,
# 	KeyVerificationKey,
# 	KeyVerificationMac,
# 	ToDeviceError,
# )
# class Callbacks(object):
# 	"""Class to pass client to callback methods."""

# 	def __init__(self, client):
# 		"""Store AsyncClient."""
# 		self.client = client

# 	async def to_device_callback(self, event):  # noqa
# 		log(f"Got key verification event: {event}")
# 		"""Handle events sent to device."""
# 		try:
# 			client = self.client

# 			if isinstance(event, KeyVerificationStart):  # first step
# 				""" first step: receive KeyVerificationStart
# 				KeyVerificationStart(
# 					source={'content':
# 							{'method': 'm.sas.v1',
# 							 'from_device': 'DEVICEIDXY',
# 							 'key_agreement_protocols':
# 								['curve25519-hkdf-sha256', 'curve25519'],
# 							 'hashes': ['sha256'],
# 							 'message_authentication_codes':
# 								['hkdf-hmac-sha256', 'hmac-sha256'],
# 							 'short_authentication_string':
# 								['decimal', 'emoji'],
# 							 'transaction_id': 'SomeTxId'
# 							 },
# 							'type': 'm.key.verification.start',
# 							'sender': '@user2:example.org'
# 							},
# 					sender='@user2:example.org',
# 					transaction_id='SomeTxId',
# 					from_device='DEVICEIDXY',
# 					method='m.sas.v1',
# 					key_agreement_protocols=[
# 						'curve25519-hkdf-sha256', 'curve25519'],
# 					hashes=['sha256'],
# 					message_authentication_codes=[
# 						'hkdf-hmac-sha256', 'hmac-sha256'],
# 					short_authentication_string=['decimal', 'emoji'])
# 				"""

# 				if "emoji" not in event.short_authentication_string:
# 					print("Other device does not support emoji verification "
# 						  f"{event.short_authentication_string}.")
# 					return
# 				resp = await client.accept_key_verification(
# 					event.transaction_id)
# 				if isinstance(resp, ToDeviceError):
# 					print(f"accept_key_verification failed with {resp}")

# 				sas = client.key_verifications[event.transaction_id]

# 				todevice_msg = sas.share_key()
# 				resp = await client.to_device(todevice_msg)
# 				if isinstance(resp, ToDeviceError):
# 					print(f"to_device failed with {resp}")

# 			elif isinstance(event, KeyVerificationCancel):  # anytime
# 				""" at any time: receive KeyVerificationCancel
# 				KeyVerificationCancel(source={
# 					'content': {'code': 'm.mismatched_sas',
# 								'reason': 'Mismatched authentication string',
# 								'transaction_id': 'SomeTxId'},
# 					'type': 'm.key.verification.cancel',
# 					'sender': '@user2:example.org'},
# 					sender='@user2:example.org',
# 					transaction_id='SomeTxId',
# 					code='m.mismatched_sas',
# 					reason='Mismatched short authentication string')
# 				"""

# 				resp = await client.cancel_key_verification(
# 					event.transaction_id, reject=False)
# 				if isinstance(resp, ToDeviceError):
# 					print(f"cancel_key_verification failed with {resp}")

# 			elif isinstance(event, KeyVerificationKey):  # second step
# 				""" Second step is to receive KeyVerificationKey
# 				KeyVerificationKey(
# 					source={'content': {
# 							'key': 'SomeCryptoKey',
# 							'transaction_id': 'SomeTxId'},
# 						'type': 'm.key.verification.key',
# 						'sender': '@user2:example.org'
# 					},
# 					sender='@user2:example.org',
# 					transaction_id='SomeTxId',
# 					key='SomeCryptoKey')
# 				"""
# 				sas = client.key_verifications[event.transaction_id]

# 				print(f"{sas.get_emoji()}")

# 				yn = input("Do the emojis match? (Y/N) ")
# 				if yn.lower() == "y":
# 					print("Match! Device will be verified "
# 						  "by accepting verification.")
# 					resp = await client.confirm_short_auth_string(
# 						event.transaction_id)
# 					if isinstance(resp, ToDeviceError):
# 						print(f"confirm_short_auth_string failed with {resp}")
# 				else:  # no, don't match, reject
# 					print("No match! Device will NOT be verified "
# 						  "by rejecting verification.")
# 					resp = await client.cancel_key_verification(
# 						event.transaction_id, reject=True)
# 					if isinstance(resp, ToDeviceError):
# 						print(f"confirm_short_auth_string failed with {resp}")
# 			elif isinstance(event, KeyVerificationMac):  # third step
# 				""" Third step is to receive KeyVerificationMac
# 				KeyVerificationMac(
# 					source={'content': {
# 						'mac': {'ed25519:DEVICEIDXY': 'SomeKey1',
# 								'ed25519:SomeKey2': 'SomeKey3'},
# 						'keys': 'SomeCryptoKey4',
# 						'transaction_id': 'SomeTxId'},
# 						'type': 'm.key.verification.mac',
# 						'sender': '@user2:example.org'},
# 					sender='@user2:example.org',
# 					transaction_id='SomeTxId',
# 					mac={'ed25519:DEVICEIDXY': 'SomeKey1',
# 						 'ed25519:SomeKey2': 'SomeKey3'},
# 					keys='SomeCryptoKey4')
# 				"""
# 				sas = client.key_verifications[event.transaction_id]
# 				todevice_msg = sas.get_mac()
# 				resp = await client.to_device(todevice_msg)
# 				if isinstance(resp, ToDeviceError):
# 					print(f"to_device failed with {resp}")
# 				print(f"sas.we_started_it = {sas.we_started_it}\n"
# 					  f"sas.sas_accepted = {sas.sas_accepted}\n"
# 					  f"sas.canceled = {sas.canceled}\n"
# 					  f"sas.timed_out = {sas.timed_out}\n"
# 					  f"sas.verified = {sas.verified}\n"
# 					  f"sas.verified_devices = {sas.verified_devices}\n")
# 				print("Emoji verification was successful.\n"
# 					  "Hit Control-C to stop the program or "
# 					  "initiate another Emoji verification from "
# 					  "another device or room.")
# 			else:
# 				print(f"Received unexpected event type {type(event)}. "
# 					  f"Event is {event}. Event will be ignored.")
# 		except BaseException:
# 			print(traceback.format_exc())