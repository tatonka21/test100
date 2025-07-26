import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the platform."""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.name = config.get("name", f"Agent-{agent_id}")
        self.type = config.get("type", "base")
        self.capabilities = config.get("capabilities", [])
        self.resources = config.get("resources", {})
        self.parameters = config.get("parameters", {})
        self.state = {}
        self.status = "initializing"
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        self.task_queue = asyncio.Queue()
        self.running = False
        
        # Initialize agent-specific state
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize agent-specific state."""
        # Default implementation does nothing
        pass
    
    @abstractmethod
    async def process_task(self, task_id: str, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return the result."""
        pass
    
    async def start(self):
        """Start the agent's main processing loop."""
        if self.running:
            logger.warning(f"Agent {self.agent_id} is already running")
            return
        
        self.running = True
        self.status = "running"
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Agent {self.agent_id} ({self.name}) started")
        
        # Start the main processing loop
        asyncio.create_task(self._processing_loop())
    
    async def stop(self):
        """Stop the agent's processing loop."""
        if not self.running:
            logger.warning(f"Agent {self.agent_id} is not running")
            return
        
        self.running = False
        self.status = "stopped"
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Agent {self.agent_id} ({self.name}) stopped")
    
    async def _processing_loop(self):
        """Main processing loop for the agent."""
        while self.running:
            try:
                # Get the next task from the queue with a timeout
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # No task available, continue the loop
                    continue
                
                task_id, task_type, parameters = task
                
                logger.info(f"Agent {self.agent_id} processing task {task_id} of type {task_type}")
                
                # Process the task
                try:
                    result = await self.process_task(task_id, task_type, parameters)
                    logger.info(f"Agent {self.agent_id} completed task {task_id}")
                    
                    # Here we would typically publish a task completion event
                    # This would be implemented by the specific agent runtime
                    
                except Exception as e:
                    logger.error(f"Agent {self.agent_id} failed to process task {task_id}: {e}")
                    result = {
                        "error": str(e),
                        "status": "failed"
                    }
                
                # Mark the task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in agent {self.agent_id} processing loop: {e}")
                # Sleep briefly to avoid tight error loops
                await asyncio.sleep(1)
    
    async def submit_task(self, task_type: str, parameters: Dict[str, Any]) -> str:
        """Submit a task to this agent's queue."""
        task_id = str(uuid.uuid4())
        
        await self.task_queue.put((task_id, task_type, parameters))
        
        logger.info(f"Task {task_id} of type {task_type} submitted to agent {self.agent_id}")
        
        return task_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "id": self.agent_id,
            "name": self.name,
            "type": self.type,
            "capabilities": self.capabilities,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
