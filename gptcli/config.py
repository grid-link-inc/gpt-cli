import os
from typing import Dict, List, Optional, TypedDict
from attr import dataclass
import yaml

from gptcli.gpt_interfaces.wrapper.wrapper import WrapperConfig
from gptcli.gpt_interfaces.chatgpt_assistant.assistant import AssistantConfig
from gptcli.gpt_interfaces.wrapper.interfaces.llama import LLaMAModelConfig


CONFIG_FILE_PATHS = [
    os.path.join(os.path.expanduser("~"), ".config", "gpt-cli", "gpt.yml"),
    os.path.join(os.path.expanduser("~"), ".gptrc"),
]


@dataclass
class GptCliConfig:
    default_wrapper: str = "general"
    markdown: bool = True
    show_price: bool = True
    api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    openai_api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = os.environ.get("GOOGLE_API_KEY")
    log_file: Optional[str] = None
    log_level: str = "INFO"
    wrappers: Dict[str, WrapperConfig] = {}
    interactive: Optional[bool] = None
    llama_models: Optional[Dict[str, LLaMAModelConfig]] = None

    assistants: Dict[str, AssistantConfig] = {}


def choose_config_file(paths: List[str]) -> str:
    for path in paths:
        if os.path.isfile(path):
            return path
    return ""


def read_yaml_config(file_path: str) -> GptCliConfig:
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
        return GptCliConfig(
            **config,
        )
