import os
import sys
from attr import dataclass
import platform
from typing import Any, Dict, Iterator, Optional, TypedDict, List

from gptcli.gpt_interfaces.completion import CompletionProvider, ModelOverrides, Message
from gptcli.gpt_interfaces.wrapper.interfaces.google import GoogleCompletionProvider
from gptcli.gpt_interfaces.wrapper.interfaces.llama import LLaMACompletionProvider
from gptcli.gpt_interfaces.wrapper.interfaces.openai import OpenAICompletionProvider
from gptcli.gpt_interfaces.wrapper.interfaces.anthropic import AnthropicCompletionProvider

from gptcli.gpt_interfaces.gpt_interface import ChatInterface

class WrapperConfig(TypedDict, total=False):
    messages: List[Message]
    model: str
    temperature: float
    top_p: float


CONFIG_DEFAULTS = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1.0,
}

DEFAULT_WRAPPER: Dict[str, WrapperConfig] = {
    "dev": {
        "messages": [
            {
                "role": "system",
                "content": f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown with a correct language tag. User's `uname`: {platform.uname()}",
            },
            {
                "role": "user",
                "content": "Your responses must be short and concise. Do not include explanations unless asked.",
            },
            {
                "role": "assistant",
                "content": "Understood.",
            },
        ],
    },
    "general": {
        "messages": [],
    },
    "bash": {
        "messages": [
            {
                "role": "system",
                "content": f"You output only valid and correct shell commands according to the user's prompt. You don't provide any explanations or any other text that is not valid shell commands. User's `uname`: {platform.uname()}. User's `$SHELL`: {os.environ.get('SHELL')}.",
            }
        ],
    },
}


def get_completion_provider(model: str) -> CompletionProvider:
    if model.startswith("gpt"):
        return OpenAICompletionProvider()
    elif model.startswith("claude"):
        return AnthropicCompletionProvider()
    elif model.startswith("llama"):
        return LLaMACompletionProvider()
    elif model.startswith("chat-bison"):
        return GoogleCompletionProvider()
    else:
        raise ValueError(f"Unknown model: {model}")


class Wrapper(ChatInterface):
    def __init__(self, config: WrapperConfig):
        self.config = config

    @classmethod
    def from_config(cls, name: str, config: WrapperConfig):
        config = config.copy()
        if name in DEFAULT_WRAPPER:
            # Merge the config with the default config
            # If a key is in both, use the value from the config
            default_config = DEFAULT_WRAPPER[name]
            for key in [*config.keys(), *default_config.keys()]:
                if config.get(key) is None:
                    config[key] = default_config[key]

        return cls(config)

    def init_messages(self) -> List[Message]:
        return self.config.get("messages", [])[:]

    def supported_overrides(self) -> List[str]:
        return ["model", "temperature", "top_p"]

    def _param(self, param: str, override_params: ModelOverrides) -> Any:
        # If the param is in the override_params, use that value
        # Otherwise, use the value from the config
        # Otherwise, use the default value
        return override_params.get(
            param, self.config.get(param, CONFIG_DEFAULTS[param])
        )

    def complete_chat(
        self, messages, override_params: ModelOverrides = {}, stream: bool = True
    ) -> Iterator[str]:
        model = self._param("model", override_params)
        completion_provider = get_completion_provider(model)
        return completion_provider.complete(
            messages,
            {
                "model": model,
                "temperature": float(self._param("temperature", override_params)),
                "top_p": float(self._param("top_p", override_params)),
            },
            stream,
        )


@dataclass
class WrapperGlobalArgs:
    wrapper_name: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


def init_wrapper(
    args: WrapperGlobalArgs, custom_wrappers: Dict[str, WrapperConfig]
) -> Wrapper:
    name = args.wrapper_name
    if name in custom_wrappers:
        wrapper = Wrapper.from_config(name, custom_wrappers[name])
    elif name in DEFAULT_WRAPPER:
        wrapper = Wrapper.from_config(name, DEFAULT_WRAPPER[name])
    else:
        print(f"Unknown wrapper: {name}")
        sys.exit(1)

    # Override config with command line arguments
    if args.temperature is not None:
        wrapper.config["temperature"] = args.temperature
    if args.model is not None:
        wrapper.config["model"] = args.model
    if args.top_p is not None:
        wrapper.config["top_p"] = args.top_p
    return wrapper
