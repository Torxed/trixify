import pathlib
import argparse


parser = argparse.ArgumentParser(description="A set of common parameters for the tooling", add_help=False)

parser.add_argument("--config", nargs="?", help="Which config to load, defaults to ~/.config/trixify/config.toml", default=pathlib.Path("~/.config/trixify/config.toml"), type=pathlib.Path)

args, unknowns = parser.parse_known_args()