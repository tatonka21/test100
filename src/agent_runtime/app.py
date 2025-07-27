from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import aio_pika
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
import sys
sys.path.append('/workspaces/test100')

from src.shared.database import (
    db_manager, get_db_session, Task as TaskModel, Agent as AgentModel,
    TaskRepository, AgentRepository, AgentStateRepository
)
from src.shared.metrics import (
    MetricsMiddleware, setup_service_metrics, metrics_endpoint,
    track_database_operation, track_agent_task, track_rabbitmq_publish,
    track_rabbitmq_consume, MetricsCollector
)
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Platform - Agent Runtime")

# Setup metrics
setup_service_metrics("agent-runtime", "1.0.0")
app.add_middleware(MetricsMiddleware, service_name="agent-runtime")
metrics_collector = MetricsCollector("agent-runtime")

# Pydantic models for API
class AgentTask(BaseModel):
    id: str
    agent_id: str
    task_type: str
    parameters: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# In-memory store for running agents (runtime state)
running_agents = {}

# Database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize database connection and start event listener on startup."""
    try:
        await db_manager.initialize()
        # Start listening for agent events
        asyncio.create_task(listen_for_agent_events())
        logger.info("Agent Runtime started successfully")
    except Exception as e:
        logger.error(f"Failed to start Agent Runtime: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    await db_manager.close()
    logger.info("Agent Runtime shut down")

# RabbitMQ connection
async def get_rabbitmq_connection():
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_user = os.getenv("RABBITMQ_USER", "agent_platform")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "agent_platform_password")
    
    connection = await aio_pika.connect_robust(
        f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}/"
    )
    return connection

# Agent event listener
async def listen_for_agent_events():
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        
        # Declare the exchange
        exchange = await channel.declare_exchange(
            "agent_events", aio_pika.ExchangeType.TOPIC
        )
        
        # Declare the queue
        queue = await channel.declare_queue("agent_runtime_events", durable=True)
        
        # Bind the queue to the exchange with routing keys
        await queue.bind(exchange, routing_key="agent.created")
        await queue.bind(exchange, routing_key="agent.terminated")
        
        async for message in queue:
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    event = data.get("event")
                    agent_id = data.get("agent_id")
                    
                    if event == "agent.created":
                        logger.info(f"Agent created event received for {agent_id}")
                        config = data.get("config", {})
                        await initialize_agent(agent_id, config)
                        # Track message consumption
                        track_rabbitmq_consume("agent-runtime", "agent_runtime_events")
                    
                    elif event == "agent.terminated":
                        logger.info(f"Agent terminated event received for {agent_id}")
                        await terminate_agent(agent_id)
                        # Track message consumption
                        track_rabbitmq_consume("agent-runtime", "agent_runtime_events")
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

# Agent lifecycle management
async def initialize_agent(agent_id: str, config: Dict[str, Any]):
    # In a real implementation, this would:
    # 1. Allocate resources for the agent
    # 2. Load the agent's model and tools
    # 3. Start the agent's execution environment
    
    logger.info(f"Initializing agent {agent_id} with config: {config}")
    
    # For now, just track that the agent is running
    running_agents[agent_id] = {
        "id": agent_id,
        "config": config,
        "status": "running",
        "started_at": datetime.utcnow()
    }
    
    # Notify the agent manager that the agent is now running
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        
        exchange = await channel.declare_exchange(
            "agent_events", aio_pika.ExchangeType.TOPIC
        )
        
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps({
                    "event": "agent.status_changed",
                    "agent_id": agent_id,
                    "status": "running"
                }).encode()
            ),
            routing_key=f"agent.status_changed.{agent_id}"
        )

async def terminate_agent(agent_id: str):
    if agent_id not in running_agents:
        logger.warning(f"Attempted to terminate non-running agent {agent_id}")
        return
    
    # In a real implementation, this would:
    # 1. Stop the agent's execution
    # 2. Save any state if needed
    # 3. Release allocated resources
    
    logger.info(f"Terminating agent {agent_id}")
    
    # Remove from running agents
    del running_agents[agent_id]

