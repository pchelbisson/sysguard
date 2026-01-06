import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="DevOps Utility: system guard."
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
    ) 

    check_parser = subparsers.add_parser(
    "check",
    help="Check directory",
    )

    check_parser.add_argument(
    "--paths",
    nargs='+',
    help="multiple dir",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)


    if args.command == "check":
        directories = ["/var/log", "/etc"]

        for path in directories:
            if not os.path.exists(path):
                print(f"ERROR: {path} does not exist")
                sys.exit(1)

            elif not os.path.isdir(path):
                print(f"ERROR: {path} is not a directory")
                sys.exit(1)

            elif not os.access(path, os.R_OK):
                print(f"ERROR: Permission denied: {path}")
                sys.exit(1)
            elif not os.listdir(path):
                print(f"ERROR: {path} contains no log files")
                sys.exit(1)


            else:
                print(f"OK: {path} is accessible")

        sys.exit(0)




if __name__ == "__main__":
    main()