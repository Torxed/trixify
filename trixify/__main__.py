import importlib
import sys
import pathlib

# Load .git version before the builtin version
if pathlib.Path('./trixify/__init__.py').absolute().exists():
	spec = importlib.util.spec_from_file_location("trixify", "./trixify/__init__.py")

	if spec is None or spec.loader is None:
		raise ValueError('Could not retrieve spec from file: trixify/__init__.py')

	trixify = importlib.util.module_from_spec(spec)
	sys.modules["trixify"] = trixify
	spec.loader.exec_module(trixify)
else:
	import trixify

if __name__ == '__main__':
	trixify.run_as_a_module()
