# Agent Platform - 100 AI Agents System

A scalable, microservices-based platform for managing and orchestrating up to 100 autonomous AI agents. The platform provides a robust infrastructure for agent lifecycle management, task execution, and monitoring.

## 🏗️ Architecture Overview

The platform consists of several microservices working together:

### Core Services
- **API Gateway** (Port 8080) - Main entry point for all client requests
- **Agent Manager** (Port 8000) - Handles agent lifecycle and configuration
- **Agent Runtime** (Port 8001) - Executes agent tasks and manages runtime state

### Infrastructure Services
- **RabbitMQ** - Message broker for inter-service communication
- **PostgreSQL** - Primary database for persistent storage
- **Redis** - Caching and pub/sub messaging
- **Qdrant** - Vector database for embeddings and semantic search
- **MinIO** - S3-compatible object storage

### Monitoring Stack
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization and dashboards
- **Various Exporters** - System and service metrics

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM
- 20GB free disk space

### 1. Clone and Setup
```bash
git clone <repository-url>
cd test100
chmod +x scripts/deploy.sh
```

### 2. Start the Platform
```bash
./scripts/deploy.sh start
```

This will:
- Start all infrastructure services
- Build and deploy application services
- Start monitoring stack
- Run health checks
- Create a test agent and task

### 3. Access the Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API Gateway | http://localhost:8080 | - |
| Agent Manager | http://localhost:8000 | - |
| Agent Runtime | http://localhost:8001 | - |
| RabbitMQ UI | http://localhost:15672 | guest/guest |
| Grafana | http://localhost:3000 | admin/admin_password |
| Prometheus | http://localhost:9090 | - |
| MinIO Console | http://localhost:9001 | agent_platform/agent_platform_password |

### 4. API Documentation
- API Gateway: http://localhost:8080/docs
- Agent Manager: http://localhost:8000/docs
- Agent Runtime: http://localhost:8001/docs

## 📋 Features

### ✅ Implemented
- **Microservices Architecture** - Scalable, distributed system design
- **Database Persistence** - PostgreSQL with SQLAlchemy ORM
- **Agent Lifecycle Management** - Create, start, stop, and delete agents
- **Task Execution System** - Asynchronous task processing
- **Built-in Tools** - File operations, code execution, HTTP requests, etc.
- **Event-Driven Communication** - RabbitMQ message broker
- **Health Monitoring** - Health check endpoints for all services
- **Docker Containerization** - Easy deployment and scaling
- **Monitoring Stack** - Prometheus and Grafana integration

### 🚧 In Progress
- **Metrics Endpoints** - Prometheus metrics for all services
- **LLM Integration** - Real AI capabilities for agents
- **Authentication/Authorization** - Security layer
- **Advanced Error Handling** - Comprehensive error management

### 📋 Planned
- **Kubernetes Deployment** - Production-ready orchestration
- **Agent Clustering** - Distributed agent execution
- **Web UI** - Management dashboard
- **Plugin System** - Extensible tool architecture

## 🤖 Agent System

### Agent Types
- **BaseAgent** - Abstract base class for all agents
- **AutonomousAgent** - Self-directed agents with goals and constraints

### Agent Capabilities
- **code_generation** - Generate and refactor code
- **data_analysis** - Analyze datasets and generate insights
- **web_browsing** - Web scraping and content retrieval
- **llm** - Text generation and language processing

### Built-in Tools
- `read_file` / `write_file` - File system operations
- `execute_code` - Safe code execution in multiple languages
- `http_request` - HTTP client for API calls
- `search_text` - Pattern matching and text search
- `memory_add` / `memory_search` - Agent memory management
- `json_parse` - JSON data processing
- `calculate` - Mathematical expressions

## 📊 Database Schema

### Core Tables
- **agents** - Agent configurations and metadata
- **tasks** - Task definitions and execution history
- **agent_states** - Persistent agent state and memory

### Key Features
- Async SQLAlchemy with PostgreSQL
- Automatic state persistence
- Task history tracking
- Memory management

## 🔧 Development

