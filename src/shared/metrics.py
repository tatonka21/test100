"""
Shared metrics module for the Agent Platform.

This module provides Prometheus metrics collection for all services.
"""

import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common metrics across all services
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['service']
)

# Agent-specific metrics
agents_total = Gauge(
    'agents_total',
    'Total number of agents',
    ['status', 'type']
)

agent_tasks_total = Counter(
    'agent_tasks_total',
    'Total number of agent tasks',
    ['agent_id', 'task_type', 'status']
)

agent_task_duration_seconds = Histogram(
    'agent_task_duration_seconds',
    'Agent task duration in seconds',
    ['agent_id', 'task_type']
)

agent_memory_usage_bytes = Gauge(
    'agent_memory_usage_bytes',
    'Agent memory usage in bytes',
    ['agent_id']
)

# Database metrics
database_connections_active = Gauge(
    'database_connections_active',
    'Active database connections',
    ['service']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['service', 'operation']
)

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['service', 'operation', 'status']
)

# Message queue metrics
rabbitmq_messages_published_total = Counter(
    'rabbitmq_messages_published_total',
    'Total messages published to RabbitMQ',
    ['service', 'exchange', 'routing_key']
)

rabbitmq_messages_consumed_total = Counter(
    'rabbitmq_messages_consumed_total',
    'Total messages consumed from RabbitMQ',
    ['service', 'queue']
)

# Service info
service_info = Info(
    'service_info',
    'Service information'
)

class MetricsMiddleware:
    """FastAPI middleware for collecting HTTP metrics."""
    
    def __init__(self, app, service_name: str):
        self.app = app
        self.service_name = service_name
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        # Start timing
        start_time = time.time()
        
        # Increment in-progress counter
        http_requests_in_progress.labels(service=self.service_name).inc()
        
        # Create a request object to get path and method
        method = scope["method"]
        path = scope["path"]
        
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            # Process request
            await self.app(scope, receive, send_wrapper)
            
        except Exception as e:
            status_code = 500
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status_code=status_code,
                service=self.service_name
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path,
                service=self.service_name
            ).observe(duration)
            
            # Decrement in-progress counter
            http_requests_in_progress.labels(service=self.service_name).dec()

def setup_service_metrics(service_name: str, version: str = "1.0.0"):
    """Setup service-specific metrics."""
    service_info.info({
        'service': service_name,
        'version': version,
        'description': f'Agent Platform - {service_name}'
    })
    
    logger.info(f"Metrics initialized for service: {service_name}")

async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

def track_database_operation(service_name: str, operation: str):
    """Decorator to track database operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                
                database_query_duration_seconds.labels(
                    service=service_name,
                    operation=operation
                ).observe(duration)
                
                database_queries_total.labels(
                    service=service_name,
                    operation=operation,
                    status=status
                ).inc()
                
        return wrapper
    return decorator

def track_agent_task(agent_id: str, task_type: str):
    """Decorator to track agent task execution."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                
                agent_task_duration_seconds.labels(
                    agent_id=agent_id,
                    task_type=task_type
                ).observe(duration)
                
                agent_tasks_total.labels(
                    agent_id=agent_id,
                    task_type=task_type,
                    status=status
                ).inc()
                
        return wrapper
    return decorator

def update_agent_count(status: str, agent_type: str, count: int):
    """Update agent count metrics."""
    agents_total.labels(status=status, type=agent_type).set(count)

def update_agent_memory(agent_id: str, memory_bytes: int):
    """Update agent memory usage metrics."""
    agent_memory_usage_bytes.labels(agent_id=agent_id).set(memory_bytes)

def update_database_connections(service_name: str, count: int):
    """Update database connection count."""
    database_connections_active.labels(service=service_name).set(count)

def track_rabbitmq_publish(service_name: str, exchange: str, routing_key: str):
    """Track RabbitMQ message publishing."""
    rabbitmq_messages_published_total.labels(
        service=service_name,
        exchange=exchange,
        routing_key=routing_key
    ).inc()

def track_rabbitmq_consume(service_name: str, queue: str):
    """Track RabbitMQ message consumption."""
    rabbitmq_messages_consumed_total.labels(
        service=service_name,
        queue=queue
    ).inc()

class MetricsCollector:
    """Centralized metrics collector for complex operations."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        
    async def collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            import psutil
            
            # CPU usage
            cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
            cpu_usage.set(psutil.cpu_percent())
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = Gauge('system_memory_usage_bytes', 'System memory usage in bytes')
            memory_usage.set(memory.used)
            
            memory_total = Gauge('system_memory_total_bytes', 'System total memory in bytes')
            memory_total.set(memory.total)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = Gauge('system_disk_usage_bytes', 'System disk usage in bytes')
            disk_usage.set(disk.used)
            
            disk_total = Gauge('system_disk_total_bytes', 'System total disk in bytes')
            disk_total.set(disk.total)
            
        except ImportError:
            logger.warning("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")