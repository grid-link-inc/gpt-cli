from abc import abstractmethod
from openai import BadRequestError, OpenAIError
from gptcli.types import Message
from typing import Any, Dict, List, Tuple
from gptcli.assistant import AssistantThread, thread_message_to_text

class ResponseStreamer:
    def __enter__(self) -> "ResponseStreamer":
        return self

    def on_next_token(self, token: str):
        pass

    def __exit__(self, *args):
        pass


class ChatListener:
    def on_chat_start(self):
        pass

    def on_chat_clear(self):
        pass

    def on_chat_rerun(self, success: bool):
        pass

    def on_error(self, error: Exception):
        pass

    def response_streamer(self) -> ResponseStreamer:
        return ResponseStreamer()

    def on_chat_message(self, message: Message):
        pass

    def on_chat_response(
        self, messages: List[Message], response: Message
    ):
        pass

    def on_chat_end(
        self
    ):
        pass


class UserInputProvider:
    @abstractmethod
    def get_user_input(self) -> Tuple[str, Dict[str, Any]]:
        pass


class InvalidArgumentError(Exception):
    def __init__(self, message: str):
        self.message = message


COMMAND_CLEAR = (":clear", ":c")
COMMAND_QUIT = (":quit", ":q")
COMMAND_RERUN = (":rerun", ":r")
COMMAND_HELP = (":help", ":h", ":?")
ALL_COMMANDS = [*COMMAND_CLEAR, *COMMAND_QUIT, *COMMAND_RERUN, *COMMAND_HELP]
COMMANDS_HELP = """
Commands:
- `:clear` / `:c` / Ctrl+C - Clear the conversation.
- `:quit` / `:q` / Ctrl+D - Quit the program.
- `:rerun` / `:r` / Ctrl+R - Re-run the last message.
- `:help` / `:h` / `:?` - Show this help message.
"""

class ChatSession:
    # This class represents a single CLI session. Including the assistant and messages between it and the user.
    def __init__(
        self,
        assistant: AssistantThread,
        listener: ChatListener,
    ):
        self.assistant = assistant
        self.messages: List[Message] = assistant.init_messages()
        self.user_prompts: List[Message] = []
        self.listener = listener

    def _clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        self.listener.on_chat_clear()

    def _rerun(self):
        if len(self.user_prompts) == 0:
            self.listener.on_chat_rerun(False)
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        self.listener.on_chat_rerun(True)
        self._get_response()

    def _get_response(self) -> bool:
        """
        Respond to the user's input and return whether the assistant's response was saved.
        """
        next_response: str = ""
        try:
            self.assistant.run_thread()
            # Fetch the text of all recent messages
            thread_messages = self.assistant.fetch_messages(since_last_user_message=True)
            thread_texts = thread_message_to_text(thread_messages)

            with self.listener.response_streamer() as stream:
                for response in thread_texts:
                    next_response += response
                    stream.on_next_token(response)
        except KeyboardInterrupt:
            # If the user interrupts the response, we'll just return what we have so far
            pass
        except BadRequestError as e:
            self.listener.on_error(e)
            return False
        except OpenAIError as e:
            self.listener.on_error(e)
            return True

        response_message: Message = {"role": "assistant", "content": next_response}
        self.listener.on_chat_message(response_message)
        self.listener.on_chat_response(self.messages, response_message)

        self.messages = self.messages + [response_message]
        return True

    def _add_user_message(self, user_input: str) -> Message:
        user_message: Message = {"role": "user", "content": user_input}
        self.assistant.add_message(user_message)
        self.messages = self.messages + [user_message]
        self.listener.on_chat_message(user_message)
        self.user_prompts.append(user_message)
        return user_message

    def _rollback_user_message(self):
        self.messages = self.messages[:-1]
        self.user_prompts = self.user_prompts[:-1]

    def _print_help(self):
        with self.listener.response_streamer() as stream:
            stream.on_next_token(COMMANDS_HELP)

    def _quit(self):
        self.listener.on_chat_end()

    def process_input(self, user_input: str, args: Dict[str, Any]):
        """
        Process the user's input and return whether the session should continue.
        """
        if not self._validate_args(args):
            return True

        if user_input in COMMAND_QUIT:
            self._quit()
            return False
        elif user_input in COMMAND_CLEAR:
            self._clear()
            return True
        elif user_input in COMMAND_RERUN:
            self._rerun()
            return True
        elif user_input in COMMAND_HELP:
            self._print_help()
            return True

        self._add_user_message(user_input)
        response_saved = self._get_response()
        if not response_saved:
            self._rollback_user_message()

        return True

    def _validate_args(self, args: Dict[str, Any]) -> bool:
        for key in args:
            supported_overrides = self.assistant.supported_overrides()
            if key not in supported_overrides:
                self.listener.on_error(
                    InvalidArgumentError(
                        f"Invalid argument: {key}. Allowed arguments: {supported_overrides}"
                    )
                )
                return False
        return True
    
    def loop(self, input_provider: UserInputProvider):
        self.listener.on_chat_start()
        while self.process_input(*input_provider.get_user_input()):
            pass
