import requests


class ContextClient:
    """Client for interacting with context management service"""

    def __init__(self, base_url: str, session_id: str):
        self.base_url = base_url
        self.session_id = session_id

    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add a message to context storage"""
        try:
            response = requests.post(
                f"{self.base_url}/context/add",
                json={
                    "session_id": self.session_id,
                    "message": {
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": metadata or {},
                    },
                },
                timeout=5,
            )
            return response.json() if response.ok else None
        except Exception as e:
            console.print(f"[dim red]Context service error: {e}[/dim red]")
            return None

    def query_relevant_context(self, query: str, top_k: int = 5):
        """Query relevant context based on semantic similarity"""
        try:
            response = requests.post(
                f"{self.base_url}/context/query",
                json={"session_id": self.session_id, "query": query, "top_k": top_k},
                timeout=5,
            )
            if response.ok:
                return response.json()["messages"]
            return []
        except Exception as e:
            console.print(f"[dim red]Context query error: {e}[/dim red]")
            return []

    def get_recent_context(self, limit: int = 5):
        """Get recent conversation history"""
        try:
            response = requests.post(
                f"{self.base_url}/context/recent",
                params={"session_id": self.session_id, "limit": limit},
                timeout=5,
            )
            if response.ok:
                return response.json()["messages"]
            return []
        except Exception as e:
            console.print(f"[dim red]Recent context error: {e}[/dim red]")
            return []

    def get_stats(self):
        """Get session statistics"""
        try:
            response = requests.get(
                f"{self.base_url}/context/stats/{self.session_id}", timeout=5
            )
            return response.json() if response.ok else None
        except Exception as e:
            return None
