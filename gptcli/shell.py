import os
import logging
import sys
import subprocess
import tempfile
from gptcli.gpt_interfaces.wrapper.wrapper import Wrapper


def simple_response(wrapper: Wrapper, prompt: str, stream: bool) -> None:
    messages = wrapper.init_messages()
    messages.append({"role": "user", "content": prompt})
    logging.info("User: %s", prompt)
    response_iter = wrapper.complete_chat(messages, stream=stream)
    result = ""
    try:
        for response in response_iter:
            result += response
            sys.stdout.write(response)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.flush()
        logging.info("Wrapper: %s", result)


def execute(wrapper: Wrapper, prompt: str) -> None:
    messages = wrapper.init_messages()
    messages.append({"role": "user", "content": prompt})
    logging.info("User: %s", prompt)
    response_iter = wrapper.complete_chat(messages, stream=False)
    result = next(response_iter)
    logging.info("Wrapper: %s", result)

    with tempfile.NamedTemporaryFile(mode="w", prefix="gptcli-", delete=False) as f:
        f.write("# Edit the command to execute below. Save and exit to execute it.\n")
        f.write("# Delete the contents to cancel.\n")
        f.write(result)
        f.flush()

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, f.name])

    with open(f.name) as f:
        lines = [line for line in f.readlines() if not line.startswith("#")]
        command = "".join(lines).strip()

    if command == "":
        print("No command to execute.")
        return

    shell = os.environ.get("SHELL", "/bin/bash")

    logging.info(f"Executing: {command}")
    print(f"Executing:\n{command}")
    subprocess.run([shell, f.name])
