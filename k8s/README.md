# Kubernetes Deployment Guide

This directory contains Kubernetes manifests to deploy the Orange Code project with context management services.

## Architecture

The deployment consists of:
- **context-service**: FastAPI service for RAG-based context management (port 8000)
- **context-admin**: Streamlit admin UI for context inspection (port 8501)
- **Persistent Storage**: PVCs for ChromaDB and logs
- **Network Policies**: Secure communication within the namespace

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured to access your cluster
- LoadBalancer service type support (or modify to NodePort/Ingress)
- StorageClass named `standard` (or update PVC manifests)

## Quick Start

1. **Create all resources:**
```bash
kubectl apply -f k8s/
```

2. **Check deployment status:**
```bash
kubectl get all -n orange-code
```

3. **Access services:**
```bash
# Get external IPs
kubectl get services -n orange-code

# Access context-service API
curl http://<EXTERNAL-IP>:8000/

# Access admin UI
open http://<EXTERNAL-IP>:8501
```

## Individual Components

### 1. Namespace & Network Policies
```bash
kubectl apply -f k8s/namespace.yaml
```
Creates the `orange-code` namespace and network policies for secure communication.

### 2. Storage
```bash
kubectl apply -f k8s/persistent-volumes.yaml
```
Creates PVCs for:
- `chroma-db-pvc`: 10Gi for ChromaDB storage
- `context-logs-pvc`: 5Gi for application logs

### 3. Application Configuration
```bash
kubectl apply -f k8s/configmap.yaml
```
Creates ConfigMap with admin UI script.

### 4. Context Service
```bash
kubectl apply -f k8s/context-service-deployment.yaml
kubectl apply -f k8s/context-service-service.yaml
```
Deploys the main RAG context management service.

### 5. Admin UI
```bash
kubectl apply -f k8s/context-admin-deployment.yaml
kubectl apply -f k8s/context-admin-service.yaml
```
Deploys the Streamlit admin interface.

## Configuration

### Resource Limits
- **context-service**: 2-4Gi memory, 1-2 CPU
- **context-admin**: 512Mi-1Gi memory, 250-500m CPU

### Storage
Adjust storage sizes in `persistent-volumes.yaml` based on your needs.

### Service Types
- Default: LoadBalancer (for cloud providers)
- Alternative: NodePort (for local clusters)
- Alternative: Ingress (for advanced routing)

## Monitoring

Check pod status:
```bash
kubectl logs -f deployment/context-service -n orange-code
kubectl logs -f deployment/context-admin -n orange-code
```

Check resource usage:
```bash
kubectl top pods -n orange-code
```

## Troubleshooting

### Common Issues

1. **Pod Pending**: Check PVC status and StorageClass availability
2. **Service Not Accessible**: Verify LoadBalancer IP assignment
3. **Image Pull Issues**: Ensure `dustynv/l4t-pytorch:r36.2.0` is accessible

### Cleanup
```bash
kubectl delete namespace orange-code
```

## Migration from Docker Compose

The Kubernetes deployment provides several advantages over Docker Compose:
- **Scalability**: Easy horizontal scaling with replicas
- **High Availability**: Self-healing and rolling updates
- **Resource Management**: CPU/memory limits and requests
- **Network Isolation**: Namespace-based security
- **Persistent Storage**: Managed PVs with backup options

## Development

For local development, you can still use Docker Compose:
```bash
docker-compose up -d
```

For production/staging environments, use the Kubernetes deployment.