import argparse
from pathlib import Path

from navl.file_tree_viewer import Settings


def create_parser():
    parser = argparse.ArgumentParser(description="Navigate file trees")
    parser.add_argument(
        "root_folder",
        nargs="?",
        default=".",
        help="Root path to navigate (default: current directory)",
        type=Path,
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_false",
        help="Disable gitignore filtering",
        default=True,
        dest="use_git_ignore",
    )
    return parser


def parse_args(args=None) -> Settings:
    parser = create_parser()
    args = parser.parse_args(args)

    return Settings(**vars(args))


def run():
    settings = parse_args()

    from navl.navl import main

    main(settings)


if __name__ == "__main__":
    run()
