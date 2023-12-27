import sys
import time
from attr import dataclass
from typing import Dict, TypedDict, List
from openai import OpenAI

from gptcli.types import Message
from gptcli.openai_types import ThreadMessage, ThreadRun

class AssistantConfig(TypedDict, total=False):
    id: str
    messages: List[Message]

CONFIG_DEFAULTS = {
    "id": "asst_jCP75X9phRfVjZ8Q4iBistYT",
}

DEFAULT_ASSISTANTS: Dict[str, AssistantConfig] = {}


class AssistantThread():
    """
    A class to represent an assistant thread.

    Upon instantiation, a new thread is created against the given ChatGPT Assistant

    In future we can decouple Assistants from Threads: 
    - create an Assistant class that can contain multiple AssistantThreads.
    """
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.openai_client = OpenAI()
        self.assistant_handle = self.openai_client.beta.assistants.retrieve(config.get("id"))
        self.last_user_message_id = None
        self.init_messages()

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
        """
        Create a new OpenAI thread and return the default messages.
        """
        self.thread = self.openai_client.beta.threads.create()  

        return self.config.get("messages", [])[:]


    def add_message(self, our_message: Message) -> ThreadMessage:
        """
        Send a message to the chatgpt Thread associated with this assistant and return the response.
        """
        their_message = self.openai_client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role=our_message['role'],
            content=our_message['content'],
        )
        self.last_user_message_id = their_message.id
        return their_message

    def run_thread(self) -> ThreadRun:
        """
        Start a Run on the chatgpt Thread associated with this assistant and wait for it to complete.
        """
        run = self.openai_client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_handle.id,
        )
        # TODO move out of this function. Use async primitive instead.
        while run.status != "completed":
            time.sleep(2)
            run = self.openai_client.beta.threads.runs.retrieve(run.id, thread_id=self.thread.id)

        return run

    def fetch_messages(self, since_last_user_message: bool) -> List[ThreadMessage]:
        # TODO keep SyncCursorPage instead of immediately converting to list? 
        # May become a problem when threads become long enough to split into multiple pages
        messages = list(self.openai_client.beta.threads.messages.list(
            thread_id=self.thread.id
        ))
        # Messages come back in reverse chronological order. We reverse them.
        messages.reverse()

        # return all new messages (i.e. all the ones after the one we just added)
        if since_last_user_message and self.last_user_message_id:
            last_message_id = self.last_user_message_id
            message_ids = [message.id for message in messages]
            last_message_index = message_ids.index(last_message_id)
            if last_message_index == -1:
                raise ValueError("last_message_id not found in messages")
            messages = messages[last_message_index+1:]

        return self.add_citations_to_messages(messages)
    
    def add_citations_to_messages(self, messages):  
        messages_with_citations = []
        for message in messages:
            # Extract the message content
            # Assumes one text message per message
            if len(message.content) > 1:
                raise ValueError("Unimplemented: More than one text message per message")
            message_content = message.content[0].text
            annotations = message_content.annotations
            citations = []

            # Iterate over the annotations and add footnotes
            for index, annotation in enumerate(annotations):
                # Replace the text with a footnote
                message_content.value = message_content.value.replace(annotation.text, f' [{index}]')

                # Gather citations based on annotation attributes
                if (file_citation := getattr(annotation, 'file_citation', None)):
                    cited_file = self.openai_client.files.retrieve(file_citation.file_id)
                    searchable_quote = ' '.join(file_citation.quote.split()[:6])
                    citations.append(f'[{index}] {cited_file.filename} - (Search: "{searchable_quote}")')
                elif (file_path := getattr(annotation, 'file_path', None)):
                    cited_file = self.openai_client.files.retrieve(file_path.file_id)
                    citations.append(f'[{index}] Click <here> to download {cited_file.filename}')

            # Add footnotes to the end of the message before displaying to user
            message_content.value += '\n\n' + '\n'.join(citations)
            messages_with_citations.append(message_content.value)
        
        return messages

    def get_thread_id(self):
        return self.thread.id
    
    def get_assistant_id(self):
        return self.assistant_handle.id

@dataclass
class AssistantGlobalArgs:
    assistant_name: str

def init_assistant(
    args: AssistantGlobalArgs, custom_assistants: Dict[str, AssistantConfig]
) -> AssistantThread:
    name = args.assistant_name
    if name in custom_assistants:
        assistant = AssistantThread.from_config(name, custom_assistants[name])
    elif name in DEFAULT_ASSISTANTS:
        assistant = AssistantThread.from_config(name, DEFAULT_ASSISTANTS[name])
    else:
        print(f"Unknown assistant: {name}")
        sys.exit(1)

    return assistant

def thread_message_to_text(thread_messages: ThreadMessage) -> str:
    thread_messages = [content for thread_message in thread_messages for content in thread_message.content]
    thread_contents = filter(lambda content: content.type == "text", thread_messages)
    thread_texts = [content.text.value + "\n" for content in thread_contents]
    return thread_texts