# Agent File Structure

## Overview

This project has been restructured to eliminate duplicate `agent_no_rag.py` files and maintain a single source of truth.

## File Locations

### Main Agent Files (Source of Truth)
- `agent_no_rag.py` - Main no-RAG agent implementation
- `utils.py` - Shared utility functions
- `agent.py` - Base agent implementation  
- `agent_with_rag.py` - RAG-enhanced agent

### Test Environment (Uses Shared Files)
- `test-no-rag/` - Local testing environment with uv
  - References `../agent_no_rag.py` (no duplicate)
  - Uses shared `../utils.py`

### Kubernetes Deployment (Uses Shared Files)
- `deploy/deploy-no-rag/` - Kubernetes manifests
  - Mounts source code via hostPath volume
  - Copies shared files during init
  - No embedded code duplication

## Benefits

1. **Single Source of Truth**: Only one `agent_no_rag.py` to maintain
2. **Consistency**: All environments use the same code
3. **Easier Updates**: Change once, affects all deployment methods
4. **Reduced Duplication**: No more sync issues between copies
5. **Better Maintainability**: Clear structure with shared components

## How It Works

### Local Testing
```bash
cd test-no-rag
uv run python ../agent_no_rag.py  # Uses shared file
```

### Kubernetes Deployment
```bash
kubectl apply -k deploy/deploy-no-rag/
# Deployment mounts source directory and copies agent files
```

## Updating the Agent

1. Edit `agent_no_rag.py` in project root
2. Test locally with: `cd test-no-rag && uv run python ../agent_no_rag.py`
3. Deploy with: `kubectl apply -k deploy/deploy-no-rag/`

All environments automatically use the updated code.

## File Relationships

```
project-root/
├── agent_no_rag.py           # ← SOURCE OF TRUTH
├── utils.py                  # ← Shared utilities
├── test-no-rag/
│   ├── agent_no_rag.py       # ❌ REMOVED (now uses ../agent_no_rag.py)
│   └── run.sh               # ✅ Updated to use shared file
└── deploy/deploy-no-rag/
    ├── agent-config.yaml     # ✅ Updated (no embedded code)
    └── agent-no-rag-deployment.yaml  # ✅ Updated (mounts source)
```

This structure eliminates code duplication while maintaining all functionality.