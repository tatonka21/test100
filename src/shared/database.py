import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String, nullable=False)
    capabilities = Column(JSON, default=list)
    resources = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    status = Column(String, default="initializing")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "capabilities": self.capabilities or [],
            "resources": self.resources or {},
            "parameters": self.parameters or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    parameters = Column(JSON, default=dict)
    status = Column(String, default="pending")
    result = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "parameters": self.parameters or {},
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class AgentState(Base):
    __tablename__ = "agent_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False)
    state_data = Column(JSON, default=dict)
    memory = Column(JSON, default=list)
    goals = Column(JSON, default=list)
    constraints = Column(JSON, default=list)
    project_context = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "state_data": self.state_data or {},
            "memory": self.memory or [],
            "goals": self.goals or [],
            "constraints": self.constraints or [],
            "project_context": self.project_context or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class DatabaseManager:
    def __init__(self):
        self.database_url = self._get_database_url()
        self.engine = None
        self.async_session_maker = None
        
    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "agent_platform")
        password = os.getenv("POSTGRES_PASSWORD", "agent_platform_password")
        database = os.getenv("POSTGRES_DB", "agent_platform")
        
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize the database connection and create tables."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close the database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.async_session_maker()

# Global database manager instance
db_manager = DatabaseManager()

async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    async with db_manager.get_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Repository classes for data access
class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, agent_data: Dict[str, Any]) -> Agent:
        """Create a new agent."""
        agent = Agent(**agent_data)
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent
    
    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        from sqlalchemy import select
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[Agent]:
        """Get all agents."""
        from sqlalchemy import select
        result = await self.session.execute(select(Agent))
        return result.scalars().all()
    
    async def update(self, agent_id: str, update_data: Dict[str, Any]) -> Optional[Agent]:
        """Update an agent."""
        agent = await self.get_by_id(agent_id)
        if agent:
            for key, value in update_data.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            agent.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(agent)
        return agent
    
    async def delete(self, agent_id: str) -> bool:
        """Delete an agent."""
        agent = await self.get_by_id(agent_id)
        if agent:
            await self.session.delete(agent)
            await self.session.commit()
            return True
        return False

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task."""
        task = Task(**task_data)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        from sqlalchemy import select
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()
    
    async def get_by_agent_id(self, agent_id: str) -> List[Task]:
        """Get all tasks for an agent."""
        from sqlalchemy import select
        result = await self.session.execute(select(Task).where(Task.agent_id == agent_id))
        return result.scalars().all()
    
    async def update(self, task_id: str, update_data: Dict[str, Any]) -> Optional[Task]:
        """Update a task."""
        task = await self.get_by_id(task_id)
        if task:
            for key, value in update_data.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(task)
        return task

class AgentStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_agent_id(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state by agent ID."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(AgentState).where(AgentState.agent_id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update(self, agent_id: str, state_data: Dict[str, Any]) -> AgentState:
        """Create or update agent state."""
        state = await self.get_by_agent_id(agent_id)
        
        if state:
            # Update existing state
            for key, value in state_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            state.updated_at = datetime.utcnow()
        else:
            # Create new state
            state = AgentState(agent_id=agent_id, **state_data)
            self.session.add(state)
        
        await self.session.commit()
        await self.session.refresh(state)
        return state