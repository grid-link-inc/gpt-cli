"""
This module is responsible for calculating the cost of a chat session.
"""

import tiktoken
import logging

from gptcli.types import Message
from gptcli.session import ChatListener
from gptcli.assistant import AssistantThread

from rich.console import Console
from typing import List, Optional


def num_tokens_from_messages(messages: List[Message], model: str) -> Optional[int]:
    return num_tokens_from_messages_openai(messages, model)


def num_tokens_from_completion(message: Message, model: str) -> Optional[int]:
    return num_tokens_from_completion_openai(message, model)


GPT_3_5_TURBO_PRICE_PER_TOKEN = {
    "prompt": 0.0015 / 1000,
    "response": 0.002 / 1000,
}

GPT_3_5_TURBO_16K_PRICE_PER_TOKEN = {
    "prompt": 0.003 / 1000,
    "response": 0.004 / 1000,
}

GPT_4_PRICE_PER_TOKEN = {
    "prompt": 0.03 / 1000,
    "response": 0.06 / 1000,
}

GPT_4_TURBO_PRICE_PER_TOKEN = {
    "prompt": 0.01 / 1000,
    "response": 0.03 / 1000,
}

GPT_4_32K_PRICE_PER_TOKEN = {
    "prompt": 0.06 / 1000,
    "response": 0.12 / 1000,
}


def gpt_pricing(model: str, prompt: bool) -> Optional[float]:
    if model.startswith("gpt-3.5-turbo-16k"):
        pricing = GPT_3_5_TURBO_16K_PRICE_PER_TOKEN
    elif model.startswith("gpt-3.5-turbo"):
        pricing = GPT_3_5_TURBO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4-32k"):
        pricing = GPT_4_32K_PRICE_PER_TOKEN
    elif model.startswith("gpt-4-1106-preview"):
        pricing = GPT_4_TURBO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4"):
        pricing = GPT_4_PRICE_PER_TOKEN
    else:
        return None
    return pricing["prompt" if prompt else "response"]


CLAUDE_PRICE_PER_TOKEN = {
    "prompt": 11.02 / 1_000_000,
    "response": 32.68 / 1_000_000,
}

CLAUDE_INSTANT_PRICE_PER_TOKEN = {
    "prompt": 1.63 / 1_000_000,
    "response": 5.51 / 1_000_000,
}


def claude_pricing(model: str, prompt: bool) -> Optional[float]:
    if "instant" in model:
        pricing = CLAUDE_INSTANT_PRICE_PER_TOKEN
    else:
        pricing = CLAUDE_PRICE_PER_TOKEN
    return pricing.get("prompt" if prompt else "response")


def price_per_token(model: str, prompt: bool) -> Optional[float]:
    if model.startswith("gpt"):
        return gpt_pricing(model, prompt)
    elif model.startswith("claude"):
        return claude_pricing(model, prompt)
    elif model.startswith("chat-bison"):
        return 0
    else:
        return None


def price_for_completion(messages: List[Message], response: Message, model: str):
    num_tokens_prompt = num_tokens_from_messages(messages, model)
    num_tokens_response = num_tokens_from_completion(response, model)
    if num_tokens_prompt is None or num_tokens_response is None:
        return None

    price_per_token_prompt = price_per_token(model, prompt=True)
    price_per_token_response = price_per_token(model, prompt=False)
    if price_per_token_prompt is None or price_per_token_response is None:
        return None

    return (
        price_per_token_prompt * num_tokens_prompt
        + price_per_token_response * num_tokens_response
    )

class PriceChatListener(ChatListener):
    def __init__(self, assistant: AssistantThread):
        self.assistant = assistant
        self.current_spend = 0
        self.logger = logging.getLogger("gptcli-price")
        self.console = Console()

    def on_chat_clear(self):
        self.current_spend = 0

    def on_chat_response(
        self, messages: List[Message], response: Message
    ):
        model = self.assistant._param("model")
        num_tokens = num_tokens_from_messages(messages + [response], model)
        price = price_for_completion(messages, response, model)
        if price is None:
            self.logger.error(f"Cannot get cost information for model {model}")
            return
        self.current_spend += price
        self.logger.info(f"Token usage {num_tokens}")
        self.logger.info(f"Message price (model: {model}): ${price:.3f}")
        self.logger.info(f"Current spend: ${self.current_spend:.3f}")
        self.console.print(
            f"Tokens: {num_tokens} | Price: ${price:.3f} | Total: ${self.current_spend:.3f}",
            justify="right",
            style="dim",
        )

def num_tokens_from_messages_openai(messages: List[Message], model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        for key, value in message.items():
            assert isinstance(value, str)
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def num_tokens_from_completion_openai(completion: Message, model: str) -> int:
    return num_tokens_from_messages_openai([completion], model)