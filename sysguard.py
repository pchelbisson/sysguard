import argparse

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

    if args.command == "check":
        print(args.paths)


if __name__ == "__main__":
    main()