### Project Structure
```
test100/
├── src/
│   ├── shared/           # Common database models and utilities
│   ├── agent_core/       # Agent base classes and tools
│   ├── agent_manager/    # Agent lifecycle service
│   ├── agent_runtime/    # Task execution service
│   └── api_gateway/      # API gateway service
├── k8s/                  # Kubernetes manifests
├── monitoring/           # Monitoring configuration
├── scripts/              # Deployment and utility scripts
└── docker-compose.yml    # Local development setup
```

### Adding New Tools
1. Implement tool function in `src/agent_core/tools.py`
2. Register tool in `BuiltinTools` class
3. Update `register_builtin_tools()` function

### Adding New Agent Types
1. Extend `BaseAgent` class
2. Implement `process_task()` method
3. Register agent type in runtime

## 🐳 Docker Commands

### Basic Operations
```bash
# Start all services
./scripts/deploy.sh start

# Stop all services
./scripts/deploy.sh stop

# Restart services
./scripts/deploy.sh restart

# Run tests
./scripts/deploy.sh test

# Clean up everything
./scripts/deploy.sh cleanup

# Show service URLs
./scripts/deploy.sh urls
```

### Manual Docker Compose
```bash
# Start infrastructure only
docker-compose up -d rabbitmq postgres redis qdrant minio

# Start applications
docker-compose up -d agent-manager agent-runtime api-gateway

# View logs
docker-compose logs -f agent-manager

# Scale services
docker-compose up -d --scale agent-runtime=3
```

## 📈 Monitoring

### Metrics Available
- HTTP request rates and latencies
- Agent count by status
- Task completion rates
- System resource usage
- Database connection pools

### Grafana Dashboards
- **Agent Platform Overview** - High-level system metrics
- Custom dashboards can be added to `monitoring/dashboards/`

### Prometheus Targets
- All application services expose `/metrics` endpoints
- Infrastructure services monitored via exporters
- Custom metrics can be added using prometheus_client

## 🔒 Security Considerations

### Current State
- No authentication/authorization implemented
- Services communicate over unencrypted HTTP
- Default credentials used for infrastructure services

### Recommendations for Production
- Implement JWT-based authentication
- Use TLS for all communications
- Rotate default passwords
- Network segmentation
- Resource limits and quotas

## 🚀 Scaling

### Horizontal Scaling
- Agent Runtime can be scaled to multiple instances
- Load balancing handled by Docker Compose
- Database connection pooling configured

### Vertical Scaling
- Adjust resource limits in docker-compose.yml
- Configure database connection pools
- Tune RabbitMQ settings

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check service logs
docker-compose logs service-name

# Verify resource availability
docker system df
```

**Database connection errors:**
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

**Agent tasks failing:**
```bash
# Check agent runtime logs
docker-compose logs agent-runtime

# Verify RabbitMQ connectivity
docker-compose exec rabbitmq rabbitmqctl status
```

### Health Checks
All services provide health check endpoints:
- http://localhost:8080/health (API Gateway)
- http://localhost:8000/health (Agent Manager)
- http://localhost:8001/health (Agent Runtime)

## 📝 API Examples

### Create an Agent
```bash
curl -X POST http://localhost:8080/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Generator",
    "description": "Generates Python code",
    "type": "autonomous",
    "capabilities": ["code_generation"],
    "resources": {"memory": "2GB", "cpu": "2 cores"},
    "parameters": {
      "goals": ["Generate high-quality code"],
      "constraints": ["Follow PEP 8 standards"]
    }
  }'
```

### Create a Task
```bash
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-uuid-here",
    "task_type": "generate_code",
    "parameters": {
      "description": "FastAPI web server",
      "language": "python",
      "framework": "fastapi"
    }
  }'
```

### List Agents
```bash
curl http://localhost:8080/agents
```

### Get Task Status
```bash
curl http://localhost:8080/tasks/task-uuid-here
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Create an issue with detailed information

---

**Status**: Active Development
**Version**: 1.0.0-beta
**Last Updated**: 2025-01-26
