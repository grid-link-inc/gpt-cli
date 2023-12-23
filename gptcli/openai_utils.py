from typing import List

# import tiktoken

from typing import List
from gptcli.openai_types import Message



# def num_tokens_from_messages_openai(messages: List[Message], model: str) -> int:
#     encoding = tiktoken.encoding_for_model(model)
#     num_tokens = 0
#     for message in messages:
#         # every message follows <im_start>{role/name}\n{content}<im_end>\n
#         num_tokens += 4
#         for key, value in message.items():
#             assert isinstance(value, str)
#             num_tokens += len(encoding.encode(value))
#             if key == "name":  # if there's a name, the role is omitted
#                 num_tokens += -1  # role is always required and always 1 token
#     num_tokens += 2  # every reply is primed with <im_start>assistant
#     return num_tokens


def num_tokens_from_completion_openai(completion: Message, model: str) -> int:
    return 1
    # TODO
    # return num_tokens_from_messages_openai([completion], model)
