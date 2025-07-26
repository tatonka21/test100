from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Platform - API Gateway")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
AGENT_MANAGER_URL = os.getenv("AGENT_MANAGER_URL", "http://localhost:8000")
AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://localhost:8001")

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

class TaskCreate(BaseModel):
    agent_id: str
    task_type: str
    parameters: Dict[str, Any]

class Task(BaseModel):
    id: str
    agent_id: str
    task_type: str
    parameters: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

# HTTP client
async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client

# Routes - Agent Management
@app.post("/agents", response_model=Agent)
async def create_agent(config: AgentConfig, client: httpx.AsyncClient = Depends(get_http_client)):
    """Create a new agent."""
    try:
        response = await client.post(f"{AGENT_MANAGER_URL}/agents", json=config.dict())
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating agent: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents", response_model=List[Agent])
async def list_agents(client: httpx.AsyncClient = Depends(get_http_client)):
    """List all agents."""
    try:
        response = await client.get(f"{AGENT_MANAGER_URL}/agents")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error listing agents: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, client: httpx.AsyncClient = Depends(get_http_client)):
    """Get an agent by ID."""
    try:
        response = await client.get(f"{AGENT_MANAGER_URL}/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting agent: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, client: httpx.AsyncClient = Depends(get_http_client)):
    """Delete an agent."""
    try:
        response = await client.delete(f"{AGENT_MANAGER_URL}/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error deleting agent: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Routes - Task Management
@app.post("/tasks", response_model=Task)
async def create_task(task: TaskCreate, client: httpx.AsyncClient = Depends(get_http_client)):
    """Create a new task for an agent."""
    try:
        response = await client.post(
            f"{AGENT_RUNTIME_URL}/tasks",
            params={
                "agent_id": task.agent_id,
                "task_type": task.task_type
            },
            json=task.parameters
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating task: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, client: httpx.AsyncClient = Depends(get_http_client)):
    """Get a task by ID."""
    try:
        response = await client.get(f"{AGENT_RUNTIME_URL}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting task: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}/tasks", response_model=List[Task])
async def get_agent_tasks(agent_id: str, client: httpx.AsyncClient = Depends(get_http_client)):
    """Get all tasks for an agent."""
    try:
        response = await client.get(f"{AGENT_RUNTIME_URL}/agents/{agent_id}/tasks")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting agent tasks: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Error getting agent tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check(client: httpx.AsyncClient = Depends(get_http_client)):
    """Check the health of the API gateway and its dependencies."""
    health = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Agent Manager
    try:
        response = await client.get(f"{AGENT_MANAGER_URL}/health", timeout=2.0)
        if response.status_code == 200:
            health["services"]["agent_manager"] = "ok"
        else:
            health["services"]["agent_manager"] = f"degraded ({response.status_code})"
            health["status"] = "degraded"
    except Exception as e:
        health["services"]["agent_manager"] = f"down ({str(e)})"
        health["status"] = "degraded"
    
    # Check Agent Runtime
    try:
        response = await client.get(f"{AGENT_RUNTIME_URL}/health", timeout=2.0)
        if response.status_code == 200:
            health["services"]["agent_runtime"] = "ok"
        else:
            health["services"]["agent_runtime"] = f"degraded ({response.status_code})"
            health["status"] = "degraded"
    except Exception as e:
        health["services"]["agent_runtime"] = f"down ({str(e)})"
        health["status"] = "degraded"
    
    return health

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Get client IP and request details
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    url = str(request.url)
    
    logger.info(f"Request started: {method} {url} from {client_host}")
    
    # Process the request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(f"Request completed: {method} {url} - Status: {response.status_code} - Duration: {duration:.3f}s")
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
