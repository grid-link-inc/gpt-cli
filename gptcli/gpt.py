#!/usr/bin/env python

import sys

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

import os
from typing import cast
import openai
import argparse
import sys
import logging
import datetime
import google.generativeai as genai
import gptcli.anthropic
from gptcli.wrapper import (
    Wrapper,
    DEFAULT_WRAPPER,
    WrapperGlobalArgs,
    init_wrapper,
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
from gptcli.llama import init_llama_models
from gptcli.logging import LoggingChatListener
from gptcli.cost import PriceChatListener
from gptcli.session import ChatSession
from gptcli.shell import execute, simple_response


logger = logging.getLogger("gptcli")

default_exception_handler = sys.excepthook


def exception_handler(type, value, traceback):
    logger.exception("Uncaught exception", exc_info=(type, value, traceback))
    print("An uncaught exception occurred. Please report this issue on GitHub.")
    default_exception_handler(type, value, traceback)


sys.excepthook = exception_handler


def parse_args(config: GptCliConfig):
    parser = argparse.ArgumentParser(
        description="Run a chat session with ChatGPT. See https://github.com/kharvd/gpt-cli for more information."
    )
    parser.add_argument(
        "wrapper_name",
        type=str,
        default=config.default_wrapper,
        nargs="?",
        choices=list(set([*DEFAULT_WRAPPER.keys(), *config.wrappers.keys()])),
        help="The name of wrapper to use. `general` (default) is a generally helpful wrapper, `dev` is a software development wrapper with shorter responses. You can specify your own wrappers in the config file ~/.config/gpt-cli/gpt.yml. See the README for more information.",
    )
    parser.add_argument(
        "--no_markdown",
        action="store_false",
        dest="markdown",
        help="Disable markdown formatting in the chat session.",
        default=config.markdown,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="The model to use for the chat session. Overrides the default model defined for the wrapper.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="The temperature to use for the chat session. Overrides the default temperature defined for the wrapper.",
    )
    parser.add_argument(
        "--top_p",
        type=float,
        default=None,
        help="The top_p to use for the chat session. Overrides the default top_p defined for the wrapper.",
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
        "--prompt",
        "-p",
        type=str,
        action="append",
        default=None,
        help="If specified, will not start an interactive chat session and instead will print the response to standard output and exit. May be specified multiple times. Use `-` to read the prompt from standard input. Implies --no_markdown.",
    )
    parser.add_argument(
        "--execute",
        "-e",
        type=str,
        default=None,
        help="If specified, passes the prompt to the wrapper and allows the user to edit the produced shell command before executing it. Implies --no_stream. Use `-` to read the prompt from standard input.",
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


def validate_args(args):
    if args.prompt is not None and args.execute is not None:
        print(
            "The --prompt and --execute options are mutually exclusive. Please specify only one of them."
        )
        sys.exit(1)


def main():
    config_file_path = choose_config_file(CONFIG_FILE_PATHS)
    if config_file_path:
        config = read_yaml_config(config_file_path)
    else:
        config = GptCliConfig()
    args = parse_args(config)

    if args.log_file is not None:
        filename = datetime.datetime.now().strftime(args.log_file)
        logging.basicConfig(
            filename=filename,
            level=args.log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        # Disable overly verbose logging for markdown_it
        logging.getLogger("markdown_it").setLevel(logging.INFO)

    if config.api_key:
        openai.api_key = config.api_key
    elif config.openai_api_key:
        openai.api_key = config.openai_api_key
    else:
        print(
            "No API key found. Please set the OPENAI_API_KEY environment variable or `api_key: <key>` value in ~/.config/gpt-cli/gpt.yml"
        )
        sys.exit(1)

    if config.anthropic_api_key:
        gptcli.anthropic.api_key = config.anthropic_api_key

    if config.google_api_key:
        genai.configure(api_key=config.google_api_key)

    if config.llama_models is not None:
        init_llama_models(config.llama_models)

    wrapper = init_wrapper(cast(WrapperGlobalArgs, args), config.wrappers)

    if args.prompt is not None:
        run_non_interactive(args, wrapper)
    elif args.execute is not None:
        run_execute(args, wrapper)
    else:
        run_interactive(args, wrapper)


def run_execute(args, wrapper):
    logger.info(
        "Starting a non-interactive execution session with prompt '%s'. Wrapper config: %s",
        args.prompt,
        wrapper.config,
    )
    if args.execute == "-":
        args.execute = "".join(sys.stdin.readlines())
    execute(wrapper, args.execute)


def run_non_interactive(args, wrapper):
    logger.info(
        "Starting a non-interactive session with prompt '%s'. Wrapper config: %s",
        args.prompt,
        wrapper.config,
    )
    if "-" in args.prompt:
        args.prompt[args.prompt.index("-")] = "".join(sys.stdin.readlines())

    simple_response(wrapper, "\n".join(args.prompt), stream=not args.no_stream)


class CLIChatSession(ChatSession):
    def __init__(self, wrapper: Wrapper, markdown: bool, show_price: bool):
        listeners = [
            CLIChatListener(markdown),
            LoggingChatListener(),
        ]

        if show_price:
            listeners.append(PriceChatListener(wrapper))

        listener = CompositeChatListener(listeners)
        super().__init__(wrapper, listener)


def run_interactive(args, wrapper):
    logger.info("Starting a new chat session. Wrapper config: %s", wrapper.config)
    session = CLIChatSession(
        wrapper=wrapper, markdown=args.markdown, show_price=args.show_price
    )
    history_filename = os.path.expanduser("~/.config/gpt-cli/history")
    os.makedirs(os.path.dirname(history_filename), exist_ok=True)
    input_provider = CLIUserInputProvider(history_filename=history_filename)
    session.loop(input_provider)


if __name__ == "__main__":
    main()
