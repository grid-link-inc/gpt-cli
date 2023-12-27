from gptcli.session import ChatListener
from gptcli.types import Message
from pathlib import Path

# TODO use the logging package to do writes instead of our own class

class PersistChatListener(ChatListener):
    def __init__(self, thread_id, assistant_id: str):
        # create a file with the thread id as the name in the current directory
        Path("./logs").mkdir(exist_ok=True)
        self.file_handle = open(f"./logs/gptcli-{assistant_id}-{thread_id}.log", "w")

    def on_chat_start(self):
        self.file_handle.write("Chat started.\n")


    def on_chat_clear(self):
        self.file_handle.write("Cleared the conversation.\n")
        
    def on_chat_rerun(self, success: bool):
        if success:
            self.file_handle.write("Re-generating the last message.\n")

    def on_error(self, e: Exception):
        self.file_handle.write(str(e))
        self.file_handle.close()

    def on_chat_message(self, message: Message):
        self.file_handle.write(f"{message['role']}: {message['content']}\n")

    def on_chat_end(self):
        self.file_handle.close()