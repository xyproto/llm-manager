#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# lm-manager
# Utility for managing LLM model configurations in /etc/llm.conf.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

CONFIG_FILE = Path("/etc/llm.conf")
VERSION = "1.0.1"

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
        description="Manage LLM model configurations by modifying /etc/llm.conf.",
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
    parser_set = subparsers.add_parser("set", help="Set or update the model for a specific task")
    parser_set.add_argument("task", type=str, help="Type of the model (e.g., text-generation)")
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


def read_config() -> List[str]:
    """
    Read the configuration file and return a list of its lines.
    Preserves comments and blank lines.
    """
    if CONFIG_FILE.is_file():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                return f.readlines()
        except PermissionError:
            sys.exit(f"Error: Permission denied while reading {CONFIG_FILE}.")
        except Exception as e:
            sys.exit(f"Error reading {CONFIG_FILE}: {e}")
    else:
        return []


def write_config(lines: List[str]) -> None:
    """
    Write the list of lines back to the configuration file.
    Overwrites the existing file.
    """
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            f.writelines(lines)
    except PermissionError:
        sys.exit(f"Error: Permission denied while writing to {CONFIG_FILE}.")
    except Exception as e:
        sys.exit(f"Error writing to {CONFIG_FILE}: {e}")


def find_assignment_operator(line: str) -> Tuple[str, str]:
    """
    Find the assignment operator in the line and return the key with operator and the value.
    Returns (key_with_operator, value)
    """
    for operator in ASSIGNMENT_OPERATORS:
        if operator in line:
            parts = line.split(operator, 1)
            key = parts[0].rstrip()
            value = parts[1].rstrip('\n').lstrip()
            return key + operator, value
    return "", ""


def set_model(task: str, model: str) -> None:
    """
    Set or update the model for the given task.
    """
    lines = read_config()
    updated = False
    new_lines = []

    in_multiline_comment = False

    for line in lines:
        stripped = line.strip()

        # Handle multi-line comments
        if in_multiline_comment:
            new_lines.append(line)
            if MULTI_LINE_COMMENT_END in stripped:
                in_multiline_comment = False
            continue

        if any(stripped.startswith(marker) for marker in SINGLE_LINE_COMMENTS):
            # Check for start of multi-line comment
            if stripped.startswith(MULTI_LINE_COMMENT_START):
                in_multiline_comment = True
            new_lines.append(line)
            continue

        if not stripped:
            new_lines.append(line)
            continue

        key_with_op, _ = find_assignment_operator(line)
        if not key_with_op:
            new_lines.append(line)
            continue

        # Extract the key without the operator
        key = ""
        operator = ""
        for op in ASSIGNMENT_OPERATORS:
            if key_with_op.endswith(op):
                key = key_with_op[:-len(op)].strip()
                operator = op
                break
        else:
            new_lines.append(line)
            continue

        if key == task:
            # Replace the line with the new value, preserving indentation
            indent = line[:line.find(key_with_op)]
            new_line = f"{indent}{task}{operator}{model}\n"
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        # Append the new task at the end without adding extra blank lines
        if lines and not lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{task}= {model}\n")

    write_config(new_lines)
    if updated:
        print(f"Updated {task}={model}")
    else:
        print(f"Set {task}={model}")


def get_model(task: str) -> None:
    """
    Retrieve and print the model for the given task.
    """
    lines = read_config()

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
                key = key_with_op[:-len(op)].strip()
                break
        else:
            continue

        if key == task:
            print(value.rstrip())
            return

    print(f"{task} is not set.")
    sys.exit(1)


def show_config() -> None:
    """
    Display all task-to-model configurations by printing the contents of /etc/llm.conf.
    """
    if CONFIG_FILE.is_file():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    print(content, end="")
                else:
                    print("No configurations found.")
        except PermissionError:
            sys.exit(f"Error: Permission denied while reading {CONFIG_FILE}.")
        except Exception as e:
            sys.exit(f"Error reading {CONFIG_FILE}: {e}")
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
