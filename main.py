#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# lm-manager
# Utility for managing LLM model configurations in ~/.config/llm-manager/llm.conf and /etc/llm.conf.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration file paths
USER_CONFIG_FILE = Path.home() / ".config" / "llm-manager" / "llm.conf"
SYSTEM_CONFIG_FILE = Path("/etc/llm.conf")
VERSION = "1.0.2"

# Define comment markers
SINGLE_LINE_COMMENTS = ["#", "//", "--"]
MULTI_LINE_COMMENT_START = "/*"
MULTI_LINE_COMMENT_END = "*/"
MULTI_LINE_COMMENTS = [MULTI_LINE_COMMENT_START, MULTI_LINE_COMMENT_END]

# Define possible assignment operators in order of precedence
ASSIGNMENT_OPERATORS = ["==", "=>", "+=", "-=", "?=", "=", ":=", "::", ":", "is"]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments and return the parsed namespace.
    Implements a shortcut: if the first argument is not a subcommand,
    treat it as 'get <task>'.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Manage LLM model configurations in ~/.config/llm-manager/llm.conf and /etc/llm.conf."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        usage=(
            "lm-manager <command> [<args>]\n\n"
            "Commands:\n"
            "  set <task> <model>   Set or update the model for a specific task\n"
            "  get <task>           Get the model for a specific task\n"
            "  show                 Show all task-to-model mappings\n\n"
            "Options:\n"
            "  -h, --help           Show this help message and exit\n"
            "  -v, --version        Show the version of this utility and exit\n\n"
            "Shortcut:\n"
            "  lm-manager <task>    Equivalent to 'lm-manager get <task>'\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand", title="Commands", metavar="")

    # Set command
    parser_set = subparsers.add_parser(
        "set", help="Set or update the model for a specific task"
    )
    parser_set.add_argument(
        "task", type=str, help="Type of the model (e.g., text-generation)"
    )
    parser_set.add_argument("model", type=str, help="Model value (e.g., gemma2:2b)")

    # Get command
    parser_get = subparsers.add_parser("get", help="Get the model for a specific task")
    parser_get.add_argument("task", type=str, help="Type of the model to retrieve")

    # Show command
    subparsers.add_parser("show", help="Show all task-to-model mappings")

    # Version flag
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"lm-manager version {VERSION}",
        help="Show the version of this utility and exit",
    )

    # If no arguments are provided, show help and exit
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
            print(f"Warning: Permission denied while reading {config_file}.")
            return []
        except Exception as e:
            print(f"Warning: Error reading {config_file}: {e}")
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
                if not line.endswith('\n'):
                    line += '\n'
                f.write(line)
    except PermissionError:
        sys.exit(f"Error: Permission denied while writing to {config_file}.")
    except Exception as e:
        sys.exit(f"Error writing to {config_file}: {e}")


def find_assignment_operator(line: str) -> Tuple[str, str]:
    """
    Find the assignment operator in the line and return the key with operator and the value.
    Returns (key_with_operator, value)
    """
    for operator in ASSIGNMENT_OPERATORS:
        if operator in line:
            parts = line.split(operator, 1)
            key = parts[0].rstrip()
            value = parts[1].rstrip("\n").lstrip()
            return key + operator, value
    return "", ""


def parse_config(lines: List[str]) -> Dict[str, str]:
    """
    Parse the configuration lines into a dictionary of task to model mappings.
    """
    config = {}
    in_multiline_comment = False

    for line in lines:
        stripped = line.strip()

        # Handle multi-line comments
        if in_multiline_comment:
            if MULTI_LINE_COMMENT_END in stripped:
                in_multiline_comment = False
            continue

        if any(stripped.startswith(marker) for marker in SINGLE_LINE_COMMENTS):
            # Check for start of multi-line comment
            if stripped.startswith(MULTI_LINE_COMMENT_START):
                in_multiline_comment = True
            continue

        if not stripped:
            continue

        key_with_op, value = find_assignment_operator(line)
        if not key_with_op:
            continue

        # Extract the key without the operator
        key = ""
        for op in ASSIGNMENT_OPERATORS:
            if key_with_op.endswith(op):
                key = key_with_op[: -len(op)].strip()
                break
        else:
            continue

        config[key] = value.rstrip()

    return config


def set_model(task: str, model: str) -> None:
    """
    Set or update the model for the given task.
    Writes only to the user configuration file.
    """
    # Read user config only
    lines = read_config_file(USER_CONFIG_FILE)

    updated = False
    new_lines = []

    in_multiline_comment = False

    for line in lines:
        original_line = line
        stripped = line.strip()

        # Handle multi-line comments
        if in_multiline_comment:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
            if MULTI_LINE_COMMENT_END in stripped:
                in_multiline_comment = False
            continue

        if any(stripped.startswith(marker) for marker in SINGLE_LINE_COMMENTS):
            # Check for start of multi-line comment
            if stripped.startswith(MULTI_LINE_COMMENT_START):
                in_multiline_comment = True
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
            continue

        if not stripped:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
            continue

        # Get the key and operator from the line
        key_with_op, _ = find_assignment_operator(line)
        if not key_with_op:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
            continue

        # Extract the key without the operator
        key = ""
        for op in ASSIGNMENT_OPERATORS:
            if key_with_op.endswith(op):
                key = key_with_op[: -len(op)].strip()
                break
        else:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
            continue

        if key == task:
            indent = line[: line.find(key_with_op)]
            new_line = f"{indent}{key_with_op} {model}\n"
            new_lines.append(new_line)
            updated = True
        else:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)

    if not updated:
        # Ensure there's a newline before appending if needed
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_line = f"{task} = {model}\n"
        new_lines.append(new_line)

    # Ensure the directory exists
    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write back to user config file
    write_config_file(USER_CONFIG_FILE, new_lines)

    if updated:
        print(f"Updated {task} = {model}")
    else:
        print(f"Set {task} = {model}")


def get_model_from_config(task: str, lines: List[str]) -> Optional[str]:
    """
    Process the lines and try to find the model for the given task.
    Returns the model value if found, else None.
    """
    in_multiline_comment = False

    for line in lines:
        stripped = line.strip()

        # Handle multi-line comments
        if in_multiline_comment:
            if MULTI_LINE_COMMENT_END in stripped:
                in_multiline_comment = False
            continue

        if any(stripped.startswith(marker) for marker in SINGLE_LINE_COMMENTS):
            # Check for start of multi-line comment
            if stripped.startswith(MULTI_LINE_COMMENT_START):
                in_multiline_comment = True
            continue

        if not stripped:
            continue

        key_with_op, value = find_assignment_operator(line)
        if not key_with_op:
            continue

        # Extract the key without the operator
        key = ""
        for op in ASSIGNMENT_OPERATORS:
            if key_with_op.endswith(op):
                key = key_with_op[: -len(op)].strip()
                break
        else:
            continue

        if key == task:
            return value.rstrip()

    return None


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
        # This should not happen due to earlier checks, but added for safety
        print("Error: No command provided.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
