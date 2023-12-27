"""
Since the openai python library doesn't have type annotations, we have to define our own types for the objects we get back from the API.
"""
class MessageText:
    def __init__(self, value, annotations):
        self.value = value
        self.annotations = annotations

class Content:
    def __init__(self, type, text):
        self.type = type
        self.text = text

# https://platform.openai.com/docs/api-reference/messages/object
class ThreadMessage:
    def __init__(self, id, object, created_at, thread_id, role, content, file_ids, assistant_id, run_id, metadata):
        self.id = id
        self.object = object
        self.created_at = created_at
        self.thread_id = thread_id
        self.role = role
        self.content = [Content(item['type'], MessageText(item['text']['value'], item['text']['annotations'])) for item in content]
        self.file_ids = file_ids
        self.assistant_id = assistant_id
        self.run_id = run_id
        self.metadata = metadata     

class Tool:
    def __init__(self, type):
        self.type = type

# https://platform.openai.com/docs/api-reference/runs/object
class ThreadRun:
    def __init__(self, id, object, created_at, assistant_id, thread_id, status, started_at, expires_at, cancelled_at, failed_at, completed_at, last_error, model, instructions, tools, file_ids, metadata):
        self.id = id
        self.object = object
        self.created_at = created_at
        self.assistant_id = assistant_id
        self.thread_id = thread_id
        self.status = status
        self.started_at = started_at
        self.expires_at = expires_at
        self.cancelled_at = cancelled_at
        self.failed_at = failed_at
        self.completed_at = completed_at
        self.last_error = last_error
        self.model = model
        self.instructions = instructions
        self.tools = [Tool(tool['type']) for tool in tools]
        self.file_ids = file_ids
        self.metadata = metadata
