# Agent No-RAG Deployment

This directory contains Kubernetes manifests to deploy the Orange Code agent without RAG (Retrieval-Augmented Generation) capabilities.

## Architecture

The deployment consists of:
- **agent-no-rag**: Autonomous coding agent with in-memory conversation history
- **agent-config**: ConfigMap containing agent scripts and requirements
- **Namespace & Network Policy**: Isolated namespace with egress to Ollama service

## Key Differences from RAG Version

| Feature | RAG Version | No-RAG Version |
|---------|-------------|----------------|
| Context Management | ChromaDB + FastAPI microservice | In-memory (10 messages) |
| Memory Usage | 2-4Gi | 512Mi-1Gi (75% reduction) |
| Storage | 15Gi PVCs | None |
| Services | 2 LoadBalancers | 0 (kubectl exec access) |
| Latency | Higher (embedding + retrieval) | Lower (direct LLM) |
| History Persistence | Persistent vector store | Session-only |

## Quick Start

### Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured
- Node with hostname `ubuntu` (as defined in nodeSelector)
- External Ollama service at `http://10.0.0.56:11434`

### Deployment

```bash
# Deploy agent-no-rag
kubectl apply -k deploy-no-rag/k8s/

# Check deployment status
kubectl get all -n orange-code

# Verify pod is running
kubectl get pods -n orange-code -l app=agent-no-rag
```

### Accessing the Agent

```bash
# Interactive access (recommended)
kubectl exec -it deployment/agent-no-rag -n orange-code -- bash

# View logs in real-time
kubectl logs -f deployment/agent-no-rag -n orange-code
```

## Configuration

### Environment Variables

- `OLLAMA_HOST`: Ollama service URL (default: `http://10.0.0.56:11434`)
- `PYTHONUNBUFFERED`: Ensures immediate log output

### Resource Limits

- **Memory**: 512Mi request, 1Gi limit
- **CPU**: 250m request, 500m limit

### Customization

#### Update Ollama Host

```bash
# Edit deployment
kubectl edit deployment agent-no-rag -n orange-code

# Or patch it
kubectl patch deployment agent-no-rag -n orange-code -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"agent-no-rag","env":[{"name":"OLLAMA_HOST","value":"http://your-ollama:11434"}]}]}}}}'
```

#### Modify Conversation History Limit

Edit `agent-config.yaml` and update line:
```python
for msg in conversation_history[-10:]:  # Change 10 to desired limit
```

Then apply changes:
```bash
kubectl apply -f deploy-no-rag/k8s/agent-config.yaml
kubectl rollout restart deployment/agent-no-rag -n orange-code
```

## Agent Features

### Available Tools

1. **read_file**: Read file content
2. **write_file**: Write content to file  
3. **list_files**: List files in current directory
4. **run_command**: Execute shell commands with confirmation

### Commands

- `quit`/`exit`: Stop the agent
- `stats`: Show session statistics
- `clear`: Clear conversation history

### Example Usage

```
You: Read the main.py file
🤖 Agent: {"tool": "read_file", "args": {"path": "main.py"}}
✅ Result: [File content displayed]
🤖 Agent: I can see the main.py file contains...

You: Create a new function to calculate fibonacci
🤖 Agent: {"tool": "write_file", "args": {"path": "fibonacci.py", "content": "..."}}
✅ Result: Success: File 'fibonacci.py' written successfully.
```

## Monitoring

### Check Pod Status
```bash
kubectl get pods -n orange-code -l app=agent-no-rag -w
```

### View Logs
```bash
kubectl logs deployment/agent-no-rag -n orange-code -f
```

### Resource Usage
```bash
kubectl top pods -n orange-code -l app=agent-no-rag
```

### Ollama Connectivity Test
```bash
kubectl exec deployment/agent-no-rag -n orange-code -- curl -v http://10.0.0.56:11434
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -n orange-code -l app=agent-no-rag

# Verify node selector
kubectl get nodes --show-labels
```

### Ollama Connection Issues

```bash
# Test from pod
kubectl exec deployment/agent-no-rag -n orange-code -- \
  python3 -c "import ollama; print(ollama.Client(host='http://10.0.0.56:11434').list())"

# Check network policy
kubectl get networkpolicy orange-code-network-policy -n orange-code -o yaml
```

### Agent Not Responding

```bash
# Check if agent is running
kubectl exec deployment/agent-no-rag -n orange-code -- ps aux

# Restart deployment
kubectl rollout restart deployment/agent-no-rag -n orange-code
```

## Maintenance

### Update Agent Code

1. Edit `agent-config.yaml` with new code
2. Apply changes: `kubectl apply -f deploy-no-rag/k8s/agent-config.yaml`
3. Restart deployment: `kubectl rollout restart deployment/agent-no-rag -n orange-code`

### Scale Deployment

```bash
# Scale replicas (not recommended for interactive CLI)
kubectl scale deployment agent-no-rag --replicas=2 -n orange-code
```

### Backup/Restore

No persistent storage needed - conversation history is in-memory only.

## Cleanup

```bash
# Remove deployment only
kubectl delete deployment agent-no-rag -n orange-code
kubectl delete configmap agent-config -n orange-code

# Remove entire namespace
kubectl delete namespace orange-code
```

## Development

### Local Testing

```bash
# Test locally before deployment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_agent.txt
python3 agent_no_rag.py
```

### Build Custom Image (Optional)

If you prefer building an image instead of using ConfigMap:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_agent.txt .
RUN pip install -r requirements_agent.txt
COPY agent_no_rag.py utils.py .
CMD ["python3", "agent_no_rag.py"]
```

Then update deployment to use your image.

## Security

- Network policy restricts egress to required services only
- No persistent storage (no data at rest)
- Interactive access requires kubectl access
- Tool execution requires user confirmation

## Performance

- **Cold Start**: ~30 seconds (Python container + dependencies)
- **First Response**: 2-5 seconds (depends on LLM model)
- **Tool Execution**: <1 second for file operations
- **Memory Usage**: ~512MB steady state

## Comparison with RAG Version

| Aspect | No-RAG (This) | RAG Version |
|--------|---------------|-------------|
| **Setup Complexity** | Simple (3 manifests) | Complex (7 manifests) |
| **Resource Usage** | Low (75% less) | High |
| **Response Time** | Fast (no context retrieval) | Slower (embedding + search) |
| **Memory** | Session-only | Persistent |
| **Scalability** | Limited (interactive) | High (API-based) |
| **History Access** | Last 10 messages | Semantic search over all history |

Choose this version when:
- You need simple, fast code generation
- You have limited resources
- Session-based history is sufficient
- You want minimal setup complexity

Choose the RAG version when:
- You need persistent conversation context
- You want semantic search over history
- You need multi-user session management
- You have sufficient resources

## Support

For issues:
1. Check the troubleshooting section above
2. Verify Ollama connectivity
3. Review pod logs
4. Ensure node selector matches available nodes