from unittest import mock
import httpx

from openai import BadRequestError, OpenAIError

from gptcli.session import ChatSession
from gptcli.openai_types import ThreadMessage


def setup_assistant_mock():
    assistant_mock = mock.MagicMock()
    assistant_mock.init_messages.return_value = []
    return assistant_mock


def setup_listener_mock():
    listener_mock = mock.MagicMock()
    response_streamer_mock = mock.MagicMock()
    response_streamer_mock.__enter__.return_value = response_streamer_mock
    listener_mock.response_streamer.return_value = response_streamer_mock
    return listener_mock, response_streamer_mock


def setup_session():
    assistant_mock = setup_assistant_mock()
    listener_mock, _ = setup_listener_mock()
    session = ChatSession(assistant_mock, listener_mock)
    return assistant_mock, listener_mock, session

def create_thread_message(role, content):
    return ThreadMessage(
        id="msg_feBzkJcQlHRyg4BsLm9GHwwf",
        assistant_id="asst_jCP75X9phRfVjZ8Q4iBistYT",
        content=[
            {
                "text": {
                    "annotations": [],
                    "value": content
                },
                "type": "text"
            }
        ],
        created_at=1703532865,
        file_ids=[],
        metadata={},
        object="thread.message",
        role=role,
        run_id="run_ZuVSExmplLDv2Z76FJNRXEzw",
        thread_id="thread_RSkXNj7NpXmAdgUTDc8Fm3XX"
    )


def test_simple_input():
    assistant_mock, listener_mock, session = setup_session()

    expected_response = "assistant message"
    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", expected_response)
    ]

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    assistant_message = {"role": "assistant", "content": expected_response}

    assistant_mock.add_message.assert_called_once_with(user_message)
    assistant_mock.run_thread.assert_called_once()
    assistant_mock.fetch_messages.assert_called_once()
    listener_mock.on_chat_message.assert_has_calls(
        [mock.call(user_message), mock.call(assistant_message)]
    )


def test_quit():
    _, _, session = setup_session()
    should_continue = session.process_input(":q", {})
    assert not should_continue

def test_clear():
    user_input = "user message"
    assistant_mock, listener_mock, session = setup_session()

    assistant_mock.init_messages.assert_called_once()
    assistant_mock.init_messages.reset_mock()

    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", "assistant_message")
    ]   

    should_continue = session.process_input(user_input, {})
    assert should_continue

    assistant_mock.add_message.assert_called_once_with(
        {"role": "user", "content": user_input}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": user_input}),
            mock.call({"role": "assistant", "content": "assistant_message"}),
        ]
    )
    assistant_mock.add_message.reset_mock()
    assistant_mock.fetch_messages.reset_mock()
    listener_mock.on_chat_message.reset_mock()

    should_continue = session.process_input(":c", {})
    assert should_continue

    assistant_mock.init_messages.assert_called_once()
    listener_mock.on_chat_clear.assert_called_once()
    assistant_mock.add_message.assert_not_called()

    assistant_output = "assistant message 2"
    user_input_2 = "user message 2"
    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", assistant_output)
    ]

    should_continue = session.process_input(user_input_2, {})
    assert should_continue

    assistant_mock.add_message.assert_called_once_with(
        {"role": "user", "content": user_input_2}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": user_input_2}),
            mock.call({"role": "assistant", "content": assistant_output}),
        ]
    )


def test_rerun():
    assistant_mock, listener_mock, session = setup_session()

    assistant_mock.init_messages.assert_called_once()
    assistant_mock.init_messages.reset_mock()

    # Re-run before any input shouldn't do anything
    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.init_messages.assert_not_called()
    assistant_mock.complete_chat.assert_not_called()
    listener_mock.on_chat_message.assert_not_called()
    listener_mock.on_chat_rerun.assert_called_once_with(False)

    listener_mock.on_chat_rerun.reset_mock()

    # Now proper re-run
    assistant_output = "assistant message"
    user_input = "user message"
    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", assistant_output)
    ]

    should_continue = session.process_input(user_input, {})
    assert should_continue

    assistant_mock.add_message.assert_called_once_with(
        {"role": "user", "content": user_input}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": user_input}),
            mock.call({"role": "assistant", "content": assistant_output}),
        ]
    )
    assistant_mock.run_thread.reset_mock()
    assistant_mock.add_message.reset_mock()
    assistant_mock.fetch_messages.reset_mock()
    listener_mock.on_chat_message.reset_mock()

    assistant_output_after_reset = "assistant message after reste"
    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", assistant_output_after_reset)
    ]

    should_continue = session.process_input(":r", {})
    assert should_continue

    listener_mock.on_chat_rerun.assert_called_once_with(True)
    assistant_mock.run_thread.assert_called_once()
    assistant_mock.fetch_messages.assert_called_once()

    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "assistant", "content": assistant_output_after_reset}),
        ]
    )


def test_invalid_request_error():
    assistant_mock, listener_mock, session = setup_session()

    error = BadRequestError(
        "error message",
        response=httpx.Response(
            401, request=httpx.Request("POST", "http://localhost/")
        ),
        body=None,
    )
    assistant_mock.run_thread.side_effect = error

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    listener_mock.on_chat_message.assert_has_calls([mock.call(user_message)])
    listener_mock.on_error.assert_called_once_with(error)
    print("done")
    # Now rerun shouldn't do anything because user input was not saved
    assistant_mock.run_thread.reset_mock()
    listener_mock.on_chat_message.reset_mock()
    listener_mock.on_error.reset_mock()

    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.run_thread.assert_not_called()
    listener_mock.on_chat_message.assert_not_called()
    listener_mock.on_error.assert_not_called()
    listener_mock.on_chat_rerun.assert_called_once_with(False)


class OpenAITestError(OpenAIError):
    pass


def test_openai_error():
    assistant_mock, listener_mock, session = setup_session()

    error = OpenAITestError()
    assistant_mock.run_thread.side_effect = error

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    listener_mock.on_chat_message.assert_has_calls([mock.call(user_message)])
    listener_mock.on_error.assert_called_once_with(error)

    # Re-run should work
    assistant_mock.run_thread.reset_mock()
    listener_mock.on_chat_message.reset_mock()
    listener_mock.on_error.reset_mock()

    assistant_mock.run_thread.side_effect = None
    assistant_output = "assistant message"
    assistant_message = {"role": "assistant", "content": assistant_output}
    assistant_mock.fetch_messages.return_value = [
        create_thread_message("assistant", assistant_output)
    ]

    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.add_message.assert_called_once_with(user_message)
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call(assistant_message),
        ]
    )
