from console.controller import ConsoleController
from database.schema import create_tables


def main() -> None:
    create_tables()

    controller = ConsoleController(
        sync_corporations_on_start=True,
    )
    controller.run()


if __name__ == "__main__":
    main()