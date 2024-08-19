import typing
import json
import datetime
import enum
import pathlib
import pydantic

def jsonify(obj :typing.Any, safe :bool=True, ignore_None=True) -> typing.Any:
	"""
	Converts almost any standard object into json.dumps() compatible nested dictionaries.
	Setting safe to True skips dictionary keys starting with a bang (!)

	Performs recursive conversion too.
	"""

	compatible_types = str, int, float, bool
	if isinstance(obj, dict):
		return {
			jsonify(key, safe): jsonify(value, safe)
			for key, value in obj.items()
			if isinstance(jsonify(key, safe), compatible_types)
			and not (isinstance(key, str) and key.startswith("!") and safe)
			and not (ignore_None is True and value is None)
		}
	elif isinstance(obj, enum.Enum):
		return obj.value
	elif hasattr(obj, '_dump'):
		print(f"obj has _dump()")
		return jsonify(obj._dump(), safe)
	elif isinstance(obj, pydantic.BaseModel):
		print(type(obj), obj)
		conversion_level = obj.model_dump(mode='python')
		for key, val in conversion_level.items():
			# print(f"Trying to preserve {key}: {getattr(obj, key).__class__.__name__}({getattr(obj, key)})")
			if isinstance(getattr(obj, key), pydantic.BaseModel):
				# print(f" Calling jsonify() on it")
				val = jsonify(getattr(obj, key), safe=safe, ignore_None=ignore_None)
			conversion_level[key] = val
		return jsonify(conversion_level, safe=safe, ignore_None=ignore_None)
	elif hasattr(obj, 'model_dump'):
		return jsonify(obj.model_dump(mode='python'), safe)
	elif hasattr(obj, 'json'):
		return jsonify(obj.json(), safe)
	elif hasattr(obj, 'to_dict'):
		return jsonify(obj.to_dict(), safe)
	elif isinstance(obj, (datetime.datetime, datetime.date)):
		return obj.isoformat()
	elif isinstance(obj, (list, set, tuple)):
		return [jsonify(item, safe) for item in obj]
	elif isinstance(obj, pathlib.Path):
		return str(obj)
	elif hasattr(obj, "__dict__"):
		return vars(obj)

	return obj

class JSON(json.JSONEncoder, json.JSONDecoder):
	"""
	This is the entrypoint to `jsonify`.
	"""

	def encode(self, obj: typing.Any) -> str:
		return super().encode(jsonify(obj))