"""
pygitscrum argparse gestion
"""

import argparse
import importlib.metadata
import yaml 
from pathlib import Path

def get_all_categories(iterable):
    cats = set()
    for item in iterable:
        for c in item.get("categories", []):
            cats.add(c)
    return sorted(cats)

def get_env_report():
    lines = []

    lines.append("\nInstalled packages:")
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        version = dist.version
        lines.append(f"  - {name}=={version}")

    return "\n".join(lines)    


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter,argparse.HelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs == argparse.ONE_OR_MORE:
            return "%s" % get_metavar(1)
        else:
            return super(CustomHelpFormatter, self)._format_args(
                action, default_metavar
            )


def compute_args():
    """
    check args and return them
    """
    BASE_DIR = Path(__file__).resolve().parent
    yaml_path = BASE_DIR / "apps.yaml"

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    apps = config.get("commands", [])
    all_categories = get_all_categories(apps)
    my_parser = argparse.ArgumentParser(
        description="pydevversions",
        epilog=f"""
To upgrade, run:
    pipx upgrade pydevversions
    pipx reinstall pydevversions #to force update dependencies
To install, run:
    pipx install pydevversions
To force reinstall, run:
    pipx install pydevversions --force
To uninstall, run:
    pipx uninstall pydevversions
To force uninstall (if needed), run:
    pipx uninstall pydevversions --force

{get_env_report()}

Full documentation at: <https://github.com/thib1984/pydevversions>.
Report bugs to <https://github.com/thib1984/pydevversions/issues>.
MIT Licence.
Copyright (c) 2026 thib1984.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Written by thib1984.
        """,
        formatter_class=CustomHelpFormatter,
    )
    my_parser.add_argument(
        "--full",
        action="store_true",
        help="display all apps",
    ),  
    my_parser.add_argument(
        "--raw",
        action="store_true",
        help="raw output",
    ),   
    my_parser.add_argument(
        "--json",
        action="store_true",
        help="json output",
    ),       
    my_parser.add_argument(
        "-f",
        "--filter",
        action="store",
        type=str,
        metavar="app",
        help="filter on apps",
        nargs="+"
    )
    my_parser.add_argument(
        "-c",
        "--categories",
        action="store",
        type=str,
        metavar="app",
        help=f"filter on categories (available: {', '.join(all_categories)})",
        nargs="+"
    )
    my_parser.add_argument(
        "--compact",
        action="store_true",
        help="compact output with minimal version info",
    )        
    my_parser.add_argument(
        "-s",
        "--shell",
        action="store",
        type=str,
        metavar="shell",
        help="shell surchargé"
    )        
    args = my_parser.parse_args()
    return args
