from database import create_tables
from monitor import check_saved_trips


def main():
    create_tables()
    check_saved_trips()


if __name__ == "__main__":
    main()
