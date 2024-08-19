# Remove this monster when all supported OS runs Python 3.11 or higher (3.12 is out, 3.13 is in testing at the moment \*hint hint\*)
try:
	import tomllib
	toml_mode = 'rb'
except:
	import toml as tomllib
	toml_mode = 'r'

import sysconfig
import os
import json
import pathlib
import pydantic
import typing
import cryptography.x509
import cryptography.hazmat.backends
import cryptography.hazmat.bindings

from .jsonify import JSON
from .arguments import args
from .models.userid import UserID

# Create sane default paths for OpenSC PKCS#11 library and config.toml config
if os.name == 'nt':
	default_config_path = pathlib.Path(args.config).expanduser().resolve().absolute()
	default_cache_path = pathlib.Path(r'./trixify_cache').expanduser().resolve().absolute()
else:
	default_config_path = pathlib.Path(args.config).expanduser().resolve().absolute()
	default_cache_path = pathlib.Path(r'~/.cache/trixify').expanduser().resolve().absolute()


class TrixConf(pydantic.BaseModel, arbitrary_types_allowed=True):
	"""
	The [general] part of the config.toml config
	"""
	homeserver :str
	room :str
	root :pathlib.Path = default_cache_path

	@pydantic.field_validator("root")
	def validate_root(cls, value):
		if (value := value.expanduser().resolve().absolute()).exists() is False:
			try:
				value.mkdir(parents=True)
			except:
				raise PermissionError(f"root directory for caching e-mails is not accessible: {value}")

		return value

	@pydantic.field_validator("homeserver")
	def validate_homeserver(cls, value):
		if not value.startswith('https://') and not value.startswith('http://'):
			value = f"https://{value}"

		return value


class Credentials(pydantic.BaseModel, arbitrary_types_allowed=True):
	"""
	The [credentials] part of the config.toml config
	You can generate a token with:
	  curl -XPOST -d '{"type": "m.login.password", "identifier": {"user": "uptime", "type": "m.id.user"}, "password": "your-personal-password", "initial_device_display_name": "trixify"}' "https://homeserver.domain/_matrix/client/v3/login"
	"""
	username :str
	token :str
	devicename :str


class ApplicationConfig(pydantic.BaseModel):
	source :str
	users :typing.List[UserID] | None = None
	git :str|None = None


class WatchList(pydantic.BaseModel):
	applications :typing.Dict[str, ApplicationConfig]

	@pydantic.model_validator(mode="before")
	def cleanup_data(cls, values):
		return {
			"applications" : values
		}

	def __getitem__(self, key):
		return self.applications[key]


class Config(pydantic.BaseModel):
	"""
	Defines the sections of config.toml, such as [credentials] and [general].
	These are the valid section headers, and they are define in :class:`Credentials`, :class:`TrixConf`
	"""
	general :TrixConf
	credentials :Credentials
	watching :WatchList

	@pydantic.model_validator(mode="after")
	def validate_config(self):
		print(f"Trying the access token")
		return self


# Load the default config path, or as a last resort attempt ./config.toml
if ((conf_file := default_config_path) if default_config_path.exists() else (conf_file := pathlib.Path('./trixify.toml').resolve())).exists():
	print(f"Using config file {conf_file}")
	with conf_file.open(toml_mode) as fh:
		conf_data = tomllib.load(fh)
else:
	raise PermissionError(f"Cannot start without a configuration")


# From here on, we can do :code:`from .config import config` and it will stay initated.
config = Config(**conf_data)