# Task execution
@track_agent_task("", "")  # Will be updated with actual values
async def execute_task(task_id: str):
    """Execute a task and update its status in the database."""
    try:
        async with db_manager.get_session() as db:
            task_repo = TaskRepository(db)
            
            # Get the task
            task = await task_repo.get_by_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            # Update task status to running
            await task_repo.update(task_id, {
                "status": "running",
                "started_at": datetime.utcnow()
            })
            
            logger.info(f"Executing task {task_id} for agent {task.agent_id}")
            
            # Track task execution start
            start_time = datetime.utcnow()
            
            # In a real implementation, this would:
            # 1. Load the agent's configuration and state
            # 2. Execute the task using the agent's capabilities
            # 3. Update the agent's state based on the result
            
            # For now, simulate task execution
            await asyncio.sleep(2)
            
            # Update task with result
            result = {"message": "Task completed successfully", "timestamp": datetime.utcnow().isoformat()}
            await task_repo.update(task_id, {
                "status": "completed",
                "result": result,
                "completed_at": datetime.utcnow()
            })
            
            # Track task completion metrics
            from src.shared.metrics import agent_tasks_total, agent_task_duration_seconds
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            agent_tasks_total.labels(
                agent_id=task.agent_id,
                task_type=task.task_type,
                status="success"
            ).inc()
            
            agent_task_duration_seconds.labels(
                agent_id=task.agent_id,
                task_type=task.task_type
            ).observe(duration)
            
            # Notify about task completion
            try:
                connection = await get_rabbitmq_connection()
                async with connection:
                    channel = await connection.channel()
                    
                    exchange = await channel.declare_exchange(
                        "agent_events", aio_pika.ExchangeType.TOPIC
                    )
                    
                    await exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({
                                "event": "task.completed",
                                "task_id": task_id,
                                "agent_id": task.agent_id,
                                "result": result
                            }).encode()
                        ),
                        routing_key=f"task.completed.{task.agent_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to publish task completion event: {e}")
                
    except Exception as e:
        logger.error(f"Failed to execute task {task_id}: {e}")
        # Update task status to failed
        try:
            async with db_manager.get_session() as db:
                task_repo = TaskRepository(db)
                await task_repo.update(task_id, {
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow()
                })
        except Exception as update_error:
            logger.error(f"Failed to update task status to failed: {update_error}")

# Routes
@app.post("/tasks", response_model=AgentTask)
async def create_task(
    agent_id: str,
    task_type: str,
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new task for an agent."""
    try:
        # Check if agent is running
        if agent_id not in running_agents:
            # Also check if agent exists in database
            agent_repo = AgentRepository(db)
            agent = await agent_repo.get_by_id(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            else:
                raise HTTPException(status_code=400, detail="Agent not running")
        
        task_id = str(uuid.uuid4())
        
        # Create task in database
        task_repo = TaskRepository(db)
        task_data = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "parameters": parameters,
            "status": "pending"
        }
        
        task_db = await task_repo.create(task_data)
        
        # Execute the task in the background
        background_tasks.add_task(execute_task, task_id)
        
        return AgentTask(
            id=task_db.id,
            agent_id=task_db.agent_id,
            task_type=task_db.task_type,
            parameters=task_db.parameters,
            status=task_db.status,
            result=task_db.result,
            error_message=task_db.error_message,
            created_at=task_db.created_at,
            updated_at=task_db.updated_at,
            started_at=task_db.started_at,
            completed_at=task_db.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.get("/tasks/{task_id}", response_model=AgentTask)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a task by ID."""
    try:
        task_repo = TaskRepository(db)
        task_db = await task_repo.get_by_id(task_id)
        
        if not task_db:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return AgentTask(
            id=task_db.id,
            agent_id=task_db.agent_id,
            task_type=task_db.task_type,
            parameters=task_db.parameters,
            status=task_db.status,
            result=task_db.result,
            error_message=task_db.error_message,
            created_at=task_db.created_at,
            updated_at=task_db.updated_at,
            started_at=task_db.started_at,
            completed_at=task_db.completed_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")

@app.get("/agents/{agent_id}/tasks", response_model=List[AgentTask])
async def get_agent_tasks(agent_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get all tasks for an agent."""
    try:
        # Check if agent exists
        agent_repo = AgentRepository(db)
        agent = await agent_repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        task_repo = TaskRepository(db)
        tasks_db = await task_repo.get_by_agent_id(agent_id)
        
        return [
            AgentTask(
                id=task.id,
                agent_id=task.agent_id,
                task_type=task.task_type,
                parameters=task.parameters,
                status=task.status,
                result=task.result,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task in tasks_db
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent tasks: {str(e)}")

@app.get("/agents/running", response_model=List[Dict[str, Any]])
async def get_running_agents():
    """Get all currently running agents."""
    return list(running_agents.values())

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db_manager.get_session() as session:
            await session.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "agent-runtime",
            "database": "connected",
            "running_agents": len(running_agents)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "agent-runtime",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()
