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

class AssistantConfig(TypedDict, total=False):
    id: str
    messages: List[Message]


CONFIG_DEFAULTS = {
    # "id": "asst_jCP75X9phRfVjZ8Q4iBistYT",
}

DEFAULT_ASSISTANTS: Dict[str, AssistantConfig] = {}


def get_completion_provider(model: str) -> CompletionProvider:
    if model.startswith("gpt"):
        return OpenAICompletionProvider()
    # elif model.startswith("claude"):
    #     return AnthropicCompletionProvider()
    # elif model.startswith("llama"):
    #     return LLaMACompletionProvider()
    # elif model.startswith("chat-bison"):
    #     return GoogleCompletionProvider()
    else:
        raise ValueError(f"Unknown model: {model}")


class Assistant(ChatInterface):
    # TODO fetch assistant from id in config
    def __init__(self, config: AssistantConfig):
        self.config = config

    @classmethod
    def from_config(cls, name: str, config: AssistantConfig):
        config = config.copy()
        if name in DEFAULT_ASSISTANTS:
            # Merge the config with the default config
            # If a key is in both, use the value from the config
            default_config = DEFAULT_ASSISTANTS[name]
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
        # 
        model = self._param("model", override_params)
        # Talk to shatgpt assistant here
        completion_provider = OpenAICompletionProvider()
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
class AssistantGlobalArgs:
    assistant_name: str

def init_assistant(
    args: AssistantGlobalArgs, custom_assistants: Dict[str, AssistantConfig]
) -> Assistant:
    name = args.assistant_name
    if name in custom_assistants:
        assistant = Assistant.from_config(name, custom_assistants[name])
    elif name in DEFAULT_ASSISTANTS:
        assistant = Assistant.from_config(name, DEFAULT_ASSISTANTS[name])
    else:
        print(f"Unknown assistant: {name}")
        sys.exit(1)

    # Override config with command line arguments
    # if args.temperature is not None:
    #     assistant.config["temperature"] = args.temperature
    # if args.model is not None:
    #     assistant.config["model"] = args.model
    # if args.top_p is not None:
    #     assistant.config["top_p"] = args.top_p
    return assistant
