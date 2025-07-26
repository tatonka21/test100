from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import aio_pika
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Platform - Agent Runtime")

# Models
class AgentTask(BaseModel):
    id: str
    agent_id: str
    task_type: str
    parameters: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

# In-memory store for development (would use DB in production)
tasks = {}
running_agents = {}

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
                    
                    elif event == "agent.terminated":
                        logger.info(f"Agent terminated event received for {agent_id}")
                        await terminate_agent(agent_id)
                
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
async def execute_task(task: AgentTask):
    # In a real implementation, this would:
    # 1. Send the task to the appropriate agent
    # 2. Monitor execution
    # 3. Update task status and result
    
    logger.info(f"Executing task {task.id} for agent {task.agent_id}")
    
    # Simulate task execution
    await asyncio.sleep(2)
    
    # Update task with result
    task.status = "completed"
    task.result = {"message": "Task completed successfully"}
    task.updated_at = datetime.utcnow()
    
    tasks[task.id] = task
    
    # Notify about task completion
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
                    "task_id": task.id,
                    "agent_id": task.agent_id,
                    "result": task.result
                }).encode()
            ),
            routing_key=f"task.completed.{task.agent_id}"
        )

# Routes
@app.post("/tasks", response_model=AgentTask)
async def create_task(
    agent_id: str, 
    task_type: str, 
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    if agent_id not in running_agents:
        raise HTTPException(status_code=404, detail="Agent not running")
    
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    task = AgentTask(
        id=task_id,
        agent_id=agent_id,
        task_type=task_type,
        parameters=parameters,
        status="pending",
        created_at=now,
        updated_at=now
    )
    
    tasks[task_id] = task
    
    # Execute the task in the background
    background_tasks.add_task(execute_task, task)
    
    return task

@app.get("/tasks/{task_id}", response_model=AgentTask)
async def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.get("/agents/{agent_id}/tasks", response_model=List[AgentTask])
async def get_agent_tasks(agent_id: str):
    if agent_id not in running_agents:
        raise HTTPException(status_code=404, detail="Agent not running")
    
    agent_tasks = [task for task in tasks.values() if task.agent_id == agent_id]
    return agent_tasks

@app.get("/agents/running", response_model=List[Dict[str, Any]])
async def get_running_agents():
    return list(running_agents.values())

@app.on_event("startup")
async def startup_event():
    # Start listening for agent events
    asyncio.create_task(listen_for_agent_events())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
