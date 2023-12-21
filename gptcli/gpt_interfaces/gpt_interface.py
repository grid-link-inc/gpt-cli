from abc import ABC, abstractmethod
from gptcli.gpt_interfaces.completion import ModelOverrides
from typing import Iterator

class ChatInterface(ABC):
    
    @abstractmethod
    def complete_chat(
        self, messages, override_params: ModelOverrides = {}, stream: bool = True
    ) -> Iterator[str]:
        pass