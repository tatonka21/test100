from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import os
import json
import aio_pika
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Platform - Agent Manager")

# Models
class AgentConfig(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    capabilities: List[str]
    resources: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

class Agent(BaseModel):
    id: str
    config: AgentConfig
    status: str
    created_at: datetime
    updated_at: datetime

# In-memory store for development (would use DB in production)
agents = {}

# RabbitMQ connection
async def get_rabbitmq_connection():
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_user = os.getenv("RABBITMQ_USER", "agent_platform")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "agent_platform_password")
    
    connection = await aio_pika.connect_robust(
        f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}/"
    )
    return connection

# Routes
@app.post("/agents", response_model=Agent)
async def create_agent(config: AgentConfig):
    agent_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    agent = Agent(
        id=agent_id,
        config=config,
        status="initializing",
        created_at=now,
        updated_at=now
    )
    
    agents[agent_id] = agent
    
    # Publish agent creation event
    try:
        connection = await get_rabbitmq_connection()
        async with connection:
            channel = await connection.channel()
            
            # Declare the exchange
            exchange = await channel.declare_exchange(
                "agent_events", aio_pika.ExchangeType.TOPIC
            )
            
            # Publish message
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps({
                        "event": "agent.created",
                        "agent_id": agent_id,
                        "config": config.dict()
                    }).encode()
                ),
                routing_key="agent.created"
            )
            
        logger.info(f"Agent {agent_id} creation event published")
    except Exception as e:
        logger.error(f"Failed to publish agent creation event: {e}")
        # We continue anyway as this is just an event notification
    
    return agent

@app.get("/agents", response_model=List[Agent])
async def list_agents():
    return list(agents.values())

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents[agent_id]

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update status to terminating
    agents[agent_id].status = "terminating"
    agents[agent_id].updated_at = datetime.utcnow()
    
    # Publish agent termination event
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
                        "event": "agent.terminated",
                        "agent_id": agent_id
                    }).encode()
                ),
                routing_key="agent.terminated"
            )
    except Exception as e:
        logger.error(f"Failed to publish agent termination event: {e}")
    
    # Remove the agent
    del agents[agent_id]
    
    return {"status": "success", "message": f"Agent {agent_id} deleted"}

@app.put("/agents/{agent_id}/status", response_model=Agent)
async def update_agent_status(agent_id: str, status: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agents[agent_id].status = status
    agents[agent_id].updated_at = datetime.utcnow()
    
    return agents[agent_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
