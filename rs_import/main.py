from traceback import print_exc

from rs_import.config import generate_config
from rs_import.logging import log, set_console_log_level


def main():  # pragma: no cover
    try:
        import_folders, config = generate_config()
        set_console_log_level(config.verbosity)

        exit_code = 0
    except SystemExit as e:
        exit_code = e.code
    except Exception:
        print("An unhandled exception occured:\n")
        print_exc()
        exit_code = 3

    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
