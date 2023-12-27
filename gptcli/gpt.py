#!/usr/bin/env python

"""
This is the main entry point for the gpt-cli program.
"""

import sys

import gptcli

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

import os
from typing import cast
import argparse
import sys


from gptcli.assistant import (
    AssistantThread,
    DEFAULT_ASSISTANTS,
    AssistantGlobalArgs,
    init_assistant,
)
from gptcli.cli import (
    CLIChatListener,
    CLIUserInputProvider,
)
from gptcli.composite import CompositeChatListener
from gptcli.config import (
    CONFIG_FILE_PATHS,
    GptCliConfig,
    choose_config_file,
    read_yaml_config,
)
from gptcli.logging_utils import LoggingChatListener
from gptcli.persist import PersistChatListener
from gptcli.cost import PriceChatListener
from gptcli.session import ChatSession

default_exception_handler = sys.excepthook


def exception_handler(type, value, traceback):
    print("An uncaught exception occurred. Please report this issue on GitHub.")
    default_exception_handler(type, value, traceback)


sys.excepthook = exception_handler


def parse_args(config: GptCliConfig):
    parser = argparse.ArgumentParser(
        description="Run a chat session with ChatGPT. See https://github.com/grid-link-inc/gpt-cli for more information."
    )
    parser.add_argument(
        "assistant_name",
        type=str,
        default=config.default_assistant,
        nargs="?",
        choices=list(set([*DEFAULT_ASSISTANTS.keys(), *config.assistants.keys()])),
        help="The name of assistant to use. Name must match an assistant in the config file ~/.config/gpt-cli/gpt.yml. See the README for more information.",
    )
    parser.add_argument(
        "--no_markdown",
        action="store_false",
        dest="markdown",
        help="Disable markdown formatting in the chat session.",
        default=config.markdown,
    )
    parser.add_argument(
        "--log_file",
        type=str,
        default=config.log_file,
        help="The file to write logs to. Supports strftime format codes.",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default=config.log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="The log level to use",
    )
    parser.add_argument(
        "--no_stream",
        action="store_true",
        default=False,
        help="If specified, will not stream the response to standard output. This is useful if you want to use the response in a script. Ignored when the --prompt option is not specified.",
    )
    parser.add_argument(
        "--no_price",
        action="store_false",
        dest="show_price",
        help="Disable price logging.",
        default=config.show_price,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"gpt-cli v{gptcli.__version__}",
        help="Print the version number and exit.",
    )

    return parser.parse_args()


def main():
    config_file_path = choose_config_file(CONFIG_FILE_PATHS)
    if config_file_path:
        config = read_yaml_config(config_file_path)
    else:
        config = GptCliConfig()
    args = parse_args(config)

    if not config.api_key or not config.openai_api_key:
        print(
            "No API key found. Please set the OPENAI_API_KEY environment variable or `api_key: <key>` value in ~/.config/gpt-cli/gpt.yml"
        )
        sys.exit(1)

    assistant = init_assistant(cast(AssistantGlobalArgs, args), config.assistants)
    run_interactive(args, assistant)

class CLIChatSession(ChatSession):
    def __init__(self, assistant: AssistantThread, markdown: bool, show_price: bool):
        listeners = [
            CLIChatListener(markdown),
            LoggingChatListener(),
            PersistChatListener(assistant.get_thread_id(), assistant.get_assistant_id()),
        ]

        # TODO: Implement price for chatgpt Assistants
        # if show_price:
        #     listeners.append(PriceChatListener(assistant))

        listener = CompositeChatListener(listeners)
        super().__init__(assistant, listener)


def run_interactive(args, assistant):
    session = CLIChatSession(
        assistant=assistant, markdown=args.markdown, show_price=args.show_price
    )
    history_filename = os.path.expanduser("~/.config/gpt-cli/history")
    os.makedirs(os.path.dirname(history_filename), exist_ok=True)
    input_provider = CLIUserInputProvider(history_filename=history_filename)
    session.loop(input_provider)

if __name__ == "__main__":
    main()
