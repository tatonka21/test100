"""
Shared modules for the Agent Platform.

This package contains common utilities, database models, metrics, LLM integration,
and shared functionality used across all services in the agent platform.
"""

from .database import (
    db_manager,
    get_db_session,
    Agent,
    Task,
    AgentState,
    AgentRepository,
    TaskRepository,
    AgentStateRepository,
    DatabaseManager
)

from .metrics import (
    MetricsMiddleware,
    setup_service_metrics,
    metrics_endpoint,
    track_database_operation,
    track_agent_task,
    update_agent_count,
    update_agent_memory,
    update_database_connections,
    track_rabbitmq_publish,
    track_rabbitmq_consume,
    MetricsCollector
)

from .llm import (
    llm_manager,
    generate_text,
    chat_completion,
    generate_code,
    analyze_data,
    plan_project,
    LLMManager,
    OpenAIProvider,
    AnthropicProvider
)

__all__ = [
    # Database
    "db_manager",
    "get_db_session",
    "Agent",
    "Task",
    "AgentState",
    "AgentRepository",
    "TaskRepository",
    "AgentStateRepository",
    "DatabaseManager",
    # Metrics
    "MetricsMiddleware",
    "setup_service_metrics",
    "metrics_endpoint",
    "track_database_operation",
    "track_agent_task",
    "update_agent_count",
    "update_agent_memory",
    "update_database_connections",
    "track_rabbitmq_publish",
    "track_rabbitmq_consume",
    "MetricsCollector",
    # LLM
    "llm_manager",
    "generate_text",
    "chat_completion",
    "generate_code",
    "analyze_data",
    "plan_project",
    "LLMManager",
    "OpenAIProvider",
    "AnthropicProvider"
]