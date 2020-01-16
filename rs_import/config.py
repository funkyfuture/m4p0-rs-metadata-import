import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from pprint import pprint
from types import SimpleNamespace
from typing import List, Tuple

import yaml
from cerberus import TypeDefinition, Validator  # type: ignore

from rs_import import logging
from rs_import.constants import WEB_URL_PATTERN


class ImportSpecValidator(Validator):
    types_mapping = Validator.types_mapping.copy()
    types_mapping["path"] = TypeDefinition("path", (Path,), ())


import_spec_validator = ImportSpecValidator(
    schema={
        "entities_namespace": {"type": "string", "regex": WEB_URL_PATTERN + "/$"},
        "import_folders": {"type": "list", "schema": {"coerce": Path, "type": "path"}},
        "media_types": {
            "type": "dict",
            "keysrules": {"type": "string", "regex": "[a-z0-9]+"},
            "valuesrules": {"type": "string", "regex": WEB_URL_PATTERN},
        },
        "sparql_user": {"type": "string", "required": True, "empty": False},
        "sparql_pass": {"type": "string", "required": True, "empty": False},
        "sparql_endpoint": {"type": "string", "regex": WEB_URL_PATTERN},
        "verbosity": {"type": "integer", "allowed": (logging.DEBUG, logging.INFO)},
    }
)


def generate_config() -> Tuple[List[Path], SimpleNamespace]:
    cli_args = parse_cli_args()

    config_file_path = Path(cli_args.config).expanduser().resolve()
    with config_file_path.open("rt") as f:
        config_contents = yaml.load(f, Loader=yaml.SafeLoader)

    import_spec = import_spec_validator.validated(
        {
            **config_contents,
            "import_folders": cli_args.import_folder,
            "verbosity": [logging.INFO, logging.DEBUG][cli_args.verbose],
        }
    )

    if import_spec is None:
        print("The configuration data did not validate. These errors were reported:")
        pprint(import_spec_validator.errors)
        raise SystemExit(1)

    import_folders = import_spec.pop("import_folders")

    return import_folders, SimpleNamespace(**import_spec_validator.document)


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
        nargs="+",
        metavar="IMPORT_PATH",
        help="The folder(s) containing the import data.",
    )

    return parser.parse_args(args)


__all__ = (generate_config.__name__,)
