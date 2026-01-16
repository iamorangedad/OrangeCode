import os
from rag.context_client import ContextClient


def test_add_message():
    CONTEXT_SERVICE_URL = os.getenv("CONTEXT_SERVICE_URL", "http://localhost:8000")
    SESSION_ID = str(uuid.uuid4())
    context_client = ContextClient(CONTEXT_SERVICE_URL, SESSION_ID)
    context_client.add_message("user", user_input, {"type": "user_query"})
