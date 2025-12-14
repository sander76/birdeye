import argparse
import logging
from pathlib import Path

from birdeye.file_tree_viewer import Settings


def setup_logging():
    root = logging.getLogger()
    handler = logging.FileHandler("birdeye.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)


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

    from birdeye.birdeye import main

    main(settings)


if __name__ == "__main__":
    setup_logging()
    run()
