"""
Context Management Microservice for Code Agent
Uses ChromaDB for vector storage and FastAPI for REST API
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Code Agent Context Service", version="1.0.0")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db", settings=Settings(anonymized_telemetry=False)
)

# Initialize embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Create or get collection
try:
    collection = chroma_client.get_collection(name="agent_context")
except:
    collection = chroma_client.create_collection(
        name="agent_context",
        metadata={"description": "Code agent conversation history"},
    )
# =================================================================
# ==================== Request/Response Models ====================
# =================================================================


class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AddContextRequest(BaseModel):
    session_id: str
    message: Message


class QueryContextRequest(BaseModel):
    session_id: str
    query: str
    top_k: Optional[int] = 5
    filter_by_type: Optional[str] = None  # tool_call, user_query, agent_response


class ContextResponse(BaseModel):
    messages: List[Dict[str, Any]]
    total_count: int


class ClearContextRequest(BaseModel):
    session_id: str


# =================================================================
# ==================== Helper Functions ===========================
# =================================================================


def generate_id(session_id: str, content: str, timestamp: str) -> str:
    """Generate unique ID for each context entry"""
    raw = f"{session_id}_{content}_{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()


def extract_metadata(message: Message, session_id: str) -> Dict[str, Any]:
    """Extract metadata from message"""
    metadata = message.metadata or {}

    # Detect message type
    msg_type = "chat"
    if message.role == "user":
        msg_type = "user_query"
    elif "tool" in message.content.lower() or '{"tool":' in message.content:
        msg_type = "tool_call"
    elif message.role == "assistant":
        msg_type = "agent_response"

    metadata.update(
        {
            "session_id": session_id,
            "role": message.role,
            "type": msg_type,
            "timestamp": message.timestamp or datetime.now().isoformat(),
            "content_length": len(message.content),
        }
    )

    return metadata


def compress_long_content(content: str, max_length: int = 1000) -> str:
    """Compress overly long content for embedding"""
    if len(content) <= max_length:
        return content

    # Keep beginning and end
    half = max_length // 2
    return f"{content[:half]}\n... [content truncated] ...\n{content[-half:]}"


# =================================================================
# ==================== API Endpoints ===========================
# =================================================================


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Code Agent Context Service",
        "status": "running",
        "total_contexts": collection.count(),
    }


@app.post("/context/add")
async def add_context(request: AddContextRequest):
    """Add a message to context storage"""
    try:
        timestamp = request.message.timestamp or datetime.now().isoformat()
        doc_id = generate_id(request.session_id, request.message.content, timestamp)

        # Extract metadata
        metadata = extract_metadata(request.message, request.session_id)

        # Compress content if too long
        content_for_embedding = compress_long_content(request.message.content)

        # Generate embedding
        embedding = embedding_model.encode(content_for_embedding).tolist()

        # Add to ChromaDB
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[request.message.content],
            metadatas=[metadata],
        )

        return {
            "status": "success",
            "id": doc_id,
            "message": "Context added successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding context: {str(e)}")


@app.post("/context/query")
async def query_context(request: QueryContextRequest) -> ContextResponse:
    """Query relevant context using semantic search"""
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(request.query).tolist()

        # Build filter
        where_filter = {"session_id": request.session_id}
        if request.filter_by_type:
            where_filter["type"] = request.filter_by_type

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(request.top_k, 20),
            where=where_filter,
        )

        # Format results
        messages = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                messages.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": (
                            results["distances"][0][i]
                            if "distances" in results
                            else None
                        ),
                    }
                )

        return ContextResponse(messages=messages, total_count=len(messages))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying context: {str(e)}")


@app.post("/context/recent")
async def get_recent_context(session_id: str, limit: int = 10, offset: int = 0):
    """Get recent messages in chronological order"""
    try:
        # Get all messages for session
        results = collection.get(where={"session_id": session_id}, limit=limit + offset)

        if not results["ids"]:
            return ContextResponse(messages=[], total_count=0)

        # Sort by timestamp
        messages_with_time = []
        for i in range(len(results["ids"])):
            messages_with_time.append(
                {
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "timestamp": results["metadatas"][i].get("timestamp", ""),
                }
            )

        messages_with_time.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply offset and limit
        paginated = messages_with_time[offset : offset + limit]

        return ContextResponse(messages=paginated, total_count=len(messages_with_time))

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting recent context: {str(e)}"
        )


@app.post("/context/clear")
async def clear_context(request: ClearContextRequest):
    """Clear all context for a session"""
    try:
        # Get all IDs for the session
        results = collection.get(where={"session_id": request.session_id})

        if results["ids"]:
            collection.delete(ids=results["ids"])

        return {"status": "success", "deleted_count": len(results["ids"])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing context: {str(e)}")


@app.get("/context/stats/{session_id}")
async def get_context_stats(session_id: str):
    """Get statistics for a session"""
    try:
        results = collection.get(where={"session_id": session_id})

        if not results["ids"]:
            return {"session_id": session_id, "total_messages": 0, "by_type": {}}

        # Count by type
        type_counts = {}
        for metadata in results["metadatas"]:
            msg_type = metadata.get("type", "unknown")
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1

        return {
            "session_id": session_id,
            "total_messages": len(results["ids"]),
            "by_type": type_counts,
            "oldest_message": min(m.get("timestamp", "") for m in results["metadatas"]),
            "newest_message": max(m.get("timestamp", "") for m in results["metadatas"]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@app.delete("/context/all")
async def clear_all_context():
    """Clear ALL context (use with caution!)"""
    try:
        chroma_client.delete_collection(name="agent_context")
        collection = chroma_client.create_collection(
            name="agent_context",
            metadata={"description": "Code agent conversation history"},
        )
        return {"status": "success", "message": "All context cleared"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error clearing all context: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
