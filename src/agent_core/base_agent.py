import asyncio
import json
import logging
import uuid
import sys
sys.path.append('/workspaces/test100')
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.shared.database import (
    db_manager, AgentRepository, AgentStateRepository, TaskRepository
)

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
        
        # Database repositories
        self._agent_repo = None
        self._state_repo = None
        self._task_repo = None
        
        # Initialize agent-specific state
        self._initialize_state()
    
    async def _init_repositories(self):
        """Initialize database repositories."""
        if not self._agent_repo:
            session = db_manager.get_session()
            self._agent_repo = AgentRepository(session)
            self._state_repo = AgentStateRepository(session)
            self._task_repo = TaskRepository(session)
    
    async def load_state_from_db(self):
        """Load agent state from database."""
        try:
            await self._init_repositories()
            state_data = await self._state_repo.get_by_agent_id(self.agent_id)
            
            if state_data:
                self.state.update(state_data.state_data or {})
                # Update other state components
                if hasattr(self, 'memory'):
                    self.memory = state_data.memory or []
                if hasattr(self, 'goals'):
                    self.goals = state_data.goals or []
                if hasattr(self, 'constraints'):
                    self.constraints = state_data.constraints or []
                if hasattr(self, 'project_context'):
                    self.project_context = state_data.project_context or {}
                    
                logger.info(f"Loaded state for agent {self.agent_id}")
            else:
                logger.info(f"No existing state found for agent {self.agent_id}")
                
        except Exception as e:
            logger.error(f"Failed to load state for agent {self.agent_id}: {e}")
    
    async def save_state_to_db(self):
        """Save agent state to database."""
        try:
            await self._init_repositories()
            
            state_data = {
                "state_data": self.state,
                "memory": getattr(self, 'memory', []),
                "goals": getattr(self, 'goals', []),
                "constraints": getattr(self, 'constraints', []),
                "project_context": getattr(self, 'project_context', {})
            }
            
            await self._state_repo.create_or_update(self.agent_id, state_data)
            logger.debug(f"Saved state for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to save state for agent {self.agent_id}: {e}")
    
    async def update_status_in_db(self, status: str):
        """Update agent status in database."""
        try:
            await self._init_repositories()
            await self._agent_repo.update(self.agent_id, {"status": status})
            self.status = status
            self.updated_at = datetime.utcnow()
            logger.debug(f"Updated status for agent {self.agent_id} to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update status for agent {self.agent_id}: {e}")
    
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
        
        try:
            # Load state from database
            await self.load_state_from_db()
            
            self.running = True
            await self.update_status_in_db("running")
            
            logger.info(f"Agent {self.agent_id} ({self.name}) started")
            
            # Start the main processing loop
            asyncio.create_task(self._processing_loop())
            
        except Exception as e:
            logger.error(f"Failed to start agent {self.agent_id}: {e}")
            await self.update_status_in_db("error")
            raise
    
    async def stop(self):
        """Stop the agent's processing loop."""
        if not self.running:
            logger.warning(f"Agent {self.agent_id} is not running")
            return
        
        try:
            self.running = False
            
            # Save final state to database
            await self.save_state_to_db()
            await self.update_status_in_db("stopped")
            
            logger.info(f"Agent {self.agent_id} ({self.name}) stopped")
            
        except Exception as e:
            logger.error(f"Error stopping agent {self.agent_id}: {e}")
            await self.update_status_in_db("error")
    
    async def _processing_loop(self):
        """Main processing loop for the agent."""
        last_state_save = datetime.utcnow()
        state_save_interval = 30  # Save state every 30 seconds
        
        while self.running:
            try:
                # Get the next task from the queue with a timeout
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # No task available, check if we need to save state
                    now = datetime.utcnow()
                    if (now - last_state_save).total_seconds() > state_save_interval:
                        await self.save_state_to_db()
                        last_state_save = now
                    continue
                
                task_id, task_type, parameters = task
                
                logger.info(f"Agent {self.agent_id} processing task {task_id} of type {task_type}")
                
                # Process the task
                try:
                    result = await self.process_task(task_id, task_type, parameters)
                    logger.info(f"Agent {self.agent_id} completed task {task_id}")
                    
                    # Save state after processing task
                    await self.save_state_to_db()
                    last_state_save = datetime.utcnow()
                    
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
