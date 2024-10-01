#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Utility for managing LLM task->model configurations in ~/.config/llm-manager/llm.conf and /etc/llm.conf.
#

import argparse
import os
import sys
import pwd
from pathlib import Path
from typing import Dict, List

VERSION = "1.1.0"


def get_user_config_file() -> Path:
    """
    Get the path to the user's configuration file, handling cases where the script is run with sudo.
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            user_info = pwd.getpwnam(sudo_user)
            home_dir = user_info.pw_dir
        except KeyError:
            print(
                f"Error: Cannot find home directory for sudo user '{sudo_user}'.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        home_dir = os.environ.get("HOME", str(Path.home()))
    return Path(home_dir) / ".config" / "llm-manager" / "llm.conf"


USER_CONFIG_FILE = get_user_config_file()
SYSTEM_CONFIG_FILE = Path("/etc/llm.conf")

COMMENT_MARKERS = ("#", "//")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments and return the parsed namespace.
    Implements a shortcut: if the first argument is not a subcommand,
    treat it as 'get <task>'.
    """
    parser = argparse.ArgumentParser(
        description="Manage LLM model configurations in ~/.config/llm-manager/llm.conf and /etc/llm.conf.",
        epilog="Shortcut:\n  llm-manager <task>    Equivalent to 'llm-manager get <task>'",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", title="Commands")

    parser_set = subparsers.add_parser(
        "set", help="Set or update the model for a specific task"
    )
    parser_set.add_argument(
        "task", type=str, help="Type of the task (e.g., text-generation)"
    )
    parser_set.add_argument("model", type=str, help="Model value (e.g., gemma2:2b)")

    parser_get = subparsers.add_parser("get", help="Get the model for a specific task")
    parser_get.add_argument("task", type=str, help="Type of the task to retrieve")

    parser_show = subparsers.add_parser("show", help="Show all task-to-model mappings")

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"llm-manager version {VERSION}",
        help="Show the version of this utility and exit",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # If the first argument is not a subcommand or option, treat it as 'get <task>'
    if sys.argv[1] not in ["set", "get", "show", "-h", "--help", "-v", "--version"]:
        # Insert 'get' as the command
        sys.argv.insert(1, "get")

    args = parser.parse_args()

    return args


def read_config_file(config_file: Path) -> List[str]:
    """
    Read the given configuration file and return a list of its lines.
    Preserves comments and blank lines.
    """
    if config_file.is_file():
        try:
            with config_file.open("r", encoding="utf-8") as f:
                return f.readlines()
        except PermissionError:
            print(
                f"Warning: Permission denied while reading {config_file}.",
                file=sys.stderr,
            )
            return []
        except Exception as e:
            print(f"Warning: Error reading {config_file}: {e}", file=sys.stderr)
            return []
    else:
        return []


def write_config_file(config_file: Path, lines: List[str]) -> None:
    """
    Write the list of lines back to the given configuration file.
    Overwrites the existing file.
    """
    try:
        with config_file.open("w", encoding="utf-8") as f:
            for line in lines:
                if not line.endswith("\n"):
                    line += "\n"
                f.write(line)
        # Set file permissions to read/write for the user only
        os.chmod(config_file, 0o600)
    except PermissionError:
        print(
            f"Error: Permission denied while writing to {config_file}.", file=sys.stderr
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error: Error writing to {config_file}: {e}", file=sys.stderr)
        sys.exit(1)


def parse_config(lines: List[str]) -> Dict[str, str]:
    """
    Parse the configuration lines into a dictionary of task to model mappings.
    """
    config = {}
    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip comments
        if stripped.startswith(COMMENT_MARKERS):
            continue

        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                config[key] = value
            else:
                print(
                    f"Warning: Ignoring invalid line in config: {line.strip()}",
                    file=sys.stderr,
                )
        else:
            print(
                f"Warning: Ignoring invalid line in config: {line.strip()}",
                file=sys.stderr,
            )
            continue  # Skip lines without the assignment operator

    return config


def validate_input(value: str) -> bool:
    """
    Validate the task or model input to prevent invalid entries.
    """
    if "=" in value or "\n" in value or value.startswith(COMMENT_MARKERS):
        return False
    return True


def set_model(task: str, model: str) -> None:
    """
    Set or update the model for the given task.
    Writes only to the user configuration file.
    """
    if not validate_input(task) or not validate_input(model):
        print("Error: Invalid characters in task or model name.", file=sys.stderr)
        sys.exit(1)

    # Read user config only
    lines = read_config_file(USER_CONFIG_FILE)

    updated = False
    new_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith(COMMENT_MARKERS):
            new_lines.append(line)
            continue

        # Check if the line contains the assignment operator
        if "=" in stripped:
            key, _ = stripped.split("=", 1)
            key = key.strip()

            if key == task:
                # Update the line with the new model
                new_line = f"{task} = {model}\n"
                new_lines.append(new_line)
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not updated:
        # Add the new task at the end
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_line = f"{task} = {model}\n"
        new_lines.append(new_line)

    # Ensure the directory exists
    try:
        USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error: Error creating configuration directory: {e}", file=sys.stderr)
        sys.exit(1)

    # Write back to user config file
    write_config_file(USER_CONFIG_FILE, new_lines)

    if updated:
        print(f"Updated {task} = {model}")
    else:
        print(f"Set {task} = {model}")


def get_model(task: str) -> None:
    """
    Retrieve and print the model for the given task.
    """
    # Read system config
    system_lines = read_config_file(SYSTEM_CONFIG_FILE)
    system_config = parse_config(system_lines)

    # Read user config
    user_lines = read_config_file(USER_CONFIG_FILE)
    user_config = parse_config(user_lines)

    # Merge configurations, with user config overriding system config
    merged_config = system_config.copy()
    merged_config.update(user_config)

    model = merged_config.get(task)
    if model:
        print(model)
    else:
        print(f"{task} is not set.")
        sys.exit(1)


def show_config() -> None:
    """
    Display all task-to-model configurations, with user configurations overriding system configurations.
    """
    # Read system config
    system_lines = read_config_file(SYSTEM_CONFIG_FILE)
    system_config = parse_config(system_lines)

    # Read user config
    user_lines = read_config_file(USER_CONFIG_FILE)
    user_config = parse_config(user_lines)

    # Merge the configs, with user config overriding system config
    merged_config = system_config.copy()
    merged_config.update(user_config)

    if merged_config:
        for task, model in merged_config.items():
            print(f"{task} = {model}")
    else:
        print("No configurations found.")


def main() -> None:
    args = parse_arguments()

    if args.subcommand == "set":
        set_model(args.task, args.model)
    elif args.subcommand == "get":
        get_model(args.task)
    elif args.subcommand == "show":
        show_config()
    else:
        print("Error: No command provided.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
