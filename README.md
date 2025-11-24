# Code Agent with RAG Context Management

An autonomous coding agent system with integrated RAG context management, featuring intelligent history retrieval through an independent microservice architecture.

## 🏗️ Architecture Design

```
┌─────────────────┐      REST API      ┌──────────────────────┐
│  Agent Client   │ ◄──────────────────► │ Context Service      │
│  (agent_with_   │                      │ (FastAPI + ChromaDB) │
│   rag.py)       │                      │                      │
└─────────────────┘                      └──────────────────────┘
         │                                         │
         │                                         ▼
         ▼                               ┌──────────────────┐
┌─────────────────┐                     │  Vector Database │
│  Ollama LLM     │                     │   (ChromaDB)     │
│  (qwen2.5)      │                     └──────────────────┘
└─────────────────┘
```

### Core Features

1. **Semantic Retrieval**: Vector similarity search based on sentence-transformers
2. **Hierarchical Context**: Combines semantic relevance + temporal continuity
3. **Microservice Architecture**: Independently deployable, easily scalable
4. **Type Classification**: Automatic message type identification (user_query, tool_call, agent_response)
5. **Session Isolation**: Multi-session management via session_id

## 📦 Quick Start

### Method 1: Docker Compose (Recommended)

```bash
# 1. Prepare file structure
project/
├── context_service.py
├── agent_with_rag.py
├── admin_ui.py
├── docker-compose.yml
├── Dockerfile.context
├── requirements_context.txt
└── requirements_agent.txt

# 2. Start services
docker-compose up -d

# 3. Check service status
docker-compose ps

# 4. Run Agent (ensure Ollama is running first)
python agent_with_rag.py
```

Access Admin UI: http://localhost:8501

### Method 2: Local Development

```bash
# 1. Install dependencies
pip install -r requirements_context.txt
pip install -r requirements_agent.txt

# 2. Start context service
python context_service.py

# 3. Run Agent in new terminal
python agent_with_rag.py
```

## 🔧 Configuration

### Environment Variables

```bash
# Agent configuration
export CONTEXT_SERVICE_URL="http://localhost:8000"
export OLLAMA_HOST="http://localhost:11434"

# Context Service configuration
export CHROMA_DB_PATH="./chroma_db"
```

### Tuning Parameters

In `agent_with_rag.py`:
```python
MAX_CONTEXT_ITEMS = 5  # Number of relevant context items to retrieve
RECENT_CONTEXT_LIMIT = 3  # Number of recent conversations to maintain
```

## 📚 API Documentation

### Context Service API

#### 1. Add Context
```bash
POST /context/add
{
  "session_id": "uuid-string",
  "message": {
    "role": "user",
    "content": "message content",
    "timestamp": "2024-01-01T12:00:00",
    "metadata": {"type": "user_query"}
  }
}
```

#### 2. Semantic Search
```bash
POST /context/query
{
  "session_id": "uuid-string",
  "query": "search query",
  "top_k": 5,
  "filter_by_type": "tool_call"  # optional
}
```

#### 3. Get Recent Conversations
```bash
POST /context/recent?session_id=xxx&limit=10&offset=0
```

#### 4. Session Statistics
```bash
GET /context/stats/{session_id}
```

#### 5. Clear Context
```bash
POST /context/clear
{
  "session_id": "uuid-string"
}
```

Full API documentation: http://localhost:8000/docs

## 🎯 Usage Examples

### Basic Conversation
```
You: Create a Python file with Hello World

🤖 Agent: [Calls write_file tool]
✅ Result: File 'hello.py' written successfully.
```

### Context-Aware Conversation
```
You: Where is the file I just created?

🤖 Agent: [Retrieves previous write_file operation from context]
Based on the previous operation, the file is located at ./hello.py
```

### Multi-Turn Collaboration
```
You: Read the contents of hello.py
🤖 Agent: [Executes read_file]

You: Change it to print Hello World in Chinese
🤖 Agent: [Uses context to understand "it" refers to hello.py, executes write_file]
```

### Special Commands
```
stats   - View current session statistics
clear   - Clear current session context
quit    - Exit program
```

## 🔍 How It Works

### 1. Context Storage Flow
```
User Input → Store in ChromaDB (generate embedding)
         ↓
    Assign type label (user_query/tool_call/agent_response)
         ↓
    Associate with session_id and timestamp
```

### 2. Context Retrieval Flow
```
New User Query → Generate query embedding
              ↓
    Search top_k similar vectors in ChromaDB
              ↓
    Fetch recent N conversations (temporal continuity)
              ↓
    Combine to build context-aware prompt
```

### 3. Prompt Building Strategy
```
[System Prompt]
  ├─ Tool definitions
  ├─ Relevant historical context (semantically similar, top 3)
  ├─ Recent conversations (temporally continuous, last 3)
  └─ Current user request
```

## 📊 Performance Metrics

- **Retrieval Latency**: < 100ms (top-5 query)
- **Storage Size**: ~1KB per message (including embedding)
- **Concurrency**: FastAPI async processing
- **Scalability**: Supports multi-session concurrency

## 🛠️ Advanced Configuration

### 1. Change Embedding Model
```python
# Modify in context_service.py
embedding_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
```

Recommended models:
- `all-MiniLM-L6-v2` (fast, 384 dimensions)
- `all-mpnet-base-v2` (accurate, 768 dimensions)
- `paraphrase-multilingual-mpnet-base-v2` (multilingual)

### 2. Adjust Vector Database
```python
# Use persistent storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Use in-memory mode (for testing)
chroma_client = chromadb.Client()
```

### 3. Custom Filter Strategy
```python
# Add custom filters in query_context
where_filter = {
    "session_id": session_id,
    "type": "tool_call",
    "$and": [
        {"metadata.tool_name": "write_file"},
        {"timestamp": {"$gte": "2024-01-01"}}
    ]
}
```

## 🐛 Troubleshooting

### Issue 1: Context service connection failed
```bash
# Check service status
curl http://localhost:8000/

# View logs
docker-compose logs context-service
```

### Issue 2: ChromaDB permission error
```bash
# Ensure directory permissions
chmod -R 755 ./chroma_db
```

### Issue 3: Slow embedding model download
```bash
# Pre-download model
python -c "from sentence_transformers import SentenceTransformer; \
           SentenceTransformer('all-MiniLM-L6-v2')"
```

## 🚀 Extension Suggestions

### 1. Additional Context Strategies
- **Time Window Filter**: Retrieve only context from last N hours
- **Importance Scoring**: Weight messages by importance
- **Topic Clustering**: Group and manage conversations by topic

### 2. Performance Optimization
- **Caching**: Redis cache for high-frequency queries
- **Batch Processing**: Batch insertions to reduce I/O
- **Async Storage**: Non-blocking context saving

### 3. Feature Enhancements
- **Multimodal Context**: Support code AST, images, documents
- **Cross-Session Retrieval**: Search across all user sessions
- **Auto-Summarization**: Automatically generate summaries for long conversations

## 📝 License

MIT License

## 🤝 Contributing

Issues and Pull Requests are welcome!