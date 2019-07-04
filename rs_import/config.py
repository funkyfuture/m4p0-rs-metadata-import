import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from pprint import pprint
from types import SimpleNamespace
from typing import List

import yaml
from cerberus import TypeDefinition, Validator  # type: ignore

from rs_import import logging


class ConfigValidator(Validator):
    types_mapping = Validator.types_mapping.copy()
    types_mapping["path"] = TypeDefinition("path", (Path,), ())


config_validator = ConfigValidator(
    schema={
        "import_folders": {"type": "list", "schema": {"coerce": Path, "type": "path"}},
        "sparql_endpoint": {"type": "string", "regex": "^https://.*"},
        "verbosity": {"type": "integer", "allowed": (logging.DEBUG, logging.INFO)},
    }
)


def generate_config() -> SimpleNamespace:
    cli_args = parse_cli_args()

    config_file_path = Path(cli_args.config).expanduser().resolve()
    with config_file_path.open("rt") as f:
        config_contents = yaml.load(f, Loader=yaml.SafeLoader)

    config_data = {
        "import_folders": cli_args.import_folder,
        "verbosity": [logging.INFO, logging.DEBUG][cli_args.verbose],
        **config_contents,
    }

    if not config_validator.validate(config_data):
        print("The configuration data did not validate. These errors were reported:")
        pprint(config_validator.errors)
        raise SystemExit(1)

    return SimpleNamespace(**config_validator.document)


def parse_cli_args(args: List[str] = sys.argv[1:]) -> Namespace:
    parser = ArgumentParser(
        description="This tool takes the contents of the specified import folders, "
        "transforms them into SPARQL statements and submits these to a SPARQL "
        "endpoint. Please refer to the supplied specification and usage documentation "
        "for details."
    )
    parser.add_argument(
        "--config",
        default="~/.rs-import.yml",
        metavar="PATH",
        help="The path to the configuration file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Increases verbosity to DEBUG level.",
    )
    parser.add_argument(
        "import_folder",
        action="append",
        metavar="IMPORT_PATH",
        help="The folder(s) containing the import data.",
    )

    return parser.parse_args(args)


__all__ = (generate_config.__name__,)
