from traceback import print_exc

from rs_import.config import generate_config


def main():  # pragma: no cover
    try:
        config = generate_config()

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
