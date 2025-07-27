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
import sys
sys.path.append('/workspaces/test100')

from src.shared.database import (
    db_manager, get_db_session, Agent as AgentModel,
    AgentRepository, AgentStateRepository
)
from src.shared.metrics import (
    MetricsMiddleware, setup_service_metrics, metrics_endpoint,
    track_database_operation, update_agent_count, track_rabbitmq_publish,
    MetricsCollector
)
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Platform - Agent Manager")

# Setup metrics
setup_service_metrics("agent-manager", "1.0.0")
app.add_middleware(MetricsMiddleware, service_name="agent-manager")
metrics_collector = MetricsCollector("agent-manager")

# Pydantic models for API
class AgentConfig(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    capabilities: List[str]
    resources: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

class Agent(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str
    capabilities: List[str]
    resources: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        await db_manager.initialize()
        
        # Start metrics collection
        asyncio.create_task(collect_agent_metrics())
        
        logger.info("Agent Manager started successfully")
    except Exception as e:
        logger.error(f"Failed to start Agent Manager: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    await db_manager.close()
    logger.info("Agent Manager shut down")

async def collect_agent_metrics():
    """Periodically collect agent metrics."""
    while True:
        try:
            async with db_manager.get_session() as db:
                agent_repo = AgentRepository(db)
                agents = await agent_repo.get_all()
                
                # Count agents by status and type
                status_counts = {}
                type_counts = {}
                
                for agent in agents:
                    status = agent.status
                    agent_type = agent.type
                    
                    status_key = f"{status}_{agent_type}"
                    status_counts[status_key] = status_counts.get(status_key, 0) + 1
                
                # Update metrics
                for key, count in status_counts.items():
                    status, agent_type = key.rsplit('_', 1)
                    update_agent_count(status, agent_type, count)
                
                # Collect system metrics
                await metrics_collector.collect_system_metrics()
                
        except Exception as e:
            logger.error(f"Error collecting agent metrics: {e}")
        
        # Wait 30 seconds before next collection
        await asyncio.sleep(30)

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
async def create_agent(config: AgentConfig, db: AsyncSession = Depends(get_db_session)):
    """Create a new agent."""
    agent_id = str(uuid.uuid4())
    
    try:
        # Create agent in database
        agent_repo = AgentRepository(db)
        agent_data = {
            "id": agent_id,
            "name": config.name,
            "description": config.description,
            "type": config.type,
            "capabilities": config.capabilities,
            "resources": config.resources,
            "parameters": config.parameters or {},
            "status": "initializing"
        }
        
        agent_db = await agent_repo.create(agent_data)
        
        # Initialize agent state
        state_repo = AgentStateRepository(db)
        await state_repo.create_or_update(agent_id, {
            "state_data": {},
            "memory": [],
            "goals": config.parameters.get("goals", []) if config.parameters else [],
            "constraints": config.parameters.get("constraints", []) if config.parameters else [],
            "project_context": {}
        })
        
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
                
                # Track metrics
                track_rabbitmq_publish("agent-manager", "agent_events", "agent.created")
                
            logger.info(f"Agent {agent_id} creation event published")
        except Exception as e:
            logger.error(f"Failed to publish agent creation event: {e}")
            # We continue anyway as this is just an event notification
        
        # Convert to response model
        return Agent(
            id=agent_db.id,
            name=agent_db.name,
            description=agent_db.description,
            type=agent_db.type,
            capabilities=agent_db.capabilities,
            resources=agent_db.resources,
            parameters=agent_db.parameters,
            status=agent_db.status,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

@app.get("/agents", response_model=List[Agent])
async def list_agents(db: AsyncSession = Depends(get_db_session)):
    """List all agents."""
    try:
        agent_repo = AgentRepository(db)
        agents_db = await agent_repo.get_all()
        
        return [
            Agent(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                type=agent.type,
                capabilities=agent.capabilities,
                resources=agent.resources,
                parameters=agent.parameters,
                status=agent.status,
                created_at=agent.created_at,
                updated_at=agent.updated_at
            )
            for agent in agents_db
        ]
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get an agent by ID."""
    try:
        agent_repo = AgentRepository(db)
        agent_db = await agent_repo.get_by_id(agent_id)
        
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return Agent(
            id=agent_db.id,
            name=agent_db.name,
            description=agent_db.description,
            type=agent_db.type,
            capabilities=agent_db.capabilities,
            resources=agent_db.resources,
            parameters=agent_db.parameters,
            status=agent_db.status,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete an agent."""
    try:
        agent_repo = AgentRepository(db)
        agent_db = await agent_repo.get_by_id(agent_id)
        
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update status to terminating first
        await agent_repo.update(agent_id, {"status": "terminating"})
        
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
                
                # Track metrics
                track_rabbitmq_publish("agent-manager", "agent_events", "agent.terminated")
                
        except Exception as e:
            logger.error(f"Failed to publish agent termination event: {e}")
        
        # Delete the agent
        success = await agent_repo.delete(agent_id)
        
        if success:
            return {"status": "success", "message": f"Agent {agent_id} deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete agent")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

@app.put("/agents/{agent_id}/status", response_model=Agent)
async def update_agent_status(agent_id: str, status: str, db: AsyncSession = Depends(get_db_session)):
    """Update an agent's status."""
    try:
        agent_repo = AgentRepository(db)
        agent_db = await agent_repo.update(agent_id, {"status": status})
        
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return Agent(
            id=agent_db.id,
            name=agent_db.name,
            description=agent_db.description,
            type=agent_db.type,
            capabilities=agent_db.capabilities,
            resources=agent_db.resources,
            parameters=agent_db.parameters,
            status=agent_db.status,
            created_at=agent_db.created_at,
            updated_at=agent_db.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent status {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent status: {str(e)}")

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
            "service": "agent-manager",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "agent-manager",
            "database": "disconnected",
            "error": str(e)
        }

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
