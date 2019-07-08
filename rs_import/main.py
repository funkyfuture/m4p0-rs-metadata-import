from traceback import print_exc

from rs_import.config import generate_config
from rs_import._import import DataSetImport
from rs_import.logging import set_console_log_level


def main():  # pragma: no cover
    try:
        import_folders, config = generate_config()
        set_console_log_level(config.verbosity)

        for import_folder in import_folders:
            dataset_import = DataSetImport(path=import_folder, config=config)
            dataset_import.run()

        exit_code = 0
    except SystemExit as e:
        exit_code = e.code
    except Exception:
        print("An unhandled exception occurred:\n")
        print_exc()
        exit_code = 3

    